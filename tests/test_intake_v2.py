"""쉬운 1차 설문·복수 선택·AI 추정·AI 추천 색상 계약 회귀 테스트 (서비스 흐름 v2 M1·M2)."""

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
    AI_SUGGEST_OPTION,
    AdaptiveWizardQuestion,
    WizardQuestionKind,
    make_submission,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    VISUAL_TONES,
    WEB_BEHAVIORS,
    color_candidate_options,
    intake_questions,
    product_design_question_guidance,
    required_product_design_question_ids,
    suggestion_warnings,
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    CreateAdaptiveWizardDraftUseCase,
    OpenAdaptiveDesignWizardUseCase,
    StartAdaptiveWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
)
from mvp_mcp.domain.spec.documentation_model import UiSurface
from mvp_mcp.domain.spec.intake_view import build_intake_view, scope_advice
from mvp_mcp.domain.spec.model import DesignPlatform, ProjectType
from mvp_mcp.domain.spec.palette import contrast_ratio, recommend_seed_colors
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation.tools.documentation_start_adaptive_wizard import (
    register_documentation_start_adaptive_wizard_tool,
)
from mvp_mcp.presentation.tools.documentation_submit_adaptive_wizard_answers import (
    register_documentation_submit_adaptive_wizard_answers_tool,
)

NOW = datetime(2026, 11, 16, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return NOW


def _wire(tmp_path: Path) -> tuple[
    StartAdaptiveWizardUseCase,
    OpenAdaptiveDesignWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
    CreateAdaptiveWizardDraftUseCase,
    InMemorySpecRepository,
]:
    clock = _Clock()
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "runs.sqlite3")
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    return (
        StartAdaptiveWizardUseCase(runs, clock),
        OpenAdaptiveDesignWizardUseCase(runs, clock),
        SubmitAdaptiveWizardAnswersUseCase(runs, clock),
        CreateAdaptiveWizardDraftUseCase(
            runs,
            specs,
            templates,
            ScopeMvpUseCase(specs, templates),
            CandidatePackageRepository(str(tmp_path / "out")),
            clock,
        ),
        specs,
    )


def _pt_intake(**overrides: object) -> dict[str, object]:
    answers: dict[str, object] = {
        "work_type": "new_project",
        "solution_family": ["product_application"],
        "primary_surface": ["web_app", "android_app"],
        "app_domain_hint": ["booking", "fitness"],
        "pain_points": ["contact", "mistake"],
        "pain_detail": "전화·카톡 예약이라 시간이 겹치고 노쇼가 잦아요.",
        "success_signals": [AI_SUGGEST_OPTION],
        "initial_audience": "customers",
        "constraints_risks": ["data"],
        "tech_stack": "ai_recommended",
    }
    answers.update(overrides)
    return answers


def _design_questions(intake: dict[str, object], inferred: dict[str, str]) -> list:
    questions = product_design_question_guidance(intake, inferred)
    replaced = []
    for question in questions:
        if question.id == "design_must_features":
            question = question.model_copy(
                update={
                    "options": [f"feature_{index}" for index in range(8)],
                    "option_labels": {f"feature_{index}": f"기능 {index}" for index in range(8)},
                }
            )
        if question.id in {"confirm_success_signals", "confirm_desired_change"}:
            question = question.model_copy(
                update={
                    "options": ["ai_proposal", "ai_alternative"],
                    "option_labels": {"ai_proposal": "AI 제안", "ai_alternative": "AI 다른 제안"},
                }
            )
        replaced.append(question)
    # 서버는 디자인 질문을 요구하지 않지만, 클라이언트가 직접 넣은 디자인 질문도 계속 처리된다.
    colors = color_candidate_options(intake)
    replaced += [
        AdaptiveWizardQuestion(
            id="design_visual_tone",
            label="느낌",
            kind=WizardQuestionKind.MULTISELECT,
            options=list(VISUAL_TONES),
            option_labels=VISUAL_TONES,
            max_selections=2,
            allow_other=True,
        ),
        AdaptiveWizardQuestion(
            id="design_color_choice",
            label="메인 색",
            kind=WizardQuestionKind.SELECT,
            options=list(colors),
            option_labels=colors,
            allow_other=True,
        ),
        AdaptiveWizardQuestion(
            id="design_web_behavior",
            label="웹 사용 환경",
            kind=WizardQuestionKind.SELECT,
            options=list(WEB_BEHAVIORS),
            option_labels=WEB_BEHAVIORS,
        ),
    ]
    return replaced


