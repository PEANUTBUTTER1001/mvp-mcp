"""요구사항·작업·테스트·실행 증거 계약 테스트."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.domain.spec.model import (
    DeliveryTestCase,
    ImplementationTask,
    Priority,
    ProjectType,
    ReleaseRecord,
    ReleaseStatus,
    RequirementInput,
    SpecDraft,
    VerificationEvidence,
    VerificationStatus,
)
from mvp_mcp.domain.spec.usecase import (
    ConfirmScopeUseCase,
    RecordReleaseUseCase,
    RecordVerificationUseCase,
    RegisterDeliveryContractUseCase,
    RegisterRequirementsUseCase,
)


def _draft(repo: InMemorySpecRepository, root: Path) -> str:
    return repo.save(
        SpecDraft(
            project_type=ProjectType.ETC,
            user_request="식당 평가 앱",
            project_root=str(root),
            status="scoped",
        )
    )


def _requirements(repo: InMemorySpecRepository, spec_id: str) -> list[str]:
    draft = RegisterRequirementsUseCase(repo)(
        spec_id,
        [
            RequirementInput(
                title="평가 저장",
                description="평가를 저장한다.",
                priority=Priority.P0,
                acceptance_criteria=["유효한 평가가 저장된다.", "범위 밖 점수는 거부된다."],
            )
        ],
    )
    return [item.id for item in draft.requirements]


def _delivery(repo: InMemorySpecRepository, spec_id: str) -> None:
    requirement_ids = _requirements(repo, spec_id)
    ConfirmScopeUseCase(repo)(spec_id)
    RegisterDeliveryContractUseCase(repo)(
        spec_id,
        [
            ImplementationTask(
                id="TASK-001",
                requirement_ids=requirement_ids,
                title="평가 저장 구현",
                file_scope=["src/reviews.py"],
                done_when=["TEST-001 통과"],
            )
        ],
        [
            DeliveryTestCase(
                id="TEST-001",
                requirement_ids=requirement_ids,
                scenario="유효한 평가 저장",
                expected_result="저장 성공",
                kind="automated",
            )
        ],
    )


def test_p0_requires_two_acceptance_criteria(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    with pytest.raises(PipelineError, match="수용 기준"):
        RegisterRequirementsUseCase(repo)(
            spec_id,
            [
                RequirementInput(
                    title="평가 저장",
                    description="저장한다.",
                    priority=Priority.P0,
                    acceptance_criteria=["저장된다."],
                )
            ],
        )


def test_delivery_requires_every_requirement_reference(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    requirement_ids = _requirements(repo, spec_id)
    ConfirmScopeUseCase(repo)(spec_id)
    with pytest.raises(PipelineError, match="연결"):
        RegisterDeliveryContractUseCase(repo)(
            spec_id,
            [
                ImplementationTask(
                    id="TASK-001",
                    requirement_ids=requirement_ids,
                    title="평가 저장",
                    file_scope=["app.py"],
                    done_when=["완료"],
                )
            ],
            [],
        )


def test_confirmed_requirements_can_be_upserted_without_losing_stable_ids(
    tmp_path: Path,
) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    original_ids = _requirements(repo, spec_id)
    ConfirmScopeUseCase(repo)(spec_id)

    updated = RegisterRequirementsUseCase(repo)(
        spec_id,
        [
            RequirementInput(
                title="결과 비교",
                description="두 실행 결과를 비교한다.",
                priority=Priority.P0,
                acceptance_criteria=["두 결과가 표시된다.", "지표 차이가 표시된다."],
            )
        ],
    )

    assert [item.id for item in updated.requirements] == [*original_ids, "FR-002"]
    assert updated.scope_confirmed
    assert updated.status == "confirmed"
    assert updated.revision == 2
    assert updated.tasks == []
    assert updated.test_cases == []


def test_requirement_registration_rejects_collecting_state_without_partial_write(
    tmp_path: Path,
) -> None:
    repo = InMemorySpecRepository()
    spec_id = repo.save(
        SpecDraft(
            project_type=ProjectType.ETC,
            user_request="초기 요청",
            project_root=str(tmp_path),
        )
    )
    with pytest.raises(PipelineError, match="범위를 먼저"):
        _requirements(repo, spec_id)

    stored = repo.find_by_id(spec_id)
    assert stored is not None
    assert stored.requirements == []


def test_pass_verification_requires_complete_evidence() -> None:
    with pytest.raises(ValueError, match="근거"):
        VerificationEvidence(test_id="TEST-001", status=VerificationStatus.PASS)


def test_verification_is_append_only_and_rejects_unknown_test(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    with pytest.raises(PipelineError, match="테스트 계약"):
        RecordVerificationUseCase(repo)(
            spec_id,
            [
                VerificationEvidence(
                    test_id="TEST-001", status=VerificationStatus.FAIL, evidence="실패 로그"
                )
            ],
        )
    _delivery(repo, spec_id)
    first = VerificationEvidence(
        test_id="TEST-001",
        status=VerificationStatus.PASS,
        evidence="pytest 통과",
        executor="test-agent",
        executed_at=datetime(2026, 9, 10, 12, 0),
        evidence_path="artifacts/pytest.txt",
    )
    updated = RecordVerificationUseCase(repo)(spec_id, [first])
    assert updated.verification == [first]
    assert RecordVerificationUseCase(repo)(spec_id, [first]).verification == [first]


def test_release_requires_all_tests_passed(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _delivery(repo, spec_id)
    released = ReleaseRecord(
        id="REL-20260910-01",
        status=ReleaseStatus.RELEASED,
        commit="abc123",
        artifact="app.whl",
        checksum_sha256="123",
        executor="release-owner",
        executed_at=datetime(2026, 9, 10, 12, 0),
        evidence="배포 로그",
    )
    with pytest.raises(PipelineError, match="PASS가 아닌"):
        RecordReleaseUseCase(repo)(spec_id, released)
