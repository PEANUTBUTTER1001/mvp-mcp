"""요청에서 확정된 1차 답을 미리 채우고 묻지 않는 흐름(from_request) 회귀 테스트."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveWizardQuestion,
    AdaptiveWizardSelectionAnswer,
    WizardQuestionKind,
    make_submission,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    intake_questions,
    prefilled_summary,
    suggestion_warnings,
)
from mvp_mcp.domain.spec.intake_view import build_intake_view
from mvp_mcp.main import build

NOW = datetime(2026, 11, 16, tzinfo=UTC)
WEATHER = {
    "work_type": "new_project",
    "solution_family": ["product_application"],
    "primary_surface": ["android_app"],
    "app_domain_hint": "날씨",
}
REST = {
    "pain_points": ["scattered"],
    "success_signals": ["time"],
    "initial_audience": "solo",
    "tech_stack": "ai_recommended",
}


def _by_id(suggested: dict[str, object]) -> dict[str, AdaptiveWizardQuestion]:
    return {question.id: question for question in intake_questions(suggested)}


def test_request_facts_are_prefilled_including_free_text() -> None:
    questions = _by_id(WEATHER)
    domain = questions["app_domain_hint"]

    assert {key for key, question in questions.items() if question.from_request} == set(WEATHER)
    assert domain.default is None and domain.default_other_text == "날씨"
    assert questions["primary_surface"].default == ["android_app"]
    dict_form = _by_id({"app_domain_hint": {"selected": ["fitness"], "other_text": "날씨"}})
    assert dict_form["app_domain_hint"].default == ["fitness"]
    assert dict_form["app_domain_hint"].default_other_text == "날씨"
    assert prefilled_summary(list(questions.values())) == [
        "어떤 작업인가요? → 새로 만들기",
        "무엇을 만들고 싶나요? → 사람들이 직접 쓰는 앱·웹사이트",
        "어디에서 쓰게 되나요? → 휴대폰 앱 · Android",
        "어떤 분야인가요? → 기타 — 날씨",
    ]


def test_skipped_request_facts_are_filled_by_server_and_marked_ai_default() -> None:
    questions = intake_questions(WEATHER)
    submission = make_submission("sub-prefill-0001", questions, dict(REST), NOW)

    assert submission.answers["work_type"] == "new_project"
    assert submission.answers["app_domain_hint"] == AdaptiveWizardSelectionAnswer(
        selected=[], other_text="날씨"
    )
    for question_id in WEATHER:
        assert submission.ai_inferred[question_id] == "default"
    # 자동 채운 work_type으로 새 프로젝트 후속 문항이 연쇄로 보인다.
    with_follow_up = make_submission(
        "sub-prefill-0002",
        questions,
        {**REST, "new_project_launch_context": "처음엔 혼자 사용"},
        NOW,
    )
    assert with_follow_up.answers["new_project_launch_context"] == "처음엔 혼자 사용"
    view = build_intake_view(submission.answers)
    assert view.surfaces == ("android_app",)
    assert "날씨" in view.domain_text


def test_user_correction_overrides_prefill_and_is_not_ai_inferred() -> None:
    questions = intake_questions(WEATHER)
    submission = make_submission(
        "sub-prefill-0003", questions, {**REST, "primary_surface": ["ios_app"]}, NOW
    )

    assert submission.answers["primary_surface"] == ["ios_app"]
    assert "primary_surface" not in submission.ai_inferred
    assert submission.ai_inferred["app_domain_hint"] == "default"


def test_invalid_prefill_is_ignored_with_warning() -> None:
    suggested = {
        "work_type": "날씨앱",  # 기타를 허용하지 않는 단일 선택
        "primary_surface": ["ai_suggest", "android_app"],  # 단독 선택값과 함께
        "pain_points": ["scattered"],  # 미리 채울 수 없는 문항
    }
    questions = _by_id(suggested)

    assert not any(question.from_request for question in questions.values())
    warnings = suggestion_warnings(suggested)
    assert len(warnings) == 3
    with pytest.raises(ValueError, match="미리 채운 값"):
        AdaptiveWizardQuestion(
            id="sample",
            label="sample",
            kind=WizardQuestionKind.SELECT,
            options=["a", "b"],
            from_request=True,
        )
    with pytest.raises(ValueError, match="기타 입력을 허용"):
        AdaptiveWizardQuestion(
            id="sample",
            label="sample",
            kind=WizardQuestionKind.SELECT,
            options=["a", "b"],
            default_other_text="날씨",
        )


def test_legacy_question_without_new_fields_still_loads() -> None:
    legacy = intake_questions()[0].model_dump(mode="json")
    legacy.pop("from_request")
    legacy.pop("default_other_text")
    restored = AdaptiveWizardQuestion.model_validate(legacy)
    assert restored.from_request is False and restored.default_other_text is None


def test_mcp_start_returns_summary_and_accepts_answers_without_prefilled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MVP_OUTPUT_DIR", str(tmp_path / "server-output"))
    monkeypatch.setenv("MVP_ADAPTIVE_WIZARD_DB_PATH", str(tmp_path / "adaptive-runs.sqlite3"))

    async def scenario() -> None:
        async with create_connected_server_and_client_session(build()) as client:
            started = await client.call_tool(
                "documentation_start_adaptive_wizard",
                {
                    "phase": "intake",
                    "user_request": "안드로이드 날씨앱 만들거야",
                    "project_root": str(tmp_path),
                    "request_key": "prefill-request-0001",
                    "suggested_answers": {
                        **WEATHER,
                        "app_domain_hint": {"selected": [], "other_text": "날씨"},
                    },
                },
            )
            payload = json.loads(started.content[0].text)  # type: ignore[union-attr]
            assert payload["prefilled_summary"][-1] == "어떤 분야인가요? → 기타 — 날씨"
            assert "from_request=true" in payload["next_instruction"]
            skipped = {q["id"] for q in payload["questions"] if q["from_request"]}
            assert skipped == set(WEATHER)

            submitted = await client.call_tool(
                "documentation_submit_adaptive_wizard_answers",
                {"run_id": payload["run_id"], "phase": "intake", "answers": REST},
            )
            result = json.loads(submitted.content[0].text)  # type: ignore[union-attr]
            assert result["status"] == "INTAKE_SUBMITTED"
            assert result["intake_answers"]["app_domain_hint"] == {
                "selected": [],
                "other_text": "날씨",
            }
            assert result["ai_inferred"]["intake"]["work_type"] == "default"

    # pytest-playwright가 같은 스레드에 이벤트 루프를 두므로 별도 스레드에서 실행한다.
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, scenario()).result()