def _design_answers(questions: list, **overrides: object) -> dict[str, object]:
    by_id = {question.id: question for question in questions}
    answers: dict[str, object] = {
        "design_frequent_user_tasks": "회원이 빈 시간 예약, 트레이너가 출석 확인",
        "design_must_features": ["feature_0", "feature_1"],
        "design_visual_tone": ["trust", "lively"],
        "design_color_choice": by_id["design_color_choice"].options[0],
        "design_web_behavior": "mobile",
    }
    for question_id in by_id:
        if question_id.startswith("confirm_") and question_id != "confirm_primary_surface":
            answers[question_id] = "ai_proposal"
    if "confirm_primary_surface" in by_id:
        answers["confirm_primary_surface"] = ["web_app"]
    answers.update(overrides)
    return answers


def test_intake_schema_uses_plain_labels_exclusive_options_and_either_required() -> None:
    questions = {question.id: question for question in intake_questions()}

    assert questions["work_type"].label_for("bug_fix") == "오류 고치기"
    assert questions["solution_family"].kind is WizardQuestionKind.MULTISELECT
    assert questions["solution_family"].allow_other
    surface = questions["primary_surface"]
    assert surface.exclusive_options == [AI_SUGGEST_OPTION]
    assert "cross_platform_app" not in surface.options
    assert questions["app_domain_hint"].max_selections == 3
    assert questions["pain_points"].required_unless == ["pain_detail"]
    assert questions["desired_change"].ai_fill_when_empty
    assert "new_project_boundary" not in questions and "mvp_scope" not in questions
    assert questions["initial_audience"].kind is WizardQuestionKind.SELECT
    dumped = surface.model_dump(mode="json")
    assert dumped["option_labels"]["web_app"] == "웹 브라우저 (PC·휴대폰)"


def test_intake_validation_enforces_exclusive_max_and_either_required() -> None:
    questions = intake_questions()

    with pytest.raises(ValueError, match="함께 고를 수 없습니다"):
        make_submission(
            "sub-exclusive-01",
            questions,
            _pt_intake(primary_surface=["web_app", AI_SUGGEST_OPTION]),
            NOW,
        )
    with pytest.raises(ValueError, match="최대 선택 수"):
        make_submission(
            "sub-max-domain-01",
            questions,
            _pt_intake(app_domain_hint=["booking", "commerce", "fitness", "business"]),
            NOW,
        )
    with pytest.raises(ValueError, match="필수 항목"):
        make_submission(
            "sub-either-0001", questions, _pt_intake(pain_points=[], pain_detail=""), NOW
        )
    only_detail = make_submission("sub-either-0002", questions, _pt_intake(pain_points=[]), NOW)
    assert "pain_points" not in only_detail.answers


def test_ai_inferred_records_unknown_default_and_empty_then_requires_confirm(
    tmp_path: Path,
) -> None:
    start, design, submit, _create, _specs = _wire(tmp_path)
    run = start(
        "동네 헬스장 PT 예약 웹앱",
        "C:/workspace/pt",
        "request-intake-v2-0001",
        suggested_answers={"app_domain_hint": ["booking", "fitness"]},
    )
    domain = next(item for item in run.intake_questions if item.id == "app_domain_hint")
    assert domain.default == ["booking", "fitness"]

    submitted = submit(run.id, "intake", _pt_intake(primary_surface=[AI_SUGGEST_OPTION]))
    inferred = submitted.intake_submission.ai_inferred if submitted.intake_submission else {}
    assert inferred == {
        "primary_surface": "unknown",
        "app_domain_hint": "default",
        "desired_change": "empty",
        "success_signals": "unknown",
    }
    intake = dict(submitted.intake_submission.answers) if submitted.intake_submission else {}
    required = required_product_design_question_ids(intake, inferred)
    assert {
        "confirm_primary_surface",
        "confirm_success_signals",
        "confirm_desired_change",
        "design_must_features",
    } <= required
    assert not required & {"design_visual_tone", "design_color_choice", "design_web_behavior"}

    questions = _design_questions(intake, inferred)
    without_confirm = [item for item in questions if item.id != "confirm_desired_change"]
    with pytest.raises(PipelineError, match="confirm_desired_change"):
        design(run.id, without_confirm)
    opened = design(run.id, questions)
    assert len(opened.design_questions) == len(questions)


