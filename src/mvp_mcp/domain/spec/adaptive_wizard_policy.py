"""2단계 적응형 Wizard의 질문 예산과 1차 문항 정책.

1차 질문은 MVP·도구 용어에 익숙하지 않은 사람도 고르기 위주로 답할 수 있게 쓴다. 선택지 값은
분기·저장용 영문 코드이고, 사람에게는 ``option_labels``의 쉬운 표시명만 보인다.
"""

# ruff: noqa: E501

from __future__ import annotations

import re
from collections.abc import Mapping

from .adaptive_wizard_model import (
    AI_SUGGEST_OPTION,
    MAX_DESIGN_QUESTIONS,
    AdaptiveWizardQuestion,
    AdaptiveWizardSelectionAnswer,
    WizardQuestionKind,
    other_text,
    selected_values,
)
from .intake_view import (
    CONFIRM_ALTERNATIVE,
    CONFIRM_SUGGESTION,
    CONFIRMABLE_INTAKE_IDS,
    MAINTENANCE_WORK,
    PRODUCT_FAMILY,
    answer_values,
    build_intake_view,
)
from .palette import recommend_seed_colors, with_contrast_note

SELECT = WizardQuestionKind.SELECT
MULTISELECT = WizardQuestionKind.MULTISELECT
TEXT = WizardQuestionKind.TEXT
TEXTAREA = WizardQuestionKind.TEXTAREA
PRODUCT_ONLY = {"solution_family": [PRODUCT_FAMILY]}
DOMAIN_MAX = 3
HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
COLOR_CHOICE_ID = "design_color_choice"
_MISSING_DESIGN_MESSAGE = "2차 필수 질문이 없습니다: "

WORK_TYPES = {
    "new_project": "새로 만들기",
    "feature_addition": "이미 있는 것에 기능 더하기",
    "bug_fix": "오류 고치기",
    MAINTENANCE_WORK: "구조·문서 정리",
}
MAINTENANCE_KINDS = {
    "refactoring": "구조 정리 (개발자용)",
    "documentation_ops": "문서 정리",
}
SOLUTION_FAMILIES = {
    PRODUCT_FAMILY: "사람들이 직접 쓰는 앱·웹사이트",
    "automation_integration": "반복 업무 자동화·다른 서비스 연결 (API)",
    "data_pipeline": "데이터 모으기·정리·분석",
    "ml_system": "AI가 핵심인 기능 (추천·분류·생성)",
}
SURFACES = {
    "web_app": "웹 브라우저 (PC·휴대폰)",
    "android_app": "휴대폰 앱 · Android",
    "ios_app": "휴대폰 앱 · iPhone",
    AI_SUGGEST_OPTION: "아직 모르겠어요 (AI 추천)",
}
DOMAINS = {
    "booking": "예약·일정",
    "commerce": "쇼핑·결제",
    "fitness": "건강·운동",
    "business": "업무·기록",
}
PAIN_POINTS = {
    "slow": "시간이 오래 걸려요",
    "mistake": "실수·빠뜨림이 생겨요",
    "contact": "연락·확인이 번거로워요",
    "scattered": "정보가 흩어져 있어요",
}
SUCCESS_SIGNALS = {
    "time": "시간이 줄어든다",
    "fewer_mistakes": "실수가 줄어든다",
    "revenue": "매출·예약·사용자가 는다",
    AI_SUGGEST_OPTION: "잘 모르겠어요 — AI가 제안",
}
AUDIENCES = {
    "solo": "나 혼자",
    "known": "아는 사람 (팀·가족)",
    "customers": "특정 고객·회원",
    "public": "누구나 (공개)",
}
CONSTRAINTS = {
    "schedule": "정해진 마감이 있어요",
    "data": "개인정보·보안·법 규정이 걱정돼요",
    "compatibility": "기존 시스템과 맞춰야 해요",
    "operations": "운영할 사람이 적어요",
}
TECH_STACK = {
    "ai_recommended": "없어요 — AI 추천 (권장)",
    "existing_project": "지금 프로젝트의 기술 그대로",
}
VISUAL_TONES = {
    "calm": "차분함",
    "trust": "믿음직함",
    "lively": "활기차고 친근함",
    "pro": "전문적",
}
WEB_BEHAVIORS = {
    "mobile": "휴대폰으로 현장에서",
    "desktop": "PC로 자리에서",
    "balanced": "둘 다 비슷하게",
}
MAX_CHOICE_OPTIONS = 4
"""client native 질문 UI(Claude Code AskUserQuestion 등)가 한 문항에 보여 줄 수 있는 선택지 수."""
MIN_CHOICE_OPTIONS = 2
MUST_FEATURES_ID = "design_must_features"
MAX_MUST_FEATURE_OPTIONS = 20
"""Must 기능은 개수 제한이 없어 선택지 4개 규칙의 유일한 예외다(클라이언트가 4개씩 나눠 묻는다)."""
SUGGESTIBLE_INTAKE_IDS = frozenset(
    {"work_type", "solution_family", "primary_surface", "app_domain_hint", "initial_audience"}
)
"""모델이 아이디어에서 추정해 미리 골라 둘 수 있는 1차 문항."""

