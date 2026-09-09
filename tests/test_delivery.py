"""6문서 실행 계약과 프로젝트 루트 저장 테스트."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.markdown_document_exporter import ProjectMvpBundleExporter
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.domain.spec.model import (
    BusinessRule,
    DataEntity,
    DeliveryTestCase,
    DesignContract,
    ErrorState,
    ExportedMvpBundle,
    ImplementationTask,
    InterfaceContract,
    MvpBundleRequest,
    Priority,
    ProjectType,
    RequirementInput,
    ScreenSpec,
    SpecDraft,
    UserFlow,
    VerificationEvidence,
    VerificationStatus,
)
from mvp_mcp.domain.spec.usecase import (
    ConfirmScopeUseCase,
    ExportMvpBundleUseCase,
    GetMvpBundleContextUseCase,
    RecordVerificationUseCase,
    RegisterDeliveryContractUseCase,
    RegisterDesignContractUseCase,
    RegisterRequirementsUseCase,
    ValidateMvpBundleUseCase,
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


def _design_contract() -> DesignContract:
    return DesignContract(
        screens=[
            ScreenSpec(
                name="식당 목록",
                route="/restaurants",
                purpose="저장한 식당을 찾는다.",
                ui_elements=["검색 입력", "평가 카드"],
                states=["기본", "빈 목록", "오류"],
            )
        ],
        user_flows=[UserFlow(name="평가 저장", steps=["평가 입력", "저장", "목록 확인"])],
        data_entities=[
            DataEntity(
                name="RestaurantReview",
                fields=["id: UUID", "rating: integer", "review: text"],
                constraints=["id는 PK", "rating은 1~5"],
            )
        ],
        interfaces=[
            InterfaceContract(
                name="평가 저장 API",
                kind="HTTP API",
                purpose="평가를 저장한다.",
                input_summary="식당명, 평점, 후기",
                output_summary="저장된 평가 ID",
                error_cases=["평점 누락", "허용 범위 초과"],
            )
        ],
        business_rules=[
            BusinessRule(
                title="평점 범위",
                rule="평점은 1부터 5까지의 정수만 허용한다.",
                rationale="평가 데이터의 일관성을 보장한다.",
            )
        ],
        error_states=[
            ErrorState(
                trigger="저장 실패",
                user_message="평가를 저장하지 못했습니다.",
                recovery="입력 내용을 유지한 채 다시 시도한다.",
            )
        ],
    )


def _bundle(spec_id: str, proposal: str = "기획서") -> MvpBundleRequest:
    return MvpBundleRequest(
        spec_id=spec_id,
        requirements_markdown="""# 요구사항
## 기능 요구사항
- REQ-001 평가 저장
## 비기능 요구사항
- 입력 검증
## 수용 기준
- REQ-001 기준 2건
## 가정 및 미확정 결정
- 로그인 정책은 추후 결정
""",
        proposal_markdown=f"""# {proposal}
## 배경 및 문제 정의
## 목표 및 기대 효과
## 대상 사용자 및 사용 시나리오
## 핵심 가치 제안
## MVP 범위
## 성공 지표
## 리스크 및 가정
""",
        plan_markdown="""# 구현 계획
## 확정 정책
## 기술 스택
## 화면 목록 및 상태
## 사용자 플로우
## 데이터 모델
## API 및 인터페이스 계약
## 업무 규칙
## 오류 및 복구
## 책임 분리 및 폴더 구조
""",
        backlog_markdown="""# 구현 백로그
## 구현 순서
평가 API 구현을 먼저 진행한다.
## 작업 상세
| ID | 내용 |
|---|---|
| TASK-001 | 평가 API 구현 |
## 완료 조건
""",
        test_plan_markdown="""# 테스트 계획