def test_suggested_answers_outside_options_are_ignored_with_warning() -> None:
    # 기타를 허용하지 않는 문항(work_type)의 선택지 밖 값과 미리 채울 수 없는 문항만 무시한다.
    warnings = suggestion_warnings({"work_type": "moon_base", "pain_detail": "x"})
    assert len(warnings) == 2
    questions = {item.id: item for item in intake_questions({"work_type": "moon_base"})}
    assert questions["work_type"].default is None
    assert not questions["work_type"].from_request
    # 기타를 허용하는 문항은 선택지 밖 값을 직접 입력으로 미리 채운다.
    assert not suggestion_warnings({"app_domain_hint": ["moon_base"]})
    domain = {item.id: item for item in intake_questions({"app_domain_hint": ["moon_base"]})}
    assert domain["app_domain_hint"].default_other_text == "moon_base"


def test_multiselect_answers_drive_platforms_surfaces_and_project_type(tmp_path: Path) -> None:
    start, design, submit, create, specs = _wire(tmp_path)
    run = start("PT 예약", "C:/workspace/pt", "request-intake-v2-0002")
    submitted = submit(run.id, "intake", _pt_intake(success_signals=["revenue"]))
    intake = dict(submitted.intake_submission.answers) if submitted.intake_submission else {}
    inferred = submitted.intake_submission.ai_inferred if submitted.intake_submission else {}
    questions = _design_questions(intake, inferred)
    design(run.id, questions)
    ready = create(submit(run.id, "design", _design_answers(questions)).id)

    draft = specs.find_by_id(ready.spec_id or "")
    assert draft is not None and draft.design_contract is not None
    direction = draft.design_contract.visual_direction
    assert direction is not None
    assert direction.platform_targets == [
        DesignPlatform.WEB,
        DesignPlatform.MOBILE,
        DesignPlatform.DESKTOP,
    ]
    assert draft.documentation.ui_surfaces == [UiSurface.WEB, UiSurface.MOBILE]
    assert draft.project_type is ProjectType.ETC
    assert direction.color_origin == "ai_recommended"
    assert (
        direction.seed_color
        == questions[[item.id for item in questions].index("design_color_choice")].options[0]
    )
    assert "믿음직함" in direction.visual_tone
    assert draft.features == ["기능 0", "기능 1"]


def test_mobile_only_product_resolves_mobile_template() -> None:
    view = build_intake_view(_pt_intake(primary_surface=["android_app", "ios_app"]))
    assert view.mobile_only
    legacy = build_intake_view(
        {"solution_family": "product_application", "primary_surface": "android_app"}
    )
    assert legacy.mobile_only and legacy.surfaces == ("android_app",)


def test_unlimited_must_features_and_scope_advice() -> None:
    must = AdaptiveWizardQuestion(
        id="design_must_features",
        label="첫 버전 기능",
        kind=WizardQuestionKind.MULTISELECT,
        options=[f"f{index}" for index in range(8)],
        allow_other=True,
    )
    submission = make_submission(
        "sub-must-0000001", [must], {"design_must_features": [f"f{i}" for i in range(8)]}, NOW
    )
    assert len(submission.answers["design_must_features"]) == 8
    advice = scope_advice(submission.answers)
    assert advice is not None and "8개" in advice
    assert scope_advice({"design_must_features": ["f0", "f1"]}) is None