# 작업 유형별 질문: (id, 문구, 종류, 필수)
_WORK_TYPE_QUESTIONS: dict[str, list[tuple[str, str, WizardQuestionKind, bool]]] = {
    "new_project": [
        ("new_project_launch_context", "처음엔 어디서·어떻게 쓰게 하나요?", TEXT, False),
        (
            "new_project_known_dependencies",
            "이미 정해진 기술이나 외부 서비스가 있나요?",
            TEXTAREA,
            False,
        ),
    ],
    "feature_addition": [
        (
            "feature_affected_contracts",
            "새 기능 때문에 영향을 받는 기존 화면·기능이 있나요?",
            TEXTAREA,
            True,
        ),
        ("feature_compatibility", "꼭 그대로 유지돼야 하는 기존 동작이 있나요?", TEXTAREA, False),
        ("feature_migration", "기존 데이터나 설정을 옮겨야 하나요?", TEXTAREA, False),
    ],
    "bug_fix": [
        ("bug_reproduction", "언제, 어떻게 하면 문제가 생기나요?", TEXTAREA, True),
        ("bug_expected_actual", "원래는 어떻게 돼야 하나요?", TEXTAREA, False),
        ("bug_impact", "얼마나 자주, 누구에게 생기나요?", TEXTAREA, False),
    ],
    "refactoring": [
        ("refactor_current_pain", "지금 구조에서 가장 불편한 점은 무엇인가요?", TEXTAREA, True),
        ("refactor_behavior_lock", "바뀌면 안 되는 동작이 있나요?", TEXTAREA, False),
        ("refactor_baseline", "지금 테스트·성능 상태는 어떤가요?", TEXTAREA, False),
    ],
    "documentation_ops": [
        ("docs_audience", "이 문서는 누가, 언제 보게 되나요?", TEXTAREA, True),
        ("docs_source_material", "참고할 기존 자료가 있나요?", TEXTAREA, False),
        ("docs_maintenance_owner", "누가 얼마나 자주 고치나요?", TEXTAREA, False),
    ],
}


def _work_type_visibility(work_type: str) -> dict[str, list[str]]:
    if work_type in MAINTENANCE_KINDS:
        return {"maintenance_kind": [work_type]}
    return {"work_type": [work_type]}


def _choice(
    question_id: str,
    label: str,
    labels: Mapping[str, str],
    *,
    kind: WizardQuestionKind = SELECT,
    description: str = "",
    required: bool = True,
    allow_other: bool = False,
    other_label: str = "기타 (직접 입력)",
    max_selections: int | None = None,
    exclusive: list[str] | None = None,
    visible_when: dict[str, list[str]] | None = None,
    required_unless: list[str] | None = None,
) -> AdaptiveWizardQuestion:
    return AdaptiveWizardQuestion(
        id=question_id,
        label=label,
        description=description,
        kind=kind,
        required=required,
        options=list(labels),
        option_labels=dict(labels),
        allow_other=allow_other,
        other_label=other_label,
        max_selections=max_selections,
        exclusive_options=exclusive or [],
        visible_when=visible_when or {},
        required_unless=required_unless or [],
    )