## 테스트 데이터 및 사전 조건
## 정상 시나리오
| ID | 시나리오 |
|---|---|
| TEST-001 | 정상 저장 |
## 경계 및 실패 시나리오
| ID | 시나리오 |
|---|---|
| TEST-002 | 범위 밖 점수 |
## 증거 수집 방법
""",
    )


def _register_complete_contract(repo: InMemorySpecRepository, spec_id: str) -> None:
    requirement = RegisterRequirementsUseCase(repo)(
        spec_id,
        [
            RequirementInput(
                title="평가 저장",
                description="체크리스트 평가를 저장한다.",
                priority=Priority.P0,
                acceptance_criteria=[
                    "필수 점수를 입력하면 저장된다.",
                    "1~5 이외의 점수는 저장되지 않는다.",
                ],
            )
        ],
    ).requirements[0]
    ConfirmScopeUseCase(repo)(spec_id)
    RegisterDesignContractUseCase(repo)(spec_id, _design_contract())
    RegisterDeliveryContractUseCase(repo)(
        spec_id,
        [
            ImplementationTask(
                id="TASK-001",
                requirement_ids=[requirement.id],
                title="평가 API 구현",
                file_scope=["src/reviews.py"],
                done_when=["저장 API 테스트 통과"],
            )
        ],
        [
            DeliveryTestCase(
                id="TEST-001",
                requirement_ids=[requirement.id],
                scenario="필수 점수로 평가 저장",
                expected_result="201 응답",
                kind="automated",
                case_type="normal",
            ),
            DeliveryTestCase(
                id="TEST-002",
                requirement_ids=[requirement.id],
                scenario="0점 입력 거부",
                expected_result="입력 오류",
                kind="automated",
                case_type="boundary",
            ),
        ],
    )


class _FailingBundleExporter:
    def export(
        self, project_root: str, request: MvpBundleRequest, verification: str
    ) -> ExportedMvpBundle:
        raise OSError("disk full")


def test_bundle_requires_complete_contract_and_writes_six_files(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)

    result = ExportMvpBundleUseCase(repo, ProjectMvpBundleExporter())(_bundle(spec_id))

    assert set(result.paths) == {
        "requirements.md",
        "proposal.md",
        "plan.md",
        "backlog.md",
        "test-plan.md",
        "verification-report.md",
    }
    for filename in result.paths:
        assert (tmp_path / "mvpmcp" / filename).is_file()
    assert "## 화면 목록 및 상태" in (tmp_path / "mvpmcp" / "plan.md").read_text(encoding="utf-8")
    assert "NOT_RUN" in (tmp_path / "mvpmcp" / "verification-report.md").read_text(encoding="utf-8")


def test_reexport_replaces_only_the_six_named_documents(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)
    use_case = ExportMvpBundleUseCase(repo, ProjectMvpBundleExporter())
    use_case(_bundle(spec_id))
    keep = tmp_path / "mvpmcp" / "keep.md"
    keep.write_text("preserve", encoding="utf-8")

    use_case(_bundle(spec_id, proposal="새 기획서"))

    assert "# 새 기획서" in (tmp_path / "mvpmcp" / "proposal.md").read_text(encoding="utf-8")
    assert keep.read_text(encoding="utf-8") == "preserve"


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


def test_delivery_contract_requires_every_requirement_to_have_task_and_test(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    requirements = RegisterRequirementsUseCase(repo)(
        spec_id,
        [
            RequirementInput(
                title="평가 저장",
                description="저장한다.",
                priority=Priority.P0,
                acceptance_criteria=["저장된다.", "범위 밖 값은 거부된다."],
            ),
            RequirementInput(
                title="방문 기록",
                description="방문 날짜를 남긴다.",
                priority=Priority.P1,
                acceptance_criteria=["날짜가 저장된다."],
            ),
        ],
    )
    ConfirmScopeUseCase(repo)(spec_id)

    with pytest.raises(PipelineError, match="연결"):
        RegisterDeliveryContractUseCase(repo)(
            spec_id,
            [
                ImplementationTask(
                    id="TASK-001",
                    requirement_ids=[requirements.requirements[0].id],
                    title="평가 저장",
                    file_scope=["app.py"],
                    done_when=["완료"],
                )
            ],
            [
                DeliveryTestCase(
                    id="TEST-001",
                    requirement_ids=[requirements.requirements[0].id],
                    scenario="저장",
                    expected_result="성공",
                    kind="manual",
                )
            ],
        )


def test_validator_reports_missing_document_sections(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)
    incomplete = _bundle(spec_id).model_copy(update={"plan_markdown": "# 구현 계획"})

    result = ValidateMvpBundleUseCase(repo)(incomplete)

    assert not result.passed
    assert any("plan_markdown 필수 섹션 누락" in issue for issue in result.issues)


def test_validator_rejects_duplicate_test_id_in_document(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)
    duplicate = _bundle(spec_id).model_copy(
        update={
            "test_plan_markdown": _bundle(spec_id).test_plan_markdown.replace(
                "| TEST-002 | 범위 밖 점수 |", "| TEST-001 | 범위 밖 점수 |"
            )
        }
    )

    result = ValidateMvpBundleUseCase(repo)(duplicate)

    assert not result.passed
    assert any("중복된 TEST-ID" in issue for issue in result.issues)


def test_bundle_context_contains_detailed_contract_and_required_sections(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)

    context = GetMvpBundleContextUseCase(repo, _TemplateRepo())(spec_id)

    assert "식당 목록" in context
    assert "## 기술 스택" in context
    assert "백슬래시 이스케이프(`\\~`)" in context
    assert "## plan.md 필수 섹션" in context
    assert "REQ-001" in context


class _TemplateRepo:
    def get(self, project_type: ProjectType):  # type: ignore[no-untyped-def]
        from mvp_mcp.domain.spec.templates_data import TEMPLATES

        return TEMPLATES[project_type]


def test_pass_verification_requires_complete_evidence() -> None:
    with pytest.raises(ValueError, match="근거"):
        VerificationEvidence(test_id="TEST-001", status=VerificationStatus.PASS)

    evidence = VerificationEvidence(
        test_id="TEST-001",
        status=VerificationStatus.PASS,
        evidence="pytest 통과",
        executor="test-agent",
        executed_at=datetime(2026, 9, 8, 13, 0),
        evidence_path="artifacts/pytest.txt",
    )
    assert evidence.status is VerificationStatus.PASS


def test_bundle_write_failure_becomes_pipeline_error(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    _register_complete_contract(repo, spec_id)

    with pytest.raises(PipelineError, match="disk full") as exc_info:
        ExportMvpBundleUseCase(repo, _FailingBundleExporter())(_bundle(spec_id))

    assert exc_info.value.stage == "export"


def test_verification_rejects_unknown_test_id(tmp_path: Path) -> None:
    repo = InMemorySpecRepository()
    spec_id = _draft(repo, tmp_path)
    with pytest.raises(Exception, match="테스트 계약"):
        RecordVerificationUseCase(repo)(
            spec_id,
            [
                VerificationEvidence(
                    test_id="TEST-001", status=VerificationStatus.FAIL, evidence="실패 로그"
                )
            ],
        )
