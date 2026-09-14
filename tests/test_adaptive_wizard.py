"""Client-native 질문 UI 기반 2단계 Adaptive Wizard 회귀 테스트."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.candidate_package_repository import CandidatePackageRepository
from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardQuestion,
    AdaptiveWizardSelectionAnswer,
    WizardQuestionKind,
    WritePolicy,
    make_submission,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import intake_questions, validate_design_questions
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    CreateAdaptiveWizardDraftUseCase,
    GetAdaptiveWizardRunUseCase,
    OpenAdaptiveDesignWizardUseCase,
    StartAdaptiveWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
)
from mvp_mcp.domain.spec.model import ProjectType
from mvp_mcp.domain.spec.query import (
    GetDraftUseCase,
    GetTemplateUseCase,
    ListProjectTypesUseCase,
)
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation.resources.spec import register_resources
from mvp_mcp.presentation.tools._adaptive_wizard_snapshot import adaptive_wizard_snapshot
from mvp_mcp.presentation.tools.documentation_start_adaptive_wizard import (
    register_documentation_start_adaptive_wizard_tool,
)
from mvp_mcp.presentation.tools.documentation_submit_adaptive_wizard_answers import (
    register_documentation_submit_adaptive_wizard_answers_tool,
)
from mvp_mcp.presentation.tools.documentation_wizard_run_status import (
    register_documentation_wizard_run_status_tool,
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 13, tzinfo=UTC)


def _intake_answers() -> dict[str, object]:
    return {
        "work_type": "feature_addition",
        "solution_family": "developer_tool",
        "target_context": "mvp-mcp 문서화 MCP 서버",
        "problem": "로컬 브라우저 설문이 Tool timeout과 결합된다.",
        "goal": "클라이언트 native 질문 UI로 답변을 수집한다.",
        "affected_users": "Codex·Claude Code·Gemini CLI 사용자",
        "mvp_scope": "질문 schema 반환, 답변 저장, 후보 preview",
        "success_criteria": "브라우저 창 없이 두 단계 질문을 완료한다.",
        "constraints_risks": "기존 .mvpmcp 파일은 덮어쓰지 않는다.",
        "tech_stack": "AI 권장안 사용",
        "feature_affected_contracts": "질문 Tool, Skill, MCP Run 계약",
        "feature_compatibility": "동일 request_key와 제출 hash는 멱등이어야 한다.",
        "feature_migration": "기존 Web Wizard는 제거한다.",
    }


def _design_questions() -> list[AdaptiveWizardQuestion]:
    return [
        AdaptiveWizardQuestion(
            id="repository_evidence",
            label="저장소 근거",
            kind=WizardQuestionKind.TEXTAREA,
        ),
        AdaptiveWizardQuestion(
            id="client_boundary",
            label="클라이언트 경계",
            kind=WizardQuestionKind.TEXTAREA,
        ),
        AdaptiveWizardQuestion(
            id="recovery_expectation",
            label="재개 기대",
            kind=WizardQuestionKind.TEXTAREA,
        ),
    ]


def _design_answers() -> dict[str, object]:
    return {
        "repository_evidence": "현재 Web Form은 localhost HTTP와 동기 대기를 사용한다.",
        "client_boundary": "질문 UI는 각 클라이언트 Skill이 소유한다.",
        "recovery_expectation": "같은 Run의 중복 제출은 같은 결과를 반환한다.",
    }


def _wire(
    tmp_path: Path,
) -> tuple[
    StartAdaptiveWizardUseCase,
    OpenAdaptiveDesignWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
    CreateAdaptiveWizardDraftUseCase,
    GetAdaptiveWizardRunUseCase,
    InMemorySpecRepository,
]:
    clock = _FixedClock()
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    scope = ScopeMvpUseCase(specs, templates)
    candidates = CandidatePackageRepository(str(tmp_path / "server-output"))
    return (
        StartAdaptiveWizardUseCase(runs, clock),
        OpenAdaptiveDesignWizardUseCase(runs, clock),
        SubmitAdaptiveWizardAnswersUseCase(runs, clock),
        CreateAdaptiveWizardDraftUseCase(runs, specs, templates, scope, candidates, clock),
        GetAdaptiveWizardRunUseCase(runs),
        specs,
    )


def test_native_question_answers_create_one_scoped_draft(tmp_path: Path) -> None:
    start, design, submit, create_draft, get_run, specs = _wire(tmp_path)

    intake = start("mvp-mcp 질문 흐름을 개선해줘", "C:/workspace/mvp-mcp", "request-0001")
    assert intake.status is AdaptiveRunStatus.INTAKE_OPEN
    assert intake.intake_submission is None
    assert {"work_type", "solution_family", "tech_stack"} <= {
        question.id for question in intake.intake_questions
    }
    assert "write_policy" not in {question.id for question in intake.intake_questions}
    assert intake.requested_write_policy is WritePolicy.SAFE_AUTO_APPLY

    submitted_intake = submit(intake.id, "intake", _intake_answers())
    assert submitted_intake.status is AdaptiveRunStatus.INTAKE_SUBMITTED
    assert submitted_intake.write_policy is WritePolicy.SAFE_AUTO_APPLY

    opened_design = design(intake.id, _design_questions())
    assert opened_design.status is AdaptiveRunStatus.DESIGN_OPEN
    submitted_design = submit(intake.id, "design", _design_answers())
    ready = create_draft(submitted_design.id)

    assert ready.status is AdaptiveRunStatus.DRAFT_READY
    assert ready.spec_id == f"adaptive-{intake.id}"
    assert ready.candidate_root is not None
    assert Path(ready.candidate_root).is_dir()
    assert ready.version == 4
    assert get_run(ready.id) == ready

    draft = specs.find_by_id(ready.spec_id)
    assert draft is not None
    assert draft.status == "scoped"
    assert draft.project_type is ProjectType.MCP_SERVER
    assert draft.intake["design_client_boundary"].startswith("질문 UI")


def test_adaptive_draft_remains_available_from_draft_resource(tmp_path: Path) -> None:
    start, design, submit, create_draft, _get_run, specs = _wire(tmp_path)
    intake = start("문서 Wizard", "C:/workspace/mvp-mcp", "request-resource-0001")
    submit(intake.id, "intake", _intake_answers())
    design(intake.id, _design_questions())
    ready = create_draft(submit(intake.id, "design", _design_answers()).id)
    assert ready.spec_id is not None

    templates = InMemoryTemplateRepository()
    server = FastMCP("adaptive_draft_resource_test")
    register_resources(
        server,
        ListProjectTypesUseCase(templates),
        GetTemplateUseCase(templates),
        GetDraftUseCase(specs),
    )

    async def scenario() -> None:
        async with create_connected_server_and_client_session(server) as client:
            templates_result = await client.list_resource_templates()
            assert "spec://drafts/{spec_id}" in {
                item.uriTemplate for item in templates_result.resourceTemplates
            }
            resource = await client.read_resource(f"spec://drafts/{ready.spec_id}")
            assert json.loads(resource.contents[0].text or "{}")["id"] == ready.spec_id

    asyncio.run(scenario())


def test_same_request_and_same_native_answers_are_idempotent(tmp_path: Path) -> None:
    start, design, submit, create_draft, _get_run, _specs = _wire(tmp_path)
    intake = start("문서 Wizard", "C:/workspace/mvp-mcp", "request-0002")
    assert start("문서 Wizard", "C:/workspace/mvp-mcp", "request-0002") == intake

    submitted_intake = submit(intake.id, "intake", _intake_answers())
    assert submit(intake.id, "intake", _intake_answers()) == submitted_intake
    opened_design = design(intake.id, _design_questions())
    assert design(intake.id, _design_questions()) == opened_design
    submitted_design = submit(intake.id, "design", _design_answers())
    ready = create_draft(submitted_design.id)
    assert submit(intake.id, "design", _design_answers()) == ready
    assert create_draft(ready.id) == ready


def test_requested_write_policy_is_bound_before_native_intake(tmp_path: Path) -> None:
    start, _design, submit, _create_draft, _get_run, _specs = _wire(tmp_path)
    intake = start(
        "후보 문서만 생성해줘",
        "C:/workspace/mvp-mcp",
        "request-policy-0001",
        WritePolicy.GENERATE_ONLY,
    )

    assert intake.requested_write_policy is WritePolicy.GENERATE_ONLY
    assert "write_policy" not in {question.id for question in intake.intake_questions}
    submitted = submit(intake.id, "intake", _intake_answers())
    assert submitted.write_policy is WritePolicy.GENERATE_ONLY
    with pytest.raises(PipelineError, match="최초 파일 반영 정책"):
        start(
            "후보 문서만 생성해줘",
            "C:/workspace/mvp-mcp",
            "request-policy-0001",
            WritePolicy.SAFE_AUTO_APPLY,
        )


def test_design_questions_reject_changed_retry_and_invalid_budget(tmp_path: Path) -> None:
    start, design, submit, _create_draft, _get_run, _specs = _wire(tmp_path)
    intake = start("문서 Wizard", "C:/workspace/mvp-mcp", "request-0003")
    submit(intake.id, "intake", _intake_answers())
    design(intake.id, _design_questions())

    changed = _design_questions()
    changed[0] = changed[0].model_copy(update={"label": "바뀐 질문"})
    with pytest.raises(PipelineError, match="질문은 변경할 수 없습니다"):
        design(intake.id, changed)
    with pytest.raises(ValueError, match="3~7개"):
        validate_design_questions(_design_questions()[:2])


def test_sqlite_run_survives_repository_recreation(tmp_path: Path) -> None:
    start, design, submit, create_draft, _get_run, _specs = _wire(tmp_path)
    intake = start("문서 Wizard", "C:/workspace/mvp-mcp", "request-0004")
    submit(intake.id, "intake", _intake_answers())
    design(intake.id, _design_questions())
    ready = create_draft(submit(intake.id, "design", _design_answers()).id)

    restored_runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    assert restored_runs.find_by_id(ready.id) == ready


def test_mcp_tools_return_schemas_then_accept_native_answers(tmp_path: Path) -> None:
    async def scenario() -> None:
        start, design, submit, create_draft, _get_run, _specs = _wire(tmp_path)
        server = FastMCP("adaptive_wizard_test")
        register_documentation_start_adaptive_wizard_tool(server, start, design)
        register_documentation_submit_adaptive_wizard_answers_tool(server, submit, create_draft)

        async with create_connected_server_and_client_session(server) as client:
            opened_response = await client.call_tool(
                "documentation_start_adaptive_wizard",
                {
                    "phase": "intake",
                    "user_request": "mvp-mcp Wizard를 개선해줘",
                    "project_root": "C:/workspace/mvp-mcp",
                    "request_key": "mcp-request-0005",
                },
            )
            opened = json.loads(opened_response.content[0].text or "{}")
            assert opened_response.isError is False
            assert opened["status"] == "INTAKE_OPEN"
            assert opened["next_action"] == "ask_client_native_questions"
            assert opened["questions"]
            assert "브라우저" in opened["next_instruction"]

            intake_response = await client.call_tool(
                "documentation_submit_adaptive_wizard_answers",
                {"run_id": opened["run_id"], "phase": "intake", "answers": _intake_answers()},
            )
            intake = json.loads(intake_response.content[0].text or "{}")
            assert intake_response.isError is False
            assert intake["status"] == "INTAKE_SUBMITTED"
            assert intake["user_message_required"] is False

            design_response = await client.call_tool(
                "documentation_start_adaptive_wizard",
                {
                    "phase": "design",
                    "run_id": opened["run_id"],
                    "design_questions": [
                        question.model_dump(mode="json") for question in _design_questions()
                    ],
                },
            )
            opened_design = json.loads(design_response.content[0].text or "{}")
            assert opened_design["status"] == "DESIGN_OPEN"
            assert opened_design["questions"]

            ready_response = await client.call_tool(
                "documentation_submit_adaptive_wizard_answers",
                {
                    "run_id": opened["run_id"],
                    "phase": "design",
                    "answers": _design_answers(),
                },
            )
            ready = json.loads(ready_response.content[0].text or "{}")
            assert ready["status"] == "DRAFT_READY"
            assert ready["candidate_root"]

    asyncio.run(scenario())


def test_mcp_run_status_recovers_open_intake_questions_by_run_id(tmp_path: Path) -> None:
    async def scenario() -> None:
        start, design, _submit, _create_draft, get_run, _specs = _wire(tmp_path)
        server = FastMCP("adaptive_wizard_status_test")
        register_documentation_start_adaptive_wizard_tool(server, start, design)
        register_documentation_wizard_run_status_tool(server, get_run)

        async with create_connected_server_and_client_session(server) as client:
            opened_response = await client.call_tool(
                "documentation_start_adaptive_wizard",
                {
                    "phase": "intake",
                    "user_request": "중단된 native 질문을 재개해줘",
                    "project_root": "C:/workspace/mvp-mcp",
                    "request_key": "mcp-status-request-0006",
                    "write_policy": "generate_only",
                },
            )
            opened = json.loads(opened_response.content[0].text or "{}")

            status_response = await client.call_tool(
                "documentation_wizard_run_status", {"run_id": opened["run_id"]}
            )
            resumed = json.loads(status_response.content[0].text or "{}")

            assert status_response.isError is False
            assert resumed["status"] == "INTAKE_OPEN"
            assert resumed["intake_questions"] == opened["questions"]
            assert "intake_questions" in resumed["resume_hint"]
            assert resumed["candidate_root"] is None

    asyncio.run(scenario())


def test_intake_separates_solution_surface_and_domain_classification() -> None:
    questions = {question.id: question for question in intake_questions()}
    assert "project_type" not in questions
    assert questions["solution_family"].options[0] == "product_application"
    assert questions["primary_surface"].visible_when == {"solution_family": ["product_application"]}


def test_selection_answers_preserve_multiple_values_and_other_text() -> None:
    question = AdaptiveWizardQuestion(
        id="launch_features",
        label="첫 출시 기능",
        kind=WizardQuestionKind.MULTISELECT,
        options=[f"feature_{index}" for index in range(20)],
        allow_other=True,
        max_selections=3,
    )

    submission = make_submission(
        "submission-0001",
        [question],
        {
            "launch_features": {
                "selected": ["feature_0", "feature_7"],
                "other_text": "음성 상태 업데이트",
            }
        },
        datetime(2026, 9, 14, tzinfo=UTC),
    )

    answer = submission.answers["launch_features"]
    assert answer == AdaptiveWizardSelectionAnswer(
        selected=["feature_0", "feature_7"],
        other_text="음성 상태 업데이트",
    )


def test_selection_answers_reject_unsupported_other_and_too_many_values() -> None:
    unsupported_other = AdaptiveWizardQuestion(
        id="write_policy",
        label="파일 반영 정책",
        kind=WizardQuestionKind.SELECT,
        options=["generate_only", "safe_auto_apply", "manual_apply"],
    )
    with pytest.raises(ValueError, match="기타 자유 입력을 허용하지 않습니다"):
        make_submission(
            "submission-0002",
            [unsupported_other],
            {"write_policy": {"selected": [], "other_text": "직접 반영"}},
            datetime(2026, 9, 14, tzinfo=UTC),
        )

    limited_multi = AdaptiveWizardQuestion(
        id="features",
        label="기능",
        kind=WizardQuestionKind.MULTISELECT,
        options=["photo", "comment", "notification"],
        allow_other=True,
        max_selections=2,
    )
    with pytest.raises(ValueError, match="최대 선택 수"):
        make_submission(
            "submission-0003",
            [limited_multi],
            {
                "features": {
                    "selected": ["photo", "comment"],
                    "other_text": "음성 게시물",
                }
            },
            datetime(2026, 9, 14, tzinfo=UTC),
        )


def test_structured_selection_answers_drive_conditional_questions() -> None:
    category = AdaptiveWizardQuestion(
        id="category",
        label="카테고리",
        kind=WizardQuestionKind.SELECT,
        options=["sns", "commerce"],
        allow_other=True,
    )
    conditional = AdaptiveWizardQuestion(
        id="sns_safety",
        label="SNS 안전 기능",
        kind=WizardQuestionKind.TEXT,
        visible_when={"category": ["sns"]},
    )

    submission = make_submission(
        "submission-0004",
        [category, conditional],
        {
            "category": {"selected": ["sns"], "other_text": None},
            "sns_safety": "차단과 신고",
        },
        datetime(2026, 9, 14, tzinfo=UTC),
    )

    assert submission.answers["sns_safety"] == "차단과 신고"


def test_legacy_selection_values_remain_valid() -> None:
    question = AdaptiveWizardQuestion(
        id="relationship",
        label="관계 모델",
        kind=WizardQuestionKind.MULTISELECT,
        options=["friend", "follow", "invite"],
        max_selections=3,
    )

    submission = make_submission(
        "submission-0005",
        [question],
        {"relationship": ["friend", "invite"]},
        datetime(2026, 9, 14, tzinfo=UTC),
    )

    assert submission.answers["relationship"] == ["friend", "invite"]


def test_structured_other_answer_survives_sqlite_and_candidate_creation(tmp_path: Path) -> None:
    start, design, submit, create_draft, _get_run, _specs = _wire(tmp_path)
    intake = start("문서 Wizard", "C:/workspace/mvp-mcp", "request-other-0001")
    submit(intake.id, "intake", _intake_answers())
    questions = _design_questions()
    questions[0] = AdaptiveWizardQuestion(
        id="launch_features",
        label="첫 출시 기능",
        kind=WizardQuestionKind.MULTISELECT,
        options=["photo", "comment", "notification"],
        allow_other=True,
        max_selections=2,
    )
    design(intake.id, questions)
    submitted = submit(
        intake.id,
        "design",
        {
            "launch_features": {
                "selected": ["photo"],
                "other_text": "음성 상태 업데이트",
            },
            "client_boundary": "질문 UI는 각 클라이언트가 소유한다.",
            "recovery_expectation": "같은 Run의 중복 제출은 같은 결과를 반환한다.",
        },
    )
    ready = create_draft(submitted.id)

    restored_runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    restored = restored_runs.find_by_id(ready.id)

    assert restored is not None
    assert restored.design_submission is not None
    assert restored.design_submission.answers["launch_features"] == (
        AdaptiveWizardSelectionAnswer(selected=["photo"], other_text="음성 상태 업데이트")
    )
    snapshot = adaptive_wizard_snapshot(restored)
    assert json.loads(json.dumps(snapshot, ensure_ascii=False))["design_answers"][
        "launch_features"
    ] == {"selected": ["photo"], "other_text": "음성 상태 업데이트"}