def intake_questions(
    suggested_answers: Mapping[str, object] | None = None,
) -> list[AdaptiveWizardQuestion]:
    """1차 고정 질문. ``suggested_answers``는 검증 뒤 미리 골라 둔 값(default)이 된다."""

    questions = [
        _choice("work_type", "어떤 작업인가요?", WORK_TYPES),
        _choice(
            "maintenance_kind",
            "어떤 정리인가요?",
            MAINTENANCE_KINDS,
            visible_when={"work_type": [MAINTENANCE_WORK]},
        ),
        _choice(
            "solution_family",
            "무엇을 만들고 싶나요?",
            SOLUTION_FAMILIES,
            kind=MULTISELECT,
            description="여러 개 골라도 돼요.",
            allow_other=True,
            other_label="기타 (예: 개발자 도구)",
        ),
        _choice(
            "primary_surface",
            "어디에서 쓰게 되나요?",
            SURFACES,
            kind=MULTISELECT,
            description="여러 개 골라도 돼요. 잘 모르면 AI가 추천해요.",
            allow_other=True,
            other_label="기타 (PC 프로그램·메신저·키오스크 등)",
            exclusive=[AI_SUGGEST_OPTION],
            visible_when=PRODUCT_ONLY,
        ),
        _choice(
            "app_domain_hint",
            "어떤 분야인가요?",
            DOMAINS,
            kind=MULTISELECT,
            description=f"최대 {DOMAIN_MAX}개까지 고를 수 있어요.",
            allow_other=True,
            other_label="기타 (예: 소통, 콘텐츠, 교육, 돈 관리, 날씨)",
            max_selections=DOMAIN_MAX,
            visible_when=PRODUCT_ONLY,
        ),
        _choice(
            "pain_points",
            "지금 무엇이 불편하거나 번거로운가요?",
            PAIN_POINTS,
            kind=MULTISELECT,
            description="해당하는 걸 고르거나 아래에 직접 적어 주세요. 둘 중 하나만 해도 돼요.",
            allow_other=True,
            required_unless=["pain_detail"],
        ),
        AdaptiveWizardQuestion(
            id="pain_detail",
            label="불편한 점을 조금 더 적어 주세요",
            description="예: 전화·카톡으로 예약을 받다 보니 시간이 겹치는 일이 잦아요",
            kind=TEXTAREA,
            required=False,
        ),
        AdaptiveWizardQuestion(
            id="desired_change",
            label="만들어지면 무엇이 달라지면 좋겠나요?",
            description="비워 두면 AI가 채워서 다음 질문에서 확인받아요.",
            kind=TEXTAREA,
            required=False,
            ai_fill_when_empty=True,
        ),
        _choice(
            "success_signals",
            "잘 만들었다고 느끼려면, 무엇이 달라져 있어야 하나요?",
            SUCCESS_SIGNALS,
            kind=MULTISELECT,
            description="여러 개 골라도 돼요.",
            allow_other=True,
            exclusive=[AI_SUGGEST_OPTION],
        ),
        AdaptiveWizardQuestion(
            id="success_amount",
            label="얼마나 달라지면 좋겠나요?",
            description="예: 예약 200건, 노쇼 20% 감소. 모르면 비워 두세요.",
            kind=TEXT,
            required=False,
        ),
        _choice(
            "initial_audience",
            "처음엔 누가 쓰게 되나요?",
            AUDIENCES,
            description="문서의 양과 보안 수준을 정하는 데 써요.",
        ),
        *[
            AdaptiveWizardQuestion(
                id=question_id,
                label=label,
                kind=kind,
                required=required,
                visible_when=_work_type_visibility(work_type),
            )
            for work_type, items in _WORK_TYPE_QUESTIONS.items()
            for question_id, label, kind, required in items
        ],
        _choice(
            "constraints_risks",
            "꼭 지켜야 하거나 걱정되는 점이 있나요?",
            CONSTRAINTS,
            kind=MULTISELECT,
            required=False,
            allow_other=True,
        ),
        _choice(
            "tech_stack",
            "어떤 기술로 만들지 정해 둔 게 있나요?",
            TECH_STACK,
            allow_other=True,
            other_label="정해 둔 기술 (직접 입력)",
        ),
        AdaptiveWizardQuestion(
            id="target_context",
            label="이미 있는 프로젝트·폴더가 있나요?",
            description="비워 두면 AI가 현재 프로젝트에서 찾아봐요.",
            kind=TEXT,
            required=False,
        ),
    ]
    if not suggested_answers:
        return questions
    return [_with_default(question, suggested_answers) for question in questions]


