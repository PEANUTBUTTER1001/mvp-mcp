"""Run 소유 후보 파일의 조건부 저장·영속 재시도·중단 복구."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from mvp_mcp.core.exceptions import PipelineError

from .adaptive_wizard_model import AdaptiveRunStatus, AdaptiveWizardRun
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .candidate_file_model import (
    CandidateFileWriteReceipt,
    CandidateFileWriteRequest,
    CandidateFileWriteResult,
)
from .candidate_lifecycle_model import AppliedCandidateCycle
from .candidate_package_policy import allowed_candidate_paths, candidate_revision
from .candidate_package_usecase import _require_candidate_run
from .ports import CandidatePackageWorkspace, Clock
from .usecase import _run_stage


class WriteCandidateFileUseCase:
    def __init__(
        self, runs: AdaptiveWizardRunRepository, candidates: CandidatePackageWorkspace, clock: Clock
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._clock = clock

    def __call__(self, request: CandidateFileWriteRequest) -> CandidateFileWriteResult:
        _require_candidate_run(self._runs, request.run_id, allow_pending=True)
        if request.relative_path not in allowed_candidate_paths():
            raise PipelineError("candidate_write", "허용되지 않은 후보 상대 경로입니다.")
        with self._candidates.exclusive(request.run_id):
            return _run_stage(
                "candidate_write",
                lambda: self._execute(request),
                "저장 결과가 불명확하면 같은 입력·idempotency_key로 재시도하세요. "
                "documentation_package_status에서 중단된 요청과 최신 hash를 확인하세요.",
            )

    def _execute(self, request: CandidateFileWriteRequest) -> CandidateFileWriteResult:
        run = _require_candidate_run(self._runs, request.run_id, allow_pending=True)
        payload_hash = hashlib.sha256(
            json.dumps(
                request.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        receipt = run.candidate_write_receipts.get(request.idempotency_key)
        if receipt is not None:
            if receipt.payload_sha256 != payload_hash:
                return self._result(run, request, "CONFLICT", reason="IDEMPOTENCY_KEY_REUSED")
            if receipt.state == "COMPLETED":
                return self._result(run, request, "REPLAYED", receipt)
            if receipt.state == "CONFLICTED":
                return self._result(run, request, "CONFLICT", receipt, "FILE_CHANGED")
            return self._resume(run, request, receipt)
        if run.pending_candidate_write:
            return self._result(run, request, "CONFLICT", reason="PENDING_WRITE")
        if run.version != request.expected_run_version:
            return self._result(run, request, "CONFLICT", reason="RUN_VERSION_CHANGED")
        source = self._candidates.read(run.id, str(run.candidate_root))
        previous = source.files.get(request.relative_path)
        previous_hash = _hash(previous)
        if previous_hash != request.expected_file_sha256:
            return self._result(run, request, "CONFLICT", reason="FILE_CHANGED")
        if previous is None and len(source.files) >= 32:
            raise PipelineError("candidate_write", "후보 파일 수는 32개 이하여야 합니다.")
        content_hash = _hash(request.content)
        assert content_hash is not None
        operation: Literal["CREATED", "UPDATED", "UNCHANGED"] = (
            "UNCHANGED"
            if previous == request.content
            else "CREATED" if previous is None else "UPDATED"
        )
        receipt = CandidateFileWriteReceipt(
            payload_sha256=payload_hash,
            relative_path=request.relative_path,
            previous_sha256=previous_hash,
            content_sha256=content_hash,
            byte_count=len(request.content.encode("utf-8")),
            operation=operation,
            state="COMPLETED" if operation == "UNCHANGED" else "PENDING",
        )
        receipts = {**run.candidate_write_receipts, request.idempotency_key: receipt}
        if operation == "UNCHANGED":
            saved = self._save(run, {"candidate_write_receipts": receipts})
            return self._result(saved, request, "UNCHANGED", receipt)
        history = list(run.applied_candidate_cycles)
        if run.status is AdaptiveRunStatus.APPLIED:
            assert run.candidate_revision and run.preview_id and run.preview_manifest_sha256
            history.append(
                AppliedCandidateCycle(
                    lifecycle_revision=run.candidate_lifecycle.lifecycle_revision,
                    candidate_revision=run.candidate_revision,
                    preview_id=run.preview_id,
                    manifest_sha256=run.preview_manifest_sha256,
                    applied_outputs=list(run.applied_outputs),
                    applied_at=run.updated_at,
                )
            )
        # 파일 교체 전에 영속 intent와 무효화부터 기록: 중단된 쓰기로 preview 불가.
        prepared = self._save(
            run,
            {
                "candidate_write_receipts": receipts,
                "pending_candidate_write": request.idempotency_key,
                "status": AdaptiveRunStatus.DRAFT_READY,
                "candidate_revision": None,
                "candidate_profile": None,
                "preview_id": None,
                "preview_manifest_sha256": None,
                "preview_candidate_revision": None,
                "preview_conflicts": [],
                "applied_outputs": [],
                "applied_candidate_cycles": history,
            },
        )
        return self._resume(prepared, request, receipt)

    def _resume(
        self,
        run: AdaptiveWizardRun,
        request: CandidateFileWriteRequest,
        receipt: CandidateFileWriteReceipt,
    ) -> CandidateFileWriteResult:
        source = self._candidates.read(run.id, str(run.candidate_root))
        current_hash = _hash(source.files.get(receipt.relative_path))
        if current_hash not in {receipt.previous_sha256, receipt.content_sha256}:
            conflicted = receipt.model_copy(update={"state": "CONFLICTED"})
            saved = self._save(
                run,
                {
                    "candidate_write_receipts": {
                        **run.candidate_write_receipts,
                        request.idempotency_key: conflicted,
                    },
                    "pending_candidate_write": None,
                },
            )
            return self._result(saved, request, "CONFLICT", conflicted, "FILE_CHANGED")
        if current_hash != receipt.content_sha256:
            self._candidates.write_file(
                run.id,
                str(run.candidate_root),
                receipt.relative_path,
                request.content,
                receipt.previous_sha256,
            )
        completed = receipt.model_copy(update={"state": "COMPLETED"})
        saved = self._save(
            run,
            {
                "candidate_write_receipts": {
                    **run.candidate_write_receipts,
                    request.idempotency_key: completed,
                },
                "pending_candidate_write": None,
            },
        )
        return self._result(saved, request, receipt.operation, completed)

    def _save(self, run: AdaptiveWizardRun, changes: dict[str, object]) -> AdaptiveWizardRun:
        updated = run.model_copy(
            update={
                **changes,
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        validated = AdaptiveWizardRun.model_validate(updated.model_dump())
        return self._runs.save(validated, expected_version=run.version)

    def _result(
        self,
        run: AdaptiveWizardRun,
        request: CandidateFileWriteRequest,
        status: Literal["CREATED", "UPDATED", "UNCHANGED", "REPLAYED", "CONFLICT"],
        receipt: CandidateFileWriteReceipt | None = None,
        reason: str | None = None,
    ) -> CandidateFileWriteResult:
        source = self._candidates.read(run.id, str(run.candidate_root))
        return CandidateFileWriteResult(
            run_id=run.id,
            run_version=run.version,
            relative_path=request.relative_path,
            status=status,
            idempotency_key=request.idempotency_key,
            stored_sha256=(
                receipt.content_sha256 if receipt and receipt.state == "COMPLETED" else None
            ),
            byte_count=receipt.byte_count if receipt and receipt.state == "COMPLETED" else None,
            current_file_sha256=_hash(source.files.get(request.relative_path)),
            current_candidate_revision=candidate_revision(source.files),
            pending_idempotency_key=run.pending_candidate_write,
            reason=reason,
            next_action=(
                "중단된 요청은 원래 입력과 같은 idempotency_key로 재시도하세요."
                if run.pending_candidate_write
                else (
                    "현재 파일을 검토하고 최신 version/hash와 새 idempotency_key로 요청하세요."
                    if status == "CONFLICT"
                    else "반환된 run_version으로 다음 파일을 저장하세요. "
                    "전체 작성 후 status → validate → preview 순서로 진행하세요."
                )
            ),
        )


def _hash(content: str | None) -> str | None:
    return hashlib.sha256(content.encode("utf-8")).hexdigest() if content is not None else None
