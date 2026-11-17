"""모델이 제안하는 메인 색 후보(design_color_choice) 검증·대비 안내·토큰 반영 회귀 테스트."""

from __future__ import annotations

import pytest

from mvp_mcp.domain.spec import palette
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveWizardQuestion,
    AdaptiveWizardSelectionAnswer,
    WizardQuestionKind,
)
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    color_candidate_options,
    product_design_question_guidance,
    validate_design_questions,
)
from mvp_mcp.domain.spec.design_direction import build_product_design_contract
from mvp_mcp.domain.spec.palette import seed_adjustment

INTAKE = {
    "work_type": "new_project",
    "solution_family": ["product_application"],
    "primary_surface": ["android_app"],
    "app_domain_hint": {"selected": [], "other_text": "날씨"},
    "desired_change": "지금·지난 날씨를 한 앱에서 본다.",
}
MODEL_COLORS = {
    "#4A90D9": "하늘색 · #4A90D9 — 맑은 하늘처럼 가볍고 시원한 인상",
    "#1E3A5F": "밤하늘 남색 · #1E3A5F — 정보가 많은 화면에서 차분함",
    "#F2A93B": "햇살 주황 · #F2A93B — 오늘 날씨를 밝게 강조",
}


def _color_question(options: list[str], labels: dict[str, str]) -> AdaptiveWizardQuestion:
    return AdaptiveWizardQuestion(
        id="design_color_choice",
        label="메인 색",
        kind=WizardQuestionKind.SELECT,
        options=options,
        option_labels=labels,
        allow_other=True,
    )


def _questions(options: list[str], labels: dict[str, str]) -> list[AdaptiveWizardQuestion]:
    # 서버는 색 질문을 요구하지 않지만, 클라이언트가 넣으면 기존 검증 규칙이 적용된다.
    return [*product_design_question_guidance(INTAKE), _color_question(options, labels)]


def _color(questions: list[AdaptiveWizardQuestion]) -> AdaptiveWizardQuestion:
    return next(question for question in questions if question.id == "design_color_choice")


def test_model_proposed_colors_are_accepted_with_contrast_note() -> None:
    validated = _color(validate_design_questions(_questions(list(MODEL_COLORS), MODEL_COLORS)))

    assert validated.options == list(MODEL_COLORS)
    for option in MODEL_COLORS:
        ui_primary, adjusted = seed_adjustment(option)
        label = validated.option_labels[option]
        assert label.startswith(MODEL_COLORS[option])
        assert ("글자 대비를 위해" in label) is adjusted
        if adjusted:
            assert ui_primary in label


@pytest.mark.parametrize(
    ("options", "labels", "message"),
    [
        (["blue", "#1E3A5F"], {"blue": "파랑", "#1E3A5F": "남색"}, "#RRGGBB"),
        (["#4A90D9", "#4a90d9"], {"#4A90D9": "하늘", "#4a90d9": "하늘2"}, "중복"),
        (["#4A90D9", "#1E3A5F"], {"#4A90D9": "하늘"}, "표시명"),
    ],
)
def test_invalid_model_colors_are_rejected(
    options: list[str], labels: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_design_questions(_questions(options, labels))


def test_server_candidates_still_pass_without_duplicate_note() -> None:
    server = color_candidate_options(INTAKE)
    guidance = _questions(list(server), server)
    original = _color(guidance)
    validated = _color(validate_design_questions(guidance))

    assert validated.option_labels == original.option_labels
    assert all(label.count("글자 대비를 위해") <= 1 for label in validated.option_labels.values())


def test_contrast_note_is_attached_once_and_fits_label_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 흰·검은 글자 중 하나는 항상 4.5:1을 넘으므로 보정이 필요한 색을 강제로 흉내 낸다.
    monkeypatch.setattr(palette, "seed_adjustment", lambda value: ("#8A5A00", True))
    long_label = "하늘 · #F2A93B — " + "가" * 200
    noted = palette.with_contrast_note(long_label, "#F2A93B")

    assert len(noted) <= 160 and noted.endswith("로 보정)")
    assert palette.with_contrast_note(noted, "#F2A93B") == noted
    assert "#8A5A00" in noted


def test_chosen_model_color_becomes_ai_recommended_seed() -> None:
    contract = build_product_design_contract(
        INTAKE,
        {
            "design_frequent_user_tasks": "지금 날씨 확인",
            "design_visual_tone": ["calm"],
            "design_color_choice": AdaptiveWizardSelectionAnswer(selected=["#4A90D9"]),
        },
    )

    assert contract is not None and contract.visual_direction is not None
    assert contract.visual_direction.seed_color == "#4A90D9"
    assert contract.visual_direction.color_origin == "ai_recommended"


def test_color_question_kind_rules_still_apply() -> None:
    multi = _color_question(list(MODEL_COLORS), MODEL_COLORS).model_copy(
        update={"kind": WizardQuestionKind.MULTISELECT}
    )
    with pytest.raises(ValueError, match="단일 선택"):
        validate_design_questions([*product_design_question_guidance(INTAKE), multi])