def suggestion_warnings(suggested_answers: Mapping[str, object] | None) -> list[str]:
    """적용하지 못한 추정값을 사람에게 알릴 경고로 바꾼다."""

    if not suggested_answers:
        return []
    by_id = {question.id: question for question in intake_questions()}
    warnings = []
    for key, value in suggested_answers.items():
        question = by_id.get(key)
        if key not in SUGGESTIBLE_INTAKE_IDS or question is None:
            warnings.append(f"추정값을 미리 고를 수 없는 문항이라 무시했습니다: {key}")
        elif _valid_prefill(question, value) is None:
            warnings.append(f"선택지에 없는 추정값이라 무시했습니다: {key}")
    return warnings


def _with_default(
    question: AdaptiveWizardQuestion, suggested_answers: Mapping[str, object]
) -> AdaptiveWizardQuestion:
    """요청에서 확정된 값을 미리 채우고 ``from_request``로 표시한다(클라이언트는 묻지 않는다)."""

    if question.id not in SUGGESTIBLE_INTAKE_IDS or question.id not in suggested_answers:
        return question
    prefilled = _valid_prefill(question, suggested_answers[question.id])
    if prefilled is None:
        return question
    default, other = prefilled
    return question.model_copy(
        update={"default": default, "default_other_text": other, "from_request": True}
    )


def _valid_prefill(
    question: AdaptiveWizardQuestion, value: object
) -> tuple[str | list[str] | None, str | None] | None:
    """미리 채울 (선택값, 기타 직접 입력). 선택지 밖 값은 기타를 허용할 때만 직접 입력이 된다."""

    if isinstance(value, dict):
        try:
            value = AdaptiveWizardSelectionAnswer.model_validate(value)
        except ValueError:
            return None
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        selected = list(value.selected)
        other = other_text(value).strip() or None
    else:
        values = answer_values(value)
        selected = [item for item in values if item in question.options]
        other = ", ".join(item for item in values if item not in question.options) or None
    if set(selected) - set(question.options) or (other and not question.allow_other):
        return None
    if not selected and not other:
        return None
    is_select = question.kind is SELECT
    if is_select and (len(selected) > 1 or (selected and other)):
        return None
    if (
        question.max_selections is not None
        and len(selected) + int(other is not None) > question.max_selections
    ):
        return None
    default: str | list[str] | None = (selected[0] if selected else None) if is_select else None
    if not is_select:
        default = selected or None
    try:
        AdaptiveWizardQuestion.model_validate(
            {
                **question.model_dump(mode="json"),
                "default": default,
                "default_other_text": other,
                "from_request": True,
            }
        )
    except ValueError:
        return None
    return default, other


def prefilled_summary(questions: list[AdaptiveWizardQuestion]) -> list[str]:
    """요청에서 확정해 묻지 않는 문항을 사람이 확인할 한 줄씩으로 만든다(코드값 대신 표시명)."""

    lines = []
    for question in questions:
        answer = question.prefilled_answer() if question.from_request else None
        if answer is None:
            continue
        parts = [question.label_for(item) for item in selected_values(answer)]
        extra = other_text(answer)
        if extra:
            parts.append(f"기타 — {extra}")
        lines.append(f"{question.label} → {', '.join(parts)}")
    return lines


def required_product_design_question_ids(
    intake_answers: Mapping[str, object],
    ai_inferred: Mapping[str, str] | None = None,
) -> set[str]:
    """2차 질문에 반드시 들어가야 하는 문항 ID."""

    view = build_intake_view(intake_answers)
    ids: set[str] = set()
    if view.is_product:
        # 디자인(분위기·메인 색·웹 반응형)은 묻지 않는다. 시제품은 문서 반영 후 사용자가 별도
        # 프로토타입 스킬로 만든다.
        ids.add("design_frequent_user_tasks")
    if view.work_type in {"new_project", "feature_addition"} and "mvp_scope" not in intake_answers:
        ids.add("design_must_features")
    ids |= {f"confirm_{question_id}" for question_id in confirm_question_sources(ai_inferred)}
    return ids


def confirm_question_sources(ai_inferred: Mapping[str, str] | None) -> list[str]:
    """2차에서 AI 제안을 확인받아야 하는 1차 문항 ID."""

    if not ai_inferred:
        return []
    return [
        question_id
        for question_id in CONFIRMABLE_INTAKE_IDS
        if ai_inferred.get(question_id) in {"unknown", "empty"}
    ]


