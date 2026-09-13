"""Run-scoped candidate 구조화 수명주기의 쓰기 UseCase.

이 모듈은 SQLite Run snapshot만 갱신한다. 후보 Markdown이나 ``.mvpmcp/``는 직접 쓰지
않으며, 구조화 계약이 바뀌면 기존 candidate 검증·preview 결속을 무효화한다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel

from mvp_mcp.core.exceptions import PipelineError

from .adaptive_wizard_model import AdaptiveRunStatus, AdaptiveWizardRun
from .adaptive_wizard_repository import AdaptiveWizardRunRepository
from .candidate_lifecycle_model import (
    AppliedCandidateCycle,
    CandidateLifecycle,
    CandidateLifecycleMutationResult,
)
from .candidate_package_policy import inspect_candidate_package
from .model import (
    DeliveryTestCase,
    DesignContract,
    ImplementationTask,
    Priority,
    ReleaseRecord,
    ReleaseStatus,
    Requirement,
    RequirementInput,
    RequirementKind,
    VerificationEvidence,
    VerificationStatus,
)
from .ports import CandidatePackageWorkspace, Clock

_PACKAGE_STATUSES = {
    AdaptiveRunStatus.DRAFT_READY,
    AdaptiveRunStatus.CANDIDATE_VALIDATED,
    AdaptiveRunStatus.PREVIEW_READY,
    AdaptiveRunStatus.CONFLICTED,
    AdaptiveRunStatus.APPLIED,
}


class UpdateCandidateRequirementsUseCase:
    """Run의 요구사항을 stable ID upsert/replace하고 하위 계약을 무효화한다."""

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
        self,
        run_id: str,
        expected_run_version: int,
        values: list[RequirementInput],
        mode: Literal["upsert", "replace"] = "upsert",
    ) -> CandidateLifecycleMutationResult:
        run = _require_mutable_run(self._runs, run_id)
        _assert_version(run, expected_run_version)
        requirements = _updated_requirements(run.candidate_lifecycle.requirements, values, mode)
        lifecycle = run.candidate_lifecycle.model_copy(
            update={
                "lifecycle_revision": run.candidate_lifecycle.lifecycle_revision + 1,
                "requirements": requirements,
                "design_contract": None,
                "tasks": [],
                "test_cases": [],
                "verification": [],
                "releases": [],
                "verification_request_hashes": {},
                "release_request_hashes": {},
            }
        )
        return _persist_mutation(
            self._runs,
            self._candidates,
            self._clock,
            run,
            lifecycle,
            invalidated_stages=["design", "delivery", "verification", "release"],
        )


class UpdateCandidateArchitectureUseCase:
    """요구사항이 있는 Run에 상세 설계를 기록하고 전달 이후 계약을 무효화한다."""

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
        self,
        run_id: str,
        expected_run_version: int,
        contract: DesignContract,
    ) -> CandidateLifecycleMutationResult:
        run = _require_mutable_run(self._runs, run_id)
        _assert_version(run, expected_run_version)
        if not run.candidate_lifecycle.requirements:
            raise PipelineError(
                "candidate_lifecycle",
                "요구사항을 먼저 등록해야 상세 설계를 갱신할 수 있습니다.",
                "documentation_update_candidate_requirements를 먼저 호출하세요.",
            )
        lifecycle = run.candidate_lifecycle.model_copy(
            update={
                "lifecycle_revision": run.candidate_lifecycle.lifecycle_revision + 1,
                "design_contract": contract,
                "tasks": [],
                "test_cases": [],
                "verification": [],
                "releases": [],
                "verification_request_hashes": {},
                "release_request_hashes": {},
            }
        )
        return _persist_mutation(
            self._runs,
            self._candidates,
            self._clock,
            run,
            lifecycle,
            invalidated_stages=["delivery", "verification", "release"],
        )


class UpdateCandidateDeliveryUseCase:
    """TASK·TEST가 Run의 모든 요구사항을 참조하도록 전달 계약을 갱신한다."""

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
        self,
        run_id: str,
        expected_run_version: int,
        tasks: list[ImplementationTask],
        tests: list[DeliveryTestCase],
    ) -> CandidateLifecycleMutationResult:
        run = _require_mutable_run(self._runs, run_id)
        _assert_version(run, expected_run_version)
        _validate_delivery_contract(run.candidate_lifecycle, tasks, tests)
        lifecycle = run.candidate_lifecycle.model_copy(
            update={
                "lifecycle_revision": run.candidate_lifecycle.lifecycle_revision + 1,
                "tasks": tasks,
                "test_cases": tests,
                "verification": [],
                "releases": [],
                "verification_request_hashes": {},
                "release_request_hashes": {},
            }
        )
        return _persist_mutation(
            self._runs,
            self._candidates,
            self._clock,
            run,
            lifecycle,
            invalidated_stages=["verification", "release"],
        )


class RecordCandidateTestRunUseCase:
    """Run의 실제 테스트 증거를 append-only·idempotency key 규칙으로 기록한다."""

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
        self,
        run_id: str,
        expected_run_version: int,
        evidence: list[VerificationEvidence],
        idempotency_key: str,
    ) -> CandidateLifecycleMutationResult:
        run = _require_mutable_run(self._runs, run_id)
        payload_hash = _payload_hash(evidence)
        replay = _replay_or_reject(
            run.candidate_lifecycle.verification_request_hashes,
            idempotency_key,
            payload_hash,
            run,
        )
        if replay is not None:
            return replay
        _assert_version(run, expected_run_version)
        lifecycle = run.candidate_lifecycle
        valid_ids = {item.id for item in lifecycle.test_cases}
        if not evidence or any(item.test_id not in valid_ids for item in evidence):
            raise PipelineError(
                "candidate_lifecycle",
                "검증 결과가 Run의 TEST 계약과 연결되지 않습니다.",
                "documentation_update_candidate_delivery로 TEST-ID를 확정한 뒤 기록하세요.",
            )
        existing = {
            (item.test_id, item.executed_at, item.status) for item in lifecycle.verification
        }
        additions = [
            item
            for item in evidence
            if (item.test_id, item.executed_at, item.status) not in existing
        ]
        if not additions:
            return _unchanged_result(run, "같은 테스트 증거가 이미 Run에 기록되어 있습니다.")
        hashes = {**lifecycle.verification_request_hashes, idempotency_key: payload_hash}
        updated = lifecycle.model_copy(
            update={
                "lifecycle_revision": lifecycle.lifecycle_revision + 1,
                "verification": [*lifecycle.verification, *additions],
                "verification_request_hashes": hashes,
            }
        )
        return _persist_mutation(
            self._runs,
            self._candidates,
            self._clock,
            run,
            updated,
            recorded_count=len(additions),
        )


class RecordCandidateReleaseUseCase:
    """PASS 증거가 충족된 Run에 append-only 릴리스/롤백 기록을 추가한다."""

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
        self,
        run_id: str,
        expected_run_version: int,
        record: ReleaseRecord,
        idempotency_key: str,
    ) -> CandidateLifecycleMutationResult:
        run = _require_mutable_run(self._runs, run_id)
        payload_hash = _payload_hash(record)
        replay = _replay_or_reject(
            run.candidate_lifecycle.release_request_hashes,
            idempotency_key,
            payload_hash,
            run,
        )
        if replay is not None:
            return replay
        _assert_version(run, expected_run_version)
        lifecycle = run.candidate_lifecycle
        if any(item.id == record.id for item in lifecycle.releases):
            raise PipelineError(
                "candidate_lifecycle",
                "이미 사용한 REL ID입니다.",
                "새 날짜·일련번호의 REL ID를 사용하세요.",
            )
        _assert_release_gate(lifecycle, record)
        hashes = {**lifecycle.release_request_hashes, idempotency_key: payload_hash}
        updated = lifecycle.model_copy(
            update={
                "lifecycle_revision": lifecycle.lifecycle_revision + 1,
                "releases": [*lifecycle.releases, record],
                "release_request_hashes": hashes,
            }
        )
        return _persist_mutation(
            self._runs,
            self._candidates,
            self._clock,
            run,
            updated,
            release_id=record.id,
            recorded_count=1,
        )


def _require_mutable_run(runs: AdaptiveWizardRunRepository, run_id: str) -> AdaptiveWizardRun:
    run = runs.find_by_id(run_id)
    if run is None:
        raise PipelineError(
            "candidate_lifecycle",
            "Wizard run을 찾을 수 없습니다.",
            "서버가 반환한 run_id를 그대로 사용하세요.",
        )
    if run.status not in _PACKAGE_STATUSES or run.write_policy is None or not run.candidate_root:
        raise PipelineError(
            "candidate_lifecycle",
            f"후보 수명주기를 갱신할 수 없는 Run 상태입니다: {run.status.value}",
            "2차 Wizard를 제출해 DRAFT_READY와 candidate_root를 만든 뒤 다시 시도하세요.",
        )
    return run


def _assert_version(run: AdaptiveWizardRun, expected_run_version: int) -> None:
    if run.version != expected_run_version:
        raise PipelineError(
            "candidate_lifecycle",
            "Run version이 최신 상태와 다릅니다.",
            "documentation_package_status에서 최신 run_version을 읽은 뒤 재시도하세요.",
        )


def _updated_requirements(
    existing: list[Requirement],
    values: list[RequirementInput],
    mode: Literal["upsert", "replace"],
) -> list[Requirement]:
    if not values:
        raise PipelineError(
            "candidate_lifecycle", "요구사항이 비어 있습니다.", "P0 요구사항을 등록하세요."
        )
    incomplete_p0 = [
        item.title
        for item in values
        if item.priority is Priority.P0 and len(item.acceptance_criteria) < 2
    ]
    if incomplete_p0:
        raise PipelineError(
            "candidate_lifecycle",
            f"P0 요구사항의 수용 기준이 부족합니다: {', '.join(incomplete_p0)}",
            "P0 요구사항마다 수용 기준을 2개 이상 등록하세요.",
        )
    existing_by_key = {(item.kind, item.title.casefold()): item for item in existing}
    counters = _requirement_counters(existing)
    incoming: list[Requirement] = []
    for value in values:
        current = existing_by_key.get((value.kind, value.title.casefold()))
        if current is not None:
            incoming.append(Requirement(id=current.id, **value.model_dump()))
            continue
        counters[value.kind] += 1
        incoming.append(
            Requirement(id=f"{value.kind.value}-{counters[value.kind]:03d}", **value.model_dump())
        )
    if mode == "replace":
        return incoming
    incoming_keys = {(item.kind, item.title.casefold()) for item in incoming}
    return [
        item for item in existing if (item.kind, item.title.casefold()) not in incoming_keys
    ] + incoming


def _requirement_counters(requirements: list[Requirement]) -> dict[RequirementKind, int]:
    counters = {kind: 0 for kind in RequirementKind}
    for item in requirements:
        suffix = item.id.rsplit("-", 1)[-1]
        if suffix.isdigit():
            counters[item.kind] = max(counters[item.kind], int(suffix))
    return counters


def _validate_delivery_contract(
    lifecycle: CandidateLifecycle,
    tasks: list[ImplementationTask],
    tests: list[DeliveryTestCase],
) -> None:
    if not lifecycle.requirements or lifecycle.design_contract is None:
        raise PipelineError(
            "candidate_lifecycle",
            "요구사항과 설계를 확정한 뒤에만 전달 계약을 등록할 수 있습니다.",
            "documentation_update_candidate_requirements와 architecture를 먼저 호출하세요.",
        )
    task_ids = [item.id for item in tasks]
    test_ids = [item.id for item in tests]
    if len(task_ids) != len(set(task_ids)):
        raise PipelineError(
            "candidate_lifecycle", "중복된 TASK-ID가 있습니다.", "TASK-ID를 고유하게 지정하세요."
        )
    if len(test_ids) != len(set(test_ids)):
        raise PipelineError(
            "candidate_lifecycle", "중복된 TEST-ID가 있습니다.", "TEST-ID를 고유하게 지정하세요."
        )
    requirement_ids = {item.id for item in lifecycle.requirements}
    task_refs = {reference for task in tasks for reference in task.requirement_ids}
    test_refs = {reference for test in tests for reference in test.requirement_ids}
    if (
        not tasks
        or not tests
        or not task_refs <= requirement_ids
        or not test_refs <= requirement_ids
        or requirement_ids - task_refs
        or requirement_ids - test_refs
    ):
        raise PipelineError(
            "candidate_lifecycle",
            "작업·테스트의 요구사항 연결이 올바르지 않습니다.",
            "모든 요구사항을 BIZ/FR/NFR/DATA/SEC ID로 TASK와 TEST에 연결하세요.",
        )


def _assert_release_gate(lifecycle: CandidateLifecycle, record: ReleaseRecord) -> None:
    if not lifecycle.test_cases:
        raise PipelineError(
            "release_gate",
            "릴리스 기록 전에 Run의 TEST 계약을 확정해야 합니다.",
            "documentation_update_candidate_delivery를 먼저 호출하세요.",
        )
    if record.status is not ReleaseStatus.RELEASED:
        return
    latest: dict[str, VerificationEvidence] = {}
    for item in lifecycle.verification:
        latest[item.test_id] = item
    missing = [
        test.id
        for test in lifecycle.test_cases
        if test.id not in latest or latest[test.id].status is not VerificationStatus.PASS
    ]
    if missing:
        raise PipelineError(
            "release_gate",
            f"PASS가 아닌 필수 테스트가 있습니다: {', '.join(missing)}",
            "TEST_PLAN에 실제 PASS 증거를 기록한 뒤 릴리스를 등록하세요.",
        )


def _payload_hash(value: object) -> str:
    encoded = json.dumps(
        _json_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _replay_or_reject(
    request_hashes: dict[str, str],
    idempotency_key: str,
    payload_hash: str,
    run: AdaptiveWizardRun,
) -> CandidateLifecycleMutationResult | None:
    key = idempotency_key.strip()
    if not key:
        raise PipelineError(
            "candidate_lifecycle",
            "idempotency_key가 비어 있습니다.",
            "호출별 고유 key를 제공하세요.",
        )
    previous = request_hashes.get(key)
    if previous is None:
        return None
    if previous != payload_hash:
        raise PipelineError(
            "candidate_lifecycle",
            "같은 idempotency_key에 다른 payload를 사용할 수 없습니다.",
            "새 실행에는 새 idempotency_key를 사용하세요.",
        )
    return CandidateLifecycleMutationResult(
        run_id=run.id,
        run_version=run.version,
        lifecycle_revision=run.candidate_lifecycle.lifecycle_revision,
        status=run.status.value,
        candidate_sync_required=run.candidate_sync_required,
        replayed=True,
        next_action=(
            "같은 idempotency_key의 기록이 이미 저장됐습니다. 최신 Run 상태를 그대로 사용하세요."
        ),
    )


def _unchanged_result(run: AdaptiveWizardRun, next_action: str) -> CandidateLifecycleMutationResult:
    return CandidateLifecycleMutationResult(
        run_id=run.id,
        run_version=run.version,
        lifecycle_revision=run.candidate_lifecycle.lifecycle_revision,
        status=run.status.value,
        candidate_sync_required=run.candidate_sync_required,
        replayed=True,
        next_action=next_action,
    )


def _persist_mutation(
    runs: AdaptiveWizardRunRepository,
    candidates: CandidatePackageWorkspace,
    clock: Clock,
    run: AdaptiveWizardRun,
    lifecycle: CandidateLifecycle,
    *,
    invalidated_stages: list[str] | None = None,
    recorded_count: int = 0,
    release_id: str | None = None,
) -> CandidateLifecycleMutationResult:
    baseline_revision = _current_candidate_revision(candidates, run)
    history = list(run.applied_candidate_cycles)
    if run.status is AdaptiveRunStatus.APPLIED:
        assert run.candidate_revision is not None
        assert run.preview_id is not None
        assert run.preview_manifest_sha256 is not None
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
    updated = run.model_copy(
        update={
            "status": AdaptiveRunStatus.DRAFT_READY,
            "candidate_lifecycle": lifecycle,
            "candidate_sync_required": True,
            "candidate_sync_base_revision": baseline_revision,
            "candidate_revision": None,
            "candidate_profile": None,
            "preview_id": None,
            "preview_manifest_sha256": None,
            "preview_candidate_revision": None,
            "preview_conflicts": [],
            "applied_outputs": [],
            "applied_candidate_cycles": history,
            "version": run.version + 1,
            "updated_at": clock.now(),
        }
    )
    saved = runs.save(updated, expected_version=run.version)
    return CandidateLifecycleMutationResult(
        run_id=saved.id,
        run_version=saved.version,
        lifecycle_revision=lifecycle.lifecycle_revision,
        status=saved.status.value,
        candidate_sync_required=True,
        invalidated_stages=invalidated_stages or [],
        requirement_ids=[item.id for item in lifecycle.requirements],
        task_ids=[item.id for item in lifecycle.tasks],
        test_ids=[item.id for item in lifecycle.test_cases],
        recorded_count=recorded_count,
        release_id=release_id,
        next_action=(
            "candidate_root의 Markdown에 최신 candidate_lifecycle를 반영한 뒤 "
            "documentation_package_status에서 새 candidate_revision을 확인하고 "
            "documentation_validate_package를 호출하세요."
        ),
    )


def _current_candidate_revision(
    candidates: CandidatePackageWorkspace, run: AdaptiveWizardRun
) -> str:
    assert run.candidate_root is not None
    inspection = inspect_candidate_package(
        candidates.read(run.id, run.candidate_root),
        run_id=run.id,
        run_version=run.version,
    )
    return inspection.validation.candidate_revision
