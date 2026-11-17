"""질문 4×4 재구성(client native 질문 UI 한도)과 MCP 앱 제거 회귀 테스트.

- 선택형 문항 선택지 2~4개(design_must_features만 1~20 예외)
- 기타로 옮긴 값은 기타 입력 키워드로 기존 분류 코드를 복원
- 구조·문서 정리는 후속 문항으로 세부 작업 유형을 정한다(연쇄 가시성)
- MCP 앱 화면·임시 저장 Tool·`_meta.ui` 없음, 구 Run의 `answer_drafts`는 무시
- 클라이언트가 문자열·직접 입력으로 보낸 답을 받아들이고, 형식 오류는 내부 오류 대신 안내로 돌려준다
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.data.spec.sqlite_adaptive_wizard_run_repository import (
    SqliteAdaptiveWizardRunRepository,
)
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveWizardQuestion,
    AdaptiveWizardRun,
    AdaptiveWizardSelectionAnswer,
    WizardQuestionKind,
    make_submission,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    MAX_CHOICE_OPTIONS,
    MIN_CHOICE_OPTIONS,
    color_candidate_options,
    intake_questions,
    product_design_question_guidance,
    validate_design_questions,
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    StartAdaptiveWizardUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
)
from mvp_mcp.domain.spec.design_direction import build_product_design_contract
from mvp_mcp.domain.spec.intake_view import build_intake_view
from mvp_mcp.domain.spec.model import DesignPlatform
from mvp_mcp.domain.spec.palette import recommend_seed_colors
from mvp_mcp.main import build

CHOICE_KINDS = {WizardQuestionKind.SELECT, WizardQuestionKind.MULTISELECT}
NOW = datetime(2026, 11, 16, tzinfo=UTC)
PRODUCT = {
    "work_type": "new_project",
    "solution_family": ["product_application"],
    "primary_surface": ["web_app"],
    "app_domain_hint": ["booking"],
}


class _Clock:
    def now(self) -> datetime:
        return NOW


def _other(selected: list[str], text: str) -> AdaptiveWizardSelectionAnswer:
    return AdaptiveWizardSelectionAnswer(selected=selected, other_text=text)


def _choice(question_id: str, count: int) -> AdaptiveWizardQuestion:
    options = [f"option_{index}" for index in range(count)]
    return AdaptiveWizardQuestion(
        id=question_id,
        label=question_id,
        kind=WizardQuestionKind.MULTISELECT,
        options=options,
        option_labels={option: option for option in options},
    )


def test_every_intake_choice_fits_native_question_ui() -> None:
    for question in intake_questions():
        if question.kind in CHOICE_KINDS:
            assert MIN_CHOICE_OPTIONS <= len(question.options) <= MAX_CHOICE_OPTIONS, question.id
            assert set(question.option_labels) == set(question.options), question.id


def test_server_design_guidance_fits_and_validation_rejects_oversized_choices() -> None:
    inferred = {"primary_surface": "unknown", "success_signals": "unknown"}
    guidance = product_design_question_guidance(PRODUCT, inferred)
    assert validate_design_questions(guidance) == guidance
    for question in guidance:
        if question.kind in CHOICE_KINDS and question.id != "design_must_features":
            assert MIN_CHOICE_OPTIONS <= len(question.options) <= MAX_CHOICE_OPTIONS, question.id

    base = [_choice("custom_a", 2), _choice("custom_b", 3)]
    with pytest.raises(ValueError, match="2~4개"):
        validate_design_questions([*base, _choice("custom_c", 5)])
    with pytest.raises(ValueError, match="2~4개"):
        validate_design_questions([*base, _choice("custom_c", 1)])
    many = _choice("design_must_features", 20).model_copy(update={"allow_other": True})
    assert validate_design_questions([*base, many])[-1].id == "design_must_features"
    with pytest.raises(ValueError):
        validate_design_questions([*base, _choice("design_must_features", 21)])


def test_other_text_keywords_restore_moved_codes() -> None:
    intake = {
        **PRODUCT,
        "solution_family": _other(["product_application"], "개발자 도구"),
        "primary_surface": _other([], "PC 프로그램, 카톡 챗봇"),
        "app_domain_hint": _other([], "PT·헬스"),
        "pain_points": ["slow"],
        "success_signals": ["time"],
        "initial_audience": "customers",
        "tech_stack": "ai_recommended",
    }
    submission = make_submission("sub-keyword-01", intake_questions(), intake, NOW)
    view = build_intake_view(submission.answers)
    assert view.families == ("product_application", "developer_tool")
    assert view.surfaces == ("desktop_app", "chat_bot")
    assert view.domains == ("fitness",)
    fitness = [item.hex for item in recommend_seed_colors(["fitness"])]
    assert list(color_candidate_options(submission.answers)) == fitness

    contract = build_product_design_contract(
        submission.answers,
        {"design_frequent_user_tasks": "예약", "design_visual_tone": ["calm"]},
    )
    assert contract is not None
    assert DesignPlatform.DESKTOP in contract.visual_direction.platform_targets


def test_ascii_keywords_need_word_boundaries_and_unknown_text_stays_text() -> None:
    view = build_intake_view(
        {
            **PRODUCT,
            "primary_surface": _other(["android_app"], "ChatGPT 연동"),
            "app_domain_hint": _other([], "날씨"),
        }
    )
    assert view.surfaces == ("android_app",)
    assert view.domains == ()
    assert "날씨" in view.domain_text


def test_maintenance_follow_up_decides_work_type_with_chained_visibility() -> None:
    questions = intake_questions()
    base = {
        "solution_family": ["automation_integration"],
        "pain_points": ["slow"],
        "success_signals": ["time"],
        "initial_audience": "known",
        "tech_stack": "existing_project",
    }
    with pytest.raises(ValueError, match="필수 항목"):
        make_submission("sub-maint-0001", questions, {**base, "work_type": "maintenance"}, NOW)
    refactor = make_submission(
        "sub-maint-0002",
        questions,
        {
            **base,
            "work_type": "maintenance",
            "maintenance_kind": "refactoring",
            "refactor_current_pain": "모듈 경계가 섞여 있어요",
        },
        NOW,
    )
    view = build_intake_view(refactor.answers)
    assert view.work_type == "refactoring"
    assert view.tech_stack == "지금 프로젝트의 기술 그대로 사용" and not view.uses_ai_stack

    # 선행 문항이 보이지 않으면 남아 있는 후속 답이 있어도 그 후속 필수 문항을 요구하지 않는다.
    stray = make_submission(
        "sub-maint-0003",
        questions,
        {**base, "work_type": "new_project", "maintenance_kind": "refactoring"},
        NOW,
    )
    assert "maintenance_kind" not in stray.answers
    assert build_intake_view(stray.answers).work_type == "new_project"


def test_legacy_values_still_build_a_design_contract() -> None:
    legacy_intake = {
        "work_type": "new_project",
        "solution_family": ["product_application", "developer_tool"],
        "primary_surface": ["desktop_app", "onsite_device"],
        "app_domain_hint": ["education", "finance"],
    }
    contract = build_product_design_contract(
        legacy_intake,
        {"design_frequent_user_tasks": "기록", "design_visual_tone": ["friendly"]},
    )
    assert contract is not None
    assert "친근함" in contract.visual_direction.visual_tone
    assert DesignPlatform.DESKTOP in contract.visual_direction.platform_targets


def test_mcp_app_surface_is_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MVP_OUTPUT_DIR", str(tmp_path / "server-output"))
    monkeypatch.setenv("MVP_ADAPTIVE_WIZARD_DB_PATH", str(tmp_path / "adaptive-runs.sqlite3"))

    async def scenario() -> None:
        async with create_connected_server_and_client_session(build()) as client:
            tools = (await client.list_tools()).tools
            resources = (await client.list_resources()).resources
            assert len(tools) == 17
            assert "documentation_save_wizard_draft" not in {tool.name for tool in tools}
            assert all(not (tool.meta or {}).get("ui") for tool in tools)
            assert not [item for item in resources if str(item.uri).startswith("ui://")]

    # pytest-playwright가 같은 스레드에 이벤트 루프를 두므로 별도 스레드에서 실행한다.
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, scenario()).result()


def test_legacy_run_with_answer_drafts_still_loads(tmp_path: Path) -> None:
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    run = StartAdaptiveWizardUseCase(runs, _Clock())("날씨 앱", "C:/work/weather", "legacy-0001")
    legacy = {**run.model_dump(mode="json"), "answer_drafts": {"intake": {"work_type": "bug_fix"}}}
    restored = AdaptiveWizardRun.model_validate(legacy)
    assert restored.id == run.id
    assert "answer_drafts" not in restored.model_dump()


# 실제 Claude Chat 클라이언트가 보낸 1차 답변(2026-11-16 날씨앱 테스트). 이전에는 내부 오류였다.
CHAT_CLIENT_ANSWERS: dict[str, object] = {
    "work_type": "new_project",
    "solution_family": "product_application",
    "primary_surface": "android_app",
    "app_domain_hint": "날씨",
    "pain_points": "scattered, 과거 날씨 조회가 안 됨",
    "pain_detail": "기존 날씨앱은 과거 날씨 조회가 안 되고, 날씨 정보가 여러 곳에 흩어져 있음",
    "desired_change": "",
    "success_signals": "내 맞춤 날씨앱, 오늘 날씨가 최근 어느 날과 비슷한지 알려주기",
    "initial_audience": "solo",
    "new_project_known_dependencies": "Kotlin 네이티브 Android만 확정",
    "constraints_risks": "schedule, 상용화를 염두에 두고 유연성·확장성·유지보수성 고려 필요",
    "tech_stack": "Kotlin native Android",
}


def test_string_and_free_text_answers_are_accepted_as_choices_or_other() -> None:
    answers = make_submission("sub-chat-0001", intake_questions(), CHAT_CLIENT_ANSWERS, NOW).answers
    assert answers["solution_family"] == ["product_application"]
    assert answers["primary_surface"] == ["android_app"]
    assert answers["app_domain_hint"] == _other([], "날씨")
    assert answers["pain_points"] == _other(["scattered"], "과거 날씨 조회가 안 됨")
    assert answers["constraints_risks"] == _other(
        ["schedule"], "상용화를 염두에 두고 유연성·확장성·유지보수성 고려 필요"
    )
    assert answers["tech_stack"] == _other([], "Kotlin native Android")
    view = build_intake_view(answers)
    assert view.tech_stack == "Kotlin native Android" and not view.uses_ai_stack
    assert view.mobile_only


def test_invalid_answers_return_actionable_error_and_keep_run_open(tmp_path: Path) -> None:
    runs = SqliteAdaptiveWizardRunRepository(tmp_path / "adaptive-runs.sqlite3")
    run = StartAdaptiveWizardUseCase(runs, _Clock())("날씨 앱", "C:/work/weather", "format-0001")
    submit = SubmitAdaptiveWizardAnswersUseCase(runs, _Clock())
    # work_type은 기타 입력을 허용하지 않으므로 선택지 밖 값은 저장하지 않고 고칠 방법을 안내한다.
    with pytest.raises(PipelineError, match="답변 형식") as caught:
        submit(run.id, "intake", {**CHAT_CLIENT_ANSWERS, "work_type": "weather"})
    assert '"other_text"' in caught.value.hint
    reloaded = runs.find_by_id(run.id)
    assert reloaded is not None and reloaded.intake_submission is None
    saved = submit(run.id, "intake", CHAT_CLIENT_ANSWERS)
    assert saved.intake_submission is not None