def color_candidate_options(intake_answers: Mapping[str, object]) -> dict[str, str]:
    """2차 메인 색 선택지: 추천 색 hex → 표시명."""

    domains = list(build_intake_view(intake_answers).domains)
    return {item.hex: item.option_label() for item in recommend_seed_colors(domains)}


def product_design_question_guidance(
    intake_answers: Mapping[str, object],
    ai_inferred: Mapping[str, str] | None = None,
) -> list[AdaptiveWizardQuestion]:
    """서버가 요구하는 2차 필수 질문의 기준 정의.

    모델은 ``design_must_features`` 선택지를 실제 분석한 기능 후보로, ``confirm_*`` 선택지를
    자신의 AI 제안 문장으로 바꿔 쓴다. 디자인 질문은 만들지 않는다.
    """

    required = required_product_design_question_ids(intake_answers, ai_inferred)
    view = build_intake_view(intake_answers)
    guidance: list[AdaptiveWizardQuestion] = []
    if "design_frequent_user_tasks" in required:
        guidance.append(
            AdaptiveWizardQuestion(
                id="design_frequent_user_tasks",
                label="사용자가 이 제품에서 자주 하는 작업은 무엇인가요?",
                description="중요한 순서대로 적어 주세요.",
                kind=TEXTAREA,
            )
        )
    if "design_must_features" in required:
        features = list(dict.fromkeys(view.scope_features))[:MAX_MUST_FEATURE_OPTIONS] or [
            "핵심 흐름"
        ]
        guidance.append(
            AdaptiveWizardQuestion(
                id="design_must_features",
                label="첫 버전에 꼭 있어야 하는 기능을 골라 주세요.",
                description="개수 제한은 없어요. 고르지 않은 기능은 ‘이번엔 안 함’으로 기록돼요.",
                kind=MULTISELECT,
                options=features,
                allow_other=True,
            )
        )
    for source_id in confirm_question_sources(ai_inferred):
        guidance.append(_confirm_template(source_id))
    return guidance


def _confirm_template(source_id: str) -> AdaptiveWizardQuestion:
    if source_id == "primary_surface":
        surfaces = {key: value for key, value in SURFACES.items() if key != AI_SUGGEST_OPTION}
        question = _choice(
            "confirm_primary_surface",
            "AI가 추천한 사용 환경이 맞나요?",
            surfaces,
            kind=MULTISELECT,
            description="AI가 골라 둔 곳이 맞으면 그대로, 아니면 바꿔 주세요.",
            allow_other=True,
        )
        return question.model_copy(update={"default": ["web_app"]})
    label = {"success_signals": "성공 기준", "desired_change": "바라는 모습"}[source_id]
    return AdaptiveWizardQuestion(
        id=f"confirm_{source_id}",
        label=f"AI가 채운 {label}이 맞나요?",
        description="AI 제안 중 맞는 것을 고르고, 아니면 고칠 내용을 직접 적어 주세요.",
        kind=SELECT,
        options=[CONFIRM_SUGGESTION, CONFIRM_ALTERNATIVE],
        allow_other=True,
        other_label="고칠게요 (직접 입력)",
    )


