"""Run-scoped candidate package의 검증·preview·write policy UseCase."""

from __future__ import annotations

from mvp_mcp.core.exceptions import PipelineError

from .adaptive_wizard_model import AdaptiveRunStatus, AdaptiveWizardRun, WritePolicy
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .candidate_package_model import (
    CandidatePackageApplyResult,
    CandidatePackageInspection,
    CandidatePackagePreviewResult,
    CandidatePackageStatusResult,
    CandidatePackageValidationResult,
    package_from_inspection,
)
from .candidate_package_policy import inspect_candidate_package
from .ports import CandidatePackageWorkspace, Clock, RepositoryDocumentationExporter

_PACKAGE_STATUSES = {
    AdaptiveRunStatus.DRAFT_READY,
    AdaptiveRunStatus.CANDIDATE_VALIDATED,
    AdaptiveRunStatus.PREVIEW_READY,
    AdaptiveRunStatus.CONFLICTED,
    AdaptiveRunStatus.APPLIED,
}


class ValidateCandidatePackageUseCase:
    """candidate root의 현 본문을 검증하고 revision을 Run에 결속한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        candidates: CandidatePackageWorkspace,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._clock = clock

    def __call__(
        self, run_id: str, run_version: int, candidate_revision: str
    ) -> CandidatePackageValidationResult:
        run = _require_candidate_run(self._runs, run_id)
        _assert_version(run, run_version)
        inspection = _inspect(self._candidates, run)
        _assert_candidate_revision(inspection, candidate_revision)
        result = inspection.validation
        if not result.valid or result.profile is None:
            return result
        if (
            run.candidate_sync_required
            and run.candidate_sync_base_revision == result.candidate_revision
        ):
            raise PipelineError(
                "candidate_lifecycle",
                "구조화 후보 계약이 바뀌었지만 candidate Markdown이 아직 갱신되지 않았습니다.",
                "candidate_lifecycle를 문서에 반영한 뒤 "
                "documentation_package_status로 다시 검증하세요.",
            )

        if (
            run.candidate_revision == result.candidate_revision
            and run.candidate_profile is result.profile
        ):
            return result

        recorded = run.model_copy(
            update={
                "status": AdaptiveRunStatus.CANDIDATE_VALIDATED,
                "candidate_revision": result.candidate_revision,
                "candidate_profile": result.profile,
                "candidate_sync_required": False,
                "candidate_sync_base_revision": None,
                "preview_id": None,
                "preview_manifest_sha256": None,
                "preview_candidate_revision": None,
                "preview_conflicts": [],
                "applied_outputs": [],
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        saved = self._runs.save(recorded, expected_version=run.version)
        return result.model_copy(
            update={
                "run_version": saved.version,
                "next_action": (
                    "documentation_preview_package에 반환된 run_version과 동일 "
                    "candidate_revision을 전달하세요."
                ),
            }
        )


class PreviewCandidatePackageUseCase:
    """검증된 candidate revision으로 preview를 만들고 safe_auto_apply를 내부 실행한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        candidates: CandidatePackageWorkspace,
        exporter: RepositoryDocumentationExporter,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._exporter = exporter
        self._clock = clock

    def __call__(
        self, run_id: str, run_version: int, candidate_revision: str
    ) -> CandidatePackagePreviewResult:
        run = _require_candidate_run(self._runs, run_id)
        _assert_version(run, run_version)
        inspection = _inspect(self._candidates, run)
        _assert_candidate_revision(inspection, candidate_revision)
        package = _require_valid_package(inspection)
        if (
            run.candidate_revision != candidate_revision
            or run.candidate_profile is not package.profile
        ):
            raise PipelineError(
                "candidate_package",
                "현재 candidate revision은 아직 Run에 검증 기록되지 않았습니다.",
                "documentation_validate_package를 먼저 호출한 뒤 반환된 run_version으로 "
                "preview하세요.",
            )

        preview = self._exporter.preview(run.id, run.project_root, package)
        previewed = run.model_copy(
            update={
                "status": (
                    AdaptiveRunStatus.CONFLICTED
                    if preview.conflicts
                    else AdaptiveRunStatus.PREVIEW_READY
                ),
                "preview_id": preview.preview_id,
                "preview_manifest_sha256": preview.manifest_sha256,
                "preview_candidate_revision": candidate_revision,
                "preview_conflicts": list(preview.conflicts),
                "applied_outputs": [],
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        saved = self._runs.save(previewed, expected_version=run.version)

        if run.write_policy is not WritePolicy.SAFE_AUTO_APPLY:
            return CandidatePackagePreviewResult(
                run_id=saved.id,
                run_version=saved.version,
                candidate_revision=candidate_revision,
                preview=preview,
                status=saved.status.value,
                next_action=_preview_next_action(saved),
            )
        if preview.conflicts:
            return CandidatePackagePreviewResult(
                run_id=saved.id,
                run_version=saved.version,
                candidate_revision=candidate_revision,
                preview=preview,
                status=AdaptiveRunStatus.CONFLICTED.value,
                next_action=(
                    "사용자 수정 또는 unmanaged 충돌 파일은 보존했습니다. candidate와 "
                    "preview를 전달하고, "
                    "충돌을 해소한 뒤 새 preview를 만드세요."
                ),
            )

        applied = self._exporter.apply(
            preview.preview_id,
            preview.manifest_sha256,
            "write_policy:safe_auto_apply",
            "1차 Adaptive Wizard에서 safe_auto_apply 정책을 확정함",
        )
        if applied.status == "BLOCKED":
            conflicted = saved.model_copy(
                update={
                    "status": AdaptiveRunStatus.CONFLICTED,
                    "preview_conflicts": list(applied.conflicts),
                    "version": saved.version + 1,
                    "updated_at": self._clock.now(),
                }
            )
            conflict_saved = self._runs.save(conflicted, expected_version=saved.version)
            return CandidatePackagePreviewResult(
                run_id=conflict_saved.id,
                run_version=conflict_saved.version,
                candidate_revision=candidate_revision,
                preview=preview,
                status=AdaptiveRunStatus.CONFLICTED.value,
                auto_apply=applied,
                next_action=(
                    "충돌 파일을 보존했습니다. candidate와 preview 결과를 사용자에게 전달하세요."
                ),
            )

        completed = saved.model_copy(
            update={
                "status": AdaptiveRunStatus.APPLIED,
                "applied_outputs": list(applied.applied_outputs),
                "version": saved.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        applied_run = self._runs.save(completed, expected_version=saved.version)
        return CandidatePackagePreviewResult(
            run_id=applied_run.id,
            run_version=applied_run.version,
            candidate_revision=candidate_revision,
            preview=preview,
            status=AdaptiveRunStatus.APPLIED.value,
            auto_apply=applied,
            next_action="safe_auto_apply 정책에 따라 충돌 없는 .mvpmcp 문서를 자동 반영했습니다.",
        )


class ApplyCandidatePackageUseCase:
    """manual_apply Run만 기존 exporter의 hash·충돌·원자 적용을 실행한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        candidates: CandidatePackageWorkspace,
        exporter: RepositoryDocumentationExporter,
        clock: Clock,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._exporter = exporter
        self._clock = clock

    def __call__(
        self,
        run_id: str,
        run_version: int,
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> CandidatePackageApplyResult:
        run = _require_candidate_run(self._runs, run_id)
        if run.write_policy is not WritePolicy.MANUAL_APPLY:
            return CandidatePackageApplyResult(
                run_id=run.id,
                run_version=run.version,
                candidate_revision=run.candidate_revision,
                status="POLICY_DENIED",
                preview_id=run.preview_id,
                manifest_sha256=run.preview_manifest_sha256,
                conflicts=list(run.preview_conflicts),
                next_action=(
                    "write_policy가 manual_apply가 아닙니다. generate_only는 후보·preview만 "
                    "제공하고, "
                    "safe_auto_apply는 preview 단계에서만 내부 반영됩니다."
                ),
            )
        if run.status is AdaptiveRunStatus.APPLIED and _matches_preview(
            run, preview_id, manifest_sha256
        ):
            return _applied_result(run)
        _assert_version(run, run_version)
        if not approved_by.strip() or not approval_note.strip():
            raise PipelineError(
                "approval",
                "manual_apply에는 적용 승인자와 승인 메모가 필요합니다.",
                "별도 반영 요청을 받은 뒤 approved_by와 approval_note를 제공하세요.",
            )
        if not _matches_preview(run, preview_id, manifest_sha256):
            raise PipelineError(
                "candidate_package",
                "preview ID 또는 manifest hash가 Run에 기록된 값과 다릅니다.",
                "documentation_package_status에서 최신 preview binding을 확인하세요.",
            )
        if run.status is AdaptiveRunStatus.CONFLICTED:
            return CandidatePackageApplyResult(
                run_id=run.id,
                run_version=run.version,
                candidate_revision=run.candidate_revision,
                status="CONFLICTED",
                preview_id=run.preview_id,
                manifest_sha256=run.preview_manifest_sha256,
                conflicts=list(run.preview_conflicts),
                next_action=(
                    "충돌 파일을 보존했습니다. 대상 파일을 정리한 뒤 "
                    "documentation_preview_package를 다시 호출하세요."
                ),
            )
        if run.status is not AdaptiveRunStatus.PREVIEW_READY:
            raise PipelineError(
                "candidate_package",
                f"수동 반영을 할 수 없는 Run 상태입니다: {run.status.value}",
                "검증·preview를 완료한 PREVIEW_READY 상태에서만 manual_apply를 호출하세요.",
            )
        inspection = _inspect(self._candidates, run)
        if inspection.validation.candidate_revision != run.preview_candidate_revision:
            raise PipelineError(
                "candidate_package",
                "preview 뒤 candidate 본문이 변경되었습니다.",
                "새 revision으로 validate와 preview를 다시 실행하세요.",
            )

        applied = self._exporter.apply(
            preview_id,
            manifest_sha256,
            approved_by.strip(),
            approval_note.strip(),
        )
        if applied.status == "BLOCKED":
            conflicted = run.model_copy(
                update={
                    "status": AdaptiveRunStatus.CONFLICTED,
                    "preview_conflicts": list(applied.conflicts),
                    "version": run.version + 1,
                    "updated_at": self._clock.now(),
                }
            )
            saved = self._runs.save(conflicted, expected_version=run.version)
            return CandidatePackageApplyResult(
                run_id=saved.id,
                run_version=saved.version,
                candidate_revision=saved.candidate_revision,
                status="CONFLICTED",
                preview_id=preview_id,
                manifest_sha256=manifest_sha256,
                conflicts=list(applied.conflicts),
                stale_outputs=list(applied.stale_outputs),
                next_action=(
                    "충돌 파일을 보존했습니다. candidate와 preview를 확인한 뒤 충돌을 해소하세요."
                ),
            )

        completed = run.model_copy(
            update={
                "status": AdaptiveRunStatus.APPLIED,
                "applied_outputs": list(applied.applied_outputs),
                "version": run.version + 1,
                "updated_at": self._clock.now(),
            }
        )
        saved = self._runs.save(completed, expected_version=run.version)
        return CandidatePackageApplyResult(
            run_id=saved.id,
            run_version=saved.version,
            candidate_revision=saved.candidate_revision,
            status="APPLIED",
            preview_id=preview_id,
            manifest_sha256=manifest_sha256,
            applied_outputs=list(applied.applied_outputs),
            skipped_outputs=list(applied.skipped_outputs),
            stale_outputs=list(applied.stale_outputs),
            next_action="manual_apply 정책에 따라 승인된 preview를 .mvpmcp에 반영했습니다.",
        )


class GetCandidatePackageStatusUseCase:
    """후보 본문 revision과 실제 `.mvpmcp` 상태를 새 I/O 없이 결합한다."""

    def __init__(
        self,
        runs: AdaptiveWizardRunRepository,
        candidates: CandidatePackageWorkspace,
        exporter: RepositoryDocumentationExporter,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._exporter = exporter

    def __call__(self, run_id: str) -> CandidatePackageStatusResult:
        run = _require_candidate_run(self._runs, run_id)
        assert run.write_policy is not None
        inspection = _inspect(self._candidates, run)
        validation = inspection.validation
        return CandidatePackageStatusResult(
            run_id=run.id,
            run_version=run.version,
            status=run.status.value,
            write_policy=run.write_policy.value,
            candidate_root=validation.candidate_root,
            candidate_lifecycle=run.candidate_lifecycle,
            candidate_sync_required=run.candidate_sync_required,
            candidate_sync_base_revision=run.candidate_sync_base_revision,
            current_candidate_revision=validation.candidate_revision,
            recorded_candidate_revision=run.candidate_revision,
            candidate_profile=validation.profile,
            candidate_valid=validation.valid,
            candidate_issues=list(validation.issues),
            candidate_warnings=list(validation.warnings),
            preview_id=run.preview_id,
            preview_manifest_sha256=run.preview_manifest_sha256,
            preview_conflicts=list(run.preview_conflicts),
            applied_outputs=list(run.applied_outputs),
            applied_candidate_cycles=list(run.applied_candidate_cycles),
            managed_package=self._exporter.status(run.project_root),
            resume_hint=_status_hint(run, validation),
        )


def _require_candidate_run(runs: AdaptiveWizardRunRepository, run_id: str) -> AdaptiveWizardRun:
    run = runs.find_by_id(run_id)
    if run is None:
        raise PipelineError(
            "candidate_package",
            "Wizard run을 찾을 수 없습니다.",
            "서버가 반환한 run_id를 그대로 사용하세요.",
        )
    if run.status not in _PACKAGE_STATUSES or run.write_policy is None:
        raise PipelineError(
            "candidate_package",
            f"candidate package를 만들 수 없는 Run 상태입니다: {run.status.value}",
            "2차 Wizard를 제출해 DRAFT_READY가 된 뒤 다시 시도하세요.",
        )
    if not run.candidate_root:
        raise PipelineError(
            "candidate_package",
            "이전 서버 버전의 Run에 candidate root가 없습니다.",
            "같은 2차 Wizard 호출을 다시 실행해 candidate workspace를 복구하세요.",
        )
    return run


def _assert_version(run: AdaptiveWizardRun, expected_version: int) -> None:
    if run.version != expected_version:
        raise PipelineError(
            "candidate_package",
            "Run version이 최신 상태와 다릅니다.",
            "documentation_package_status로 최신 run_version과 candidate_revision을 "
            "확인한 뒤 재시도하세요.",
        )


def _inspect(
    candidates: CandidatePackageWorkspace, run: AdaptiveWizardRun
) -> CandidatePackageInspection:
    assert run.candidate_root is not None
    return inspect_candidate_package(
        candidates.read(run.id, run.candidate_root),
        run_id=run.id,
        run_version=run.version,
    )


def _assert_candidate_revision(
    inspection: CandidatePackageInspection, requested_revision: str
) -> None:
    actual = inspection.validation.candidate_revision
    if actual != requested_revision:
        raise PipelineError(
            "candidate_package",
            "candidate_revision이 현재 candidate 본문과 다릅니다.",
            "documentation_package_status에서 current_candidate_revision을 다시 확인하세요.",
        )


def _require_valid_package(inspection: CandidatePackageInspection):  # type: ignore[no-untyped-def]
    if not inspection.validation.valid:
        raise PipelineError(
            "quality_gate",
            "; ".join(inspection.validation.issues),
            "candidate package 구조·문서 계약·추적성 오류를 고친 뒤 validate부터 다시 실행하세요.",
        )
    return package_from_inspection(inspection)


def _matches_preview(run: AdaptiveWizardRun, preview_id: str, manifest_sha256: str) -> bool:
    return run.preview_id == preview_id and run.preview_manifest_sha256 == manifest_sha256


def _preview_next_action(run: AdaptiveWizardRun) -> str:
    if run.status is AdaptiveRunStatus.CONFLICTED:
        return "충돌 파일을 보존했습니다. candidate와 preview를 전달하고 충돌을 해소하세요."
    if run.write_policy is WritePolicy.GENERATE_ONLY:
        return (
            "generate_only 정책입니다. candidate와 preview를 산출물로 제공하고 .mvpmcp는 "
            "변경하지 마세요."
        )
    return (
        "manual_apply 정책입니다. 별도 반영 요청이 있을 때만 documentation_apply_package를 "
        "호출하세요."
    )


def _applied_result(run: AdaptiveWizardRun) -> CandidatePackageApplyResult:
    return CandidatePackageApplyResult(
        run_id=run.id,
        run_version=run.version,
        candidate_revision=run.candidate_revision,
        status="APPLIED",
        preview_id=run.preview_id,
        manifest_sha256=run.preview_manifest_sha256,
        applied_outputs=list(run.applied_outputs),
        next_action=(
            "같은 preview는 이미 반영됐습니다. candidate를 수정했으면 새 revision으로 "
            "validate부터 시작하세요."
        ),
    )


def _status_hint(run: AdaptiveWizardRun, validation: CandidatePackageValidationResult) -> str:
    if run.candidate_sync_required:
        return (
            "candidate_lifecycle 구조화 계약이 변경됐습니다. candidate_root의 Markdown을 갱신한 뒤 "
            "새 current_candidate_revision으로 documentation_validate_package를 호출하세요."
        )
    if not validation.valid:
        return (
            "candidate 문서를 보완한 뒤 current_candidate_revision으로 "
            "documentation_validate_package를 호출하세요."
        )
    if run.candidate_revision != validation.candidate_revision:
        return (
            "candidate가 새로 작성되었거나 변경됐습니다. current_candidate_revision으로 "
            "validate부터 다시 시작하세요."
        )
    if run.status is AdaptiveRunStatus.CANDIDATE_VALIDATED:
        return (
            "검증된 candidate입니다. 같은 revision과 run_version으로 "
            "documentation_preview_package를 호출하세요."
        )
    if run.status is AdaptiveRunStatus.PREVIEW_READY:
        return (
            "preview가 준비됐습니다. generate_only는 결과를 제공하고 manual_apply는 "
            "별도 요청 때만 반영하세요."
        )
    if run.status is AdaptiveRunStatus.CONFLICTED:
        return (
            "충돌 파일은 보존됐습니다. 대상 파일을 해소한 뒤 같은 candidate revision으로 "
            "새 preview를 만드세요."
        )
    if run.status is AdaptiveRunStatus.APPLIED:
        return (
            "마지막 candidate revision은 반영됐습니다. 새 후보를 작성하면 validate부터 "
            "다시 시작하세요."
        )
    return "candidate를 작성한 뒤 documentation_package_status에서 revision을 확인하세요."