def test_custom_color_must_be_hex_and_color_options_need_hex_and_labels(tmp_path: Path) -> None:
    start, design, submit, create, specs = _wire(tmp_path)
    run = start("PT 예약", "C:/workspace/pt", "request-intake-v2-0003")
    submitted = submit(run.id, "intake", _pt_intake(success_signals=["time"]))
    intake = dict(submitted.intake_submission.answers) if submitted.intake_submission else {}
    inferred = submitted.intake_submission.ai_inferred if submitted.intake_submission else {}
    questions = _design_questions(intake, inferred)

    def _colors(options: list[str], labels: dict[str, str]) -> list:
        return [
            (
                item.model_copy(
                    update={"options": options, "option_labels": labels, "default": None}
                )
                if item.id == "design_color_choice"
                else item
            )
            for item in questions
        ]

    # 모델이 제안한 색도 쓸 수 있지만 #RRGGBB 값과 사람용 표시명이 있어야 한다.
    with pytest.raises(PipelineError, match="#RRGGBB"):
        design(run.id, _colors(["blue", "#123456"], {"blue": "파랑", "#123456": "남색"}))
    with pytest.raises(PipelineError, match="표시명"):
        design(run.id, _colors(["#123456", "#654321"], {"#123456": "남색"}))
    design(run.id, questions)
    with pytest.raises(PipelineError, match="#RRGGBB"):
        submit(
            run.id,
            "design",
            _design_answers(
                questions, design_color_choice={"selected": [], "other_text": "파란색"}
            ),
        )
    ready = create(
        submit(
            run.id,
            "design",
            _design_answers(
                questions, design_color_choice={"selected": [], "other_text": "#2f6fb5"}
            ),
        ).id
    )
    draft = specs.find_by_id(ready.spec_id or "")
    assert draft is not None and draft.design_contract is not None
    direction = draft.design_contract.visual_direction
    assert direction is not None
    assert (direction.seed_color, direction.color_origin) == ("#2F6FB5", "user")


def test_recommended_colors_are_three_accessible_candidates_per_domain() -> None:
    for domains in (["fitness"], ["commerce"], ["booking"], []):
        candidates = recommend_seed_colors(domains)
        assert len(candidates) == 3
        for candidate in candidates:
            best = max(
                contrast_ratio(candidate.ui_primary, "#FFFFFF"),
                contrast_ratio(candidate.ui_primary, "#000000"),
            )
            assert best >= 4.5
            assert candidate.hex in candidate.option_label()
    assert list(color_candidate_options({"app_domain_hint": ["fitness"]}))[0] == "#1F7A6D"


def test_mcp_start_returns_defaults_warnings_and_design_guidance(tmp_path: Path) -> None:
    async def scenario() -> None:
        start, design, submit, create, _specs = _wire(tmp_path)
        server = FastMCP("intake_v2_test")
        register_documentation_start_adaptive_wizard_tool(server, start, design)
        register_documentation_submit_adaptive_wizard_answers_tool(server, submit, create)
        async with create_connected_server_and_client_session(server) as client:
            opened = json.loads(
                (
                    await client.call_tool(
                        "documentation_start_adaptive_wizard",
                        {
                            "phase": "intake",
                            "user_request": "PT 예약",
                            "project_root": "C:/workspace/pt",
                            "request_key": "mcp-intake-v2-0001",
                            "suggested_answers": {
                                "app_domain_hint": ["fitness"],
                                "work_type": "moon",
                            },
                        },
                    )
                )
                .content[0]
                .text
                or "{}"
            )
            domain = next(q for q in opened["questions"] if q["id"] == "app_domain_hint")
            assert domain["default"] == ["fitness"]
            assert opened["suggestion_warnings"]
            submitted = json.loads(
                (
                    await client.call_tool(
                        "documentation_submit_adaptive_wizard_answers",
                        {
                            "run_id": opened["run_id"],
                            "phase": "intake",
                            "answers": _pt_intake(app_domain_hint=["fitness"]),
                        },
                    )
                )
                .content[0]
                .text
                or "{}"
            )
            assert submitted["ai_inferred"]["intake"]["app_domain_hint"] == "default"
            guidance_ids = {item["id"] for item in submitted["design_question_guidance"]}
            assert set(submitted["required_design_question_ids"]) == guidance_ids
            assert "confirm_success_signals" in guidance_ids

    asyncio.run(scenario())