def validate_design_questions(
    questions: list[AdaptiveWizardQuestion],
    intake_question_ids: set[str] | None = None,
    required_question_ids: set[str] | None = None,
) -> list[AdaptiveWizardQuestion]:
    """모델이 만든 2차 질문이 질문 예산·안전한 선언형 계약을 지키는지 확인한다.

    메인 색 후보는 모델이 제품에 맞게 제안할 수 있으며, 대비 보정이 필요한 후보 표시명에는
    서버가 보정 안내를 붙여 돌려준다.
    """

    if not 3 <= len(questions) <= MAX_DESIGN_QUESTIONS:
        raise ValueError(f"2차 맞춤 Wizard는 3~{MAX_DESIGN_QUESTIONS}개 질문이어야 합니다.")
    ids = [question.id for question in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("2차 Wizard 문항 ID는 중복될 수 없습니다.")
    repeated_intake_ids = set(ids).intersection(intake_question_ids or set())
    if repeated_intake_ids:
        raise ValueError(
            "2차 Wizard는 1차 문항을 다시 사용할 수 없습니다: "
            + ", ".join(sorted(repeated_intake_ids))
        )
    if "document_output_mode" in ids:
        raise ValueError(
            "2차 Wizard는 파일 반영 정책을 다시 물을 수 없습니다: document_output_mode"
        )
    missing_required = sorted((required_question_ids or set()) - set(ids))
    if missing_required:
        raise ValueError(_MISSING_DESIGN_MESSAGE + ", ".join(missing_required))
    if any(question.visible_when for question in questions):
        raise ValueError(
            "2차 맞춤 Wizard는 이미 분석된 질문만 포함하므로 조건부 문항을 사용할 수 없습니다."
        )
    for question in questions:
        _validate_design_shape(question)
        _validate_option_count(question)
    return [_with_color_notes(question) for question in questions]


def _with_color_notes(question: AdaptiveWizardQuestion) -> AdaptiveWizardQuestion:
    if question.id != COLOR_CHOICE_ID:
        return question
    labels = {
        option: with_contrast_note(question.option_labels[option], option)
        for option in question.options
    }
    return question.model_copy(update={"option_labels": labels})


def _validate_option_count(question: AdaptiveWizardQuestion) -> None:
    """선택형 문항이 native 질문 UI 한 문항(선택지 2~4개)에 그대로 들어가는지 확인한다.

    개수 제한 없는 ``design_must_features``만 예외이며, 클라이언트가 4개씩 나눠 묻는다.
    """

    if question.kind not in {SELECT, MULTISELECT}:
        return
    count = len(question.options)
    if question.id == MUST_FEATURES_ID:
        if not 1 <= count <= MAX_MUST_FEATURE_OPTIONS:
            raise ValueError(
                f"{MUST_FEATURES_ID} 선택지는 1~{MAX_MUST_FEATURE_OPTIONS}개여야 합니다."
            )
        return
    if not MIN_CHOICE_OPTIONS <= count <= MAX_CHOICE_OPTIONS:
        raise ValueError(
            f"{question.id} 선택지는 {MIN_CHOICE_OPTIONS}~{MAX_CHOICE_OPTIONS}개여야 합니다"
            f"(현재 {count}개). 4개를 넘으면 묶거나 나머지는 기타 입력으로 받으세요."
        )


def _validate_design_shape(question: AdaptiveWizardQuestion) -> None:
    if question.id == MUST_FEATURES_ID and (
        question.kind is not MULTISELECT or question.max_selections is not None
    ):
        raise ValueError("design_must_features는 개수 제한 없는 복수 선택이어야 합니다.")
    if question.id == "design_color_choice":
        if question.kind is not SELECT or not question.allow_other:
            raise ValueError("design_color_choice는 기타 입력을 허용하는 단일 선택이어야 합니다.")
        if any(not HEX_PATTERN.fullmatch(option) for option in question.options):
            raise ValueError(
                "design_color_choice 선택지는 #RRGGBB 색 값이어야 합니다(예: #2F6FB5)."
            )
        if len({option.upper() for option in question.options}) != len(question.options):
            raise ValueError("design_color_choice 선택지에 같은 색이 중복되었습니다.")
        if set(question.options) - set(question.option_labels):
            raise ValueError(
                "design_color_choice 선택지마다 '이름 · #RRGGBB — 이유' 표시명이 필요합니다."
            )
    if question.id == "confirm_primary_surface":
        allowed = set(SURFACES) - {AI_SUGGEST_OPTION}
        if question.kind is not MULTISELECT or set(question.options) - allowed:
            raise ValueError(
                "confirm_primary_surface는 1차 사용 환경 선택지의 복수 선택이어야 합니다."
            )
    elif question.id.startswith("confirm_") and (
        question.kind is not SELECT or not question.allow_other
    ):
        raise ValueError(f"{question.id}는 AI 제안과 직접 입력을 고르는 단일 선택이어야 합니다.")


def validate_design_color_answer(answer: object) -> None:
    """직접 고른 메인 색이 #RRGGBB인지 확인한다."""

    other = getattr(answer, "other_text", None)
    if other is not None and not HEX_PATTERN.match(other.strip()):
        raise ValueError("메인 색상은 #RRGGBB 형식으로 적어 주세요. 예: #2F6FB5")
