"""Run-scoped candidate 수명주기·동시성·후보 재검증 회귀 테스트."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardQuestion,
    AdaptiveWizardRun,
    WizardQuestionKind,
    WritePolicy,
    make_submission,
)
from mvp_mcp.domain.spec.candidate_lifecycle_usecase import (
    RecordCandidateReleaseUseCase,
    RecordCandidateTestRunUseCase,
    UpdateCandidateArchitectureUseCase,
    UpdateCandidateDeliveryUseCase,
    UpdateCandidateRequirementsUseCase,
)
from mvp_mcp.domain.spec.documentation_model import DocumentProfile
from mvp_mcp.domain.spec.model import (
    DeliveryTestCase,
    DesignContract,
    ImplementationTask,
    Priority,
    ReleaseRecord,
    ReleaseStatus,
    RequirementInput,
    VerificationEvidence,
    VerificationStatus,
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 13, tzinfo=UTC)


def _wire(tmp_path: Path) -> tuple[
    AdaptiveWizardRun,
    SqliteAdaptiveWizardRunRepository,
    CandidatePackageRepository,
    UpdateCandidateRequirementsUseCase,
    UpdateCandidateArchitectureUseCase,
    UpdateCandidateDeliveryUseCase,
    RecordCandidateTestRunUseCase,
    RecordCandidateReleaseUseCase,
]:
    clock = _FixedClock()
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    candidates = CandidatePackageRepository(str(tmp_path / "server-output"))
    root = candidates.ensure_workspace("run-lifecycle-0001")
    intake_questions = [
        AdaptiveWizardQuestion(
            id="write_policy",
            label="반영 정책",
            kind=WizardQuestionKind.SELECT,
            options=[WritePolicy.GENERATE_ONLY.value],
        )
    ]
    design_questions = [
        AdaptiveWizardQuestion(
            id=f"design_{index}", label=f"설계 {index}", kind=WizardQuestionKind.TEXT
        )
        for index in range(1, 4)
    ]
    run = AdaptiveWizardRun(
        id="run-lifecycle-0001",
        request_key="lifecycle-request-0001",
        user_request="후보 수명주기를 관리한다",
        project_root=str(tmp_path / "project"),
        status=AdaptiveRunStatus.DRAFT_READY,
        write_policy=WritePolicy.GENERATE_ONLY,
        version=4,
        intake_questions=intake_questions,
        intake_submission=make_submission(
            "sub-intake-lifecycle-0001",
            intake_questions,
            {"write_policy": WritePolicy.GENERATE_ONLY.value},
            clock.now(),
        ),
        design_questions=design_questions,
        design_submission=make_submission(
            "sub-design-lifecycle-0001",
            design_questions,
            {item.id: "확정" for item in design_questions},
            clock.now(),
        ),
        spec_id="adaptive-run-lifecycle-0001",
        candidate_root=root,
        created_at=clock.now(),
        updated_at=clock.now(),
    )
    runs.create_or_get(run)
    return (
        run,
        runs,
        candidates,
        UpdateCandidateRequirementsUseCase(runs, candidates, clock),
        UpdateCandidateArchitectureUseCase(runs, candidates, clock),
        UpdateCandidateDeliveryUseCase(runs, candidates, clock),
        RecordCandidateTestRunUseCase(runs, candidates, clock),
        RecordCandidateReleaseUseCase(runs, candidates, clock),
    )


def _requirements() -> list[RequirementInput]:
    return [
        RequirementInput(
            title="후보 수명주기를 Run에 저장한다",
            description="요구사항·설계·전달 기록은 서버 재시작 뒤에도 남는다.",
            priority=Priority.P0,
            acceptance_criteria=["run_id로 상태를 읽는다", "서버 재시작 뒤 상태가 유지된다"],
        )
    ]


def _delivery() -> tuple[list[ImplementationTask], list[DeliveryTestCase]]:
    return (
        [
            ImplementationTask(
                id="TASK-001",
                requirement_ids=["FR-001"],
                title="Run lifecycle 저장 구현",
                file_scope=["src/mvp_mcp/domain/spec/candidate_lifecycle_usecase.py"],
                done_when=["SQLite Run을 다시 열어도 lifecycle이 남는다"],
            )
        ],
        [
            DeliveryTestCase(
                id="TEST-001",
                requirement_ids=["FR-001"],
                scenario="서버 재시작 뒤 Run lifecycle을 조회한다",
                expected_result="동일 요구사항과 TEST 계약을 반환한다",
                kind="automated",
            )
        ],
    )


def _pass_evidence() -> list[VerificationEvidence]:
    return [
        VerificationEvidence(
            test_id="TEST-001",
            status=VerificationStatus.PASS,
            evidence="pytest tests/test_candidate_lifecycle.py",
            executor="codex",
            executed_at=datetime(2026, 9, 13, tzinfo=UTC),
            evidence_path="tests/test_candidate_lifecycle.py",
        )
    ]


def test_run_scoped_lifecycle_persists_all_five_contracts(tmp_path: Path) -> None:
    run, runs, _candidates, requirements, architecture, delivery, test_run, release = _wire(
        tmp_path
    )

    requirement_result = requirements(run.id, run.version, _requirements())
    assert requirement_result.requirement_ids == ["FR-001"]
    assert requirement_result.candidate_sync_required

    architecture_result = architecture(run.id, requirement_result.run_version, DesignContract())
    tasks, tests = _delivery()
    delivery_result = delivery(run.id, architecture_result.run_version, tasks, tests)
    test_result = test_run(run.id, delivery_result.run_version, _pass_evidence(), "test-run-0001")
    release_result = release(
        run.id,
        test_result.run_version,
        ReleaseRecord(
            id="REL-20260913-01",
            status=ReleaseStatus.RELEASED,
            commit="abc1234",
            artifact="dist/mvp-mcp.whl",
            checksum_sha256="a" * 64,
            executor="codex",
            executed_at=datetime(2026, 9, 13, tzinfo=UTC),
            evidence="release checklist",
        ),
        "release-run-0001",
    )

    restored = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3").find_by_id(
        run.id
    )
    assert restored is not None
    assert restored.version == release_result.run_version
    assert restored.candidate_lifecycle.lifecycle_revision == 5
    assert restored.candidate_lifecycle.requirements[0].id == "FR-001"
    assert restored.candidate_lifecycle.test_cases[0].id == "TEST-001"
    assert restored.candidate_lifecycle.verification[0].status is VerificationStatus.PASS
    assert restored.candidate_lifecycle.releases[0].id == "REL-20260913-01"
    assert restored.candidate_sync_required


def test_lifecycle_rejects_stale_run_and_invalidates_downstream_contracts(tmp_path: Path) -> None:
    run, runs, _candidates, requirements, architecture, delivery, test_run, _release = _wire(
        tmp_path
    )
    first = requirements(run.id, run.version, _requirements())
    second = architecture(run.id, first.run_version, DesignContract())
    tasks, tests = _delivery()
    third = delivery(run.id, second.run_version, tasks, tests)
    fourth = test_run(run.id, third.run_version, _pass_evidence(), "test-run-0002")

    with pytest.raises(PipelineError, match="Run version"):
        architecture(run.id, first.run_version, DesignContract())

    changed = requirements(
        run.id,
        fourth.run_version,
        [
            RequirementInput(
                title="후보 수명주기를 Run에 저장한다",
                description="수정된 요구사항은 이후 계약을 재검토시킨다.",
                priority=Priority.P0,
                acceptance_criteria=["수정한다", "하위 계약을 비운다"],
            )
        ],
    )
    saved = runs.find_by_id(run.id)
    assert saved is not None
    assert changed.invalidated_stages == ["design", "delivery", "verification", "release"]
    assert saved.candidate_lifecycle.design_contract is None
    assert saved.candidate_lifecycle.tasks == []
    assert saved.candidate_lifecycle.verification == []


def test_test_record_idempotency_replays_without_new_version(tmp_path: Path) -> None:
    run, _runs, _candidates, requirements, architecture, delivery, test_run, _release = _wire(
        tmp_path
    )
    first = requirements(run.id, run.version, _requirements())
    second = architecture(run.id, first.run_version, DesignContract())
    tasks, tests = _delivery()
    third = delivery(run.id, second.run_version, tasks, tests)
    recorded = test_run(run.id, third.run_version, _pass_evidence(), "test-run-0003")

    replayed = test_run(run.id, third.run_version, _pass_evidence(), "test-run-0003")
    assert replayed.replayed
    assert replayed.run_version == recorded.run_version
    changed_evidence = _pass_evidence()
    changed_evidence[0] = changed_evidence[0].model_copy(update={"evidence": "other"})
    with pytest.raises(PipelineError, match="idempotency_key"):
        test_run(run.id, recorded.run_version, changed_evidence, "test-run-0003")


def test_applied_run_starts_new_candidate_cycle_without_losing_apply_history(
    tmp_path: Path,
) -> None:
    run, runs, _candidates, requirements, _architecture, _delivery, _test_run, _release = _wire(
        tmp_path
    )
    applied = run.model_copy(
        update={
            "status": AdaptiveRunStatus.APPLIED,
            "candidate_revision": "b" * 64,
            "candidate_profile": DocumentProfile.MVP_6,
            "preview_id": "preview-lifecycle-0001",
            "preview_manifest_sha256": "c" * 64,
            "preview_candidate_revision": "b" * 64,
            "applied_outputs": ["docs/REQUIREMENTS.md"],
            "version": run.version + 1,
        }
    )
    runs.save(applied, expected_version=run.version)

    updated = requirements(applied.id, applied.version, _requirements())
    saved = runs.find_by_id(applied.id)
    assert saved is not None
    assert updated.status == AdaptiveRunStatus.DRAFT_READY.value
    assert saved.applied_outputs == []
    assert saved.applied_candidate_cycles[0].candidate_revision == "b" * 64
    assert saved.applied_candidate_cycles[0].applied_outputs == ["docs/REQUIREMENTS.md"]
