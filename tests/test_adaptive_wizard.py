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
    WizardQuestionKind,
    WritePolicy,
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
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation.tools.documentation_start_adaptive_wizard import (
    register_documentation_start_adaptive_wizard_tool,
)
from mvp_mcp.presentation.tools.documentation_submit_adaptive_wizard_answers import (
    register_documentation_submit_adaptive_wizard_answers_tool,
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
        "write_policy": "generate_only",
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

    submitted_intake = submit(intake.id, "intake", _intake_answers())
    assert submitted_intake.status is AdaptiveRunStatus.INTAKE_SUBMITTED
    assert submitted_intake.write_policy is WritePolicy.GENERATE_ONLY

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
    answers = _intake_answers()
    answers.pop("write_policy")
    submitted = submit(intake.id, "intake", answers)
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


def test_intake_separates_solution_surface_and_domain_classification() -> None:
    questions = {question.id: question for question in intake_questions()}
    assert "project_type" not in questions
    assert questions["solution_family"].options[0] == "product_application"
    assert questions["primary_surface"].visible_when == {"solution_family": ["product_application"]}
