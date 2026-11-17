"""1·2차 답변을 구·신 설문 schema 구분 없이 읽는 단일 해석 계층.

새 설문은 복수 선택·AI 추정·2차 확인 질문을 쓰고, 이전 Run은 문자열 답을 저장했다. 문서 초안·
디자인 계약·템플릿 선택은 이 모듈의 ``IntakeView``만 읽어 두 형식을 같은 의미로 다룬다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from .adaptive_wizard_model import (
    AI_SUGGEST_OPTION,
    AdaptiveWizardSelectionAnswer,
    AnswerValue,
    other_text,
    selected_values,
)

PRODUCT_FAMILY = "product_application"
MOBILE_SURFACES = frozenset({"android_app", "ios_app", "cross_platform_app"})
DEFAULT_SURFACE = "web_app"
AI_RECOMMENDED_STACK = "ai_recommended"
EXISTING_PROJECT_STACK = "existing_project"
MAINTENANCE_WORK = "maintenance"
LEGACY_AI_STACK = "AI 권장안 사용"
WORK_TYPE_REQUIRED_DETAIL = {
    "feature_addition": "feature_affected_contracts",
    "bug_fix": "bug_reproduction",
    "refactoring": "refactor_current_pain",
    "documentation_ops": "docs_audience",
}
CONFIRMABLE_INTAKE_IDS = ("primary_surface", "success_signals", "desired_change")
"""2차에서 confirm_<id> 질문으로 확인받는 AI 추정 1차 문항."""
CONFIRM_SUGGESTION = "AI_SUGGESTION"
CONFIRM_ALTERNATIVE = "AI_ALTERNATIVE"
CONFIRM_PLACEHOLDERS = frozenset({CONFIRM_SUGGESTION, CONFIRM_ALTERNATIVE})
"""confirm_* 템플릿의 자리표시 option. 모델이 단 option_labels 문장으로만 해석한다."""

LABELS: dict[str, dict[str, str]] = {
    "app_domain_hint": {
        "booking": "예약·일정",
        "commerce": "쇼핑·결제",
        "community": "소통·커뮤니티",
        "content": "콘텐츠·게시",
        "business": "업무·관리",
        "education": "교육·학습",
        "fitness": "건강·운동",
        "finance": "돈·가계",
        "productivity": "기록·생산성",
        "general_business": "일반 업무",
        "communication": "커뮤니케이션",
        "content_publishing": "콘텐츠 게시",
    },
    "initial_audience": {
        "solo": "나 혼자",
        "known": "아는 사람 (팀·가족)",
        "customers": "특정 고객·회원",
        "public": "누구나 (공개)",
    },
    "success_signals": {
        "time": "시간이 줄어든다",
        "fewer_mistakes": "실수가 줄어든다",
        "more_users": "더 많은 사람이 쓴다",
        "revenue": "매출·예약·사용자가 는다",
        "self_use": "내가 매일 쓴다",
    },
    "pain_points": {
        "slow": "시간이 오래 걸려요",
        "mistake": "실수·빠뜨림이 생겨요",
        "contact": "연락·확인이 번거로워요",
        "scattered": "정보가 흩어져 있어요",
        "cost": "돈이 들어요",
    },
}

Answers = Mapping[str, AnswerValue | object]


@dataclass(frozen=True)
class IntakeView:
    """문서 초안이 쓰는 해석된 설문 결과."""

    work_type: str
    families: tuple[str, ...]
    surfaces: tuple[str, ...]
    domains: tuple[str, ...]
    domain_text: str
    problem: str
    goal: str
    success: str
    audience: str
    users: str
    tech_stack: str
    uses_ai_stack: bool
    scope_features: tuple[str, ...]
    target_context: str
    ai_inferred: dict[str, str] = field(default_factory=dict)

    @property
    def is_product(self) -> bool:
        return PRODUCT_FAMILY in self.families

    @property
    def has_web(self) -> bool:
        return DEFAULT_SURFACE in self.surfaces

    @property
    def mobile_only(self) -> bool:
        return bool(set(self.surfaces) & MOBILE_SURFACES) and not self.has_web


def build_intake_view(
    intake: Answers,
    design: Answers | None = None,
    ai_inferred: Mapping[str, str] | None = None,
    option_labels: Mapping[str, Mapping[str, str]] | None = None,
) -> IntakeView:
    """1차·2차 답변을 해석한다. 2차 확인 답변이 있으면 AI 추정값보다 우선한다."""

    design = design or {}
    families = _with_other_keywords(intake.get("solution_family"), "solution_family") or ("other",)
    surfaces = _resolved_surfaces(intake, design)
    domains = _with_other_keywords(intake.get("app_domain_hint"), "app_domain_hint")
    domain_other = _other(intake.get("app_domain_hint"))
    domain_text = ", ".join(
        [LABELS["app_domain_hint"].get(item, item) for item in domains]
        + ([domain_other] if domain_other else [])
    )
    pain = _join(
        [LABELS["pain_points"].get(item, item) for item in _values(intake.get("pain_points"))]
        + [_text(intake.get("pain_detail"))]
    )
    problem = _first(_text(intake.get("problem")), pain)
    labels = option_labels or {}
    goal = _first(
        _confirmed_text(design, "desired_change", labels),
        _text(intake.get("desired_change")),
        _text(intake.get("goal")),
        problem,
    )
    success = _first(
        _confirmed_text(design, "success_signals", labels),
        _success_text(intake),
        _text(intake.get("success_criteria")),
    )
    audience_value = _text(intake.get("initial_audience"))
    audience = LABELS["initial_audience"].get(audience_value, audience_value)
    users = _first(
        _text(design.get("design_users")),
        _text(intake.get("affected_users")),
        audience,
        "핵심 사용자",
    )
    tech_stack, uses_ai_stack = _tech_stack(intake.get("tech_stack"))
    work_type = _work_type(intake)
    return IntakeView(
        work_type=work_type,
        families=families,
        surfaces=surfaces,
        domains=domains,
        domain_text=domain_text,
        problem=problem,
        goal=goal,
        success=success,
        audience=audience,
        users=users,
        tech_stack=tech_stack,
        uses_ai_stack=uses_ai_stack,
        scope_features=_scope_features(
            intake, design, work_type, goal, labels.get("design_must_features", {})
        ),
        target_context=_text(intake.get("target_context")),
        ai_inferred=dict(ai_inferred or {}),
    )


MUST_FEATURE_SOFT_LIMIT = 6


def scope_advice(design: Answers | None) -> str | None:
    """첫 버전 기능을 많이 고른 경우 문서 작성에 줄 범위 안내."""

    if not design:
        return None
    count = len(_values(design.get("design_must_features"))) + int(
        bool(_other(design.get("design_must_features")))
    )
    if count < MUST_FEATURE_SOFT_LIMIT:
        return None
    return (
        f"첫 버전 기능을 {count}개 골랐습니다. 문서에서 사용자 확인을 거쳐 "
        "‘첫 버전 / 다음 버전’으로 나눈 안을 함께 제시하고, 나눈 결과는 추론으로 표시하세요."
    )


def answer_values(value: object) -> list[str]:
    """임의 답(문자열·목록·선택+기타)을 선택값 목록으로 읽는다."""
    return _values(value)


def answer_text(value: object) -> str:
    """임의 답을 사람이 읽을 한 줄 문자열로 만든다."""
    return _text(value)


def _resolved_surfaces(intake: Answers, design: Answers) -> tuple[str, ...]:
    confirmed = _with_other_keywords(design.get("confirm_primary_surface"), "primary_surface")
    if confirmed:
        return confirmed
    values = _with_other_keywords(intake.get("primary_surface"), "primary_surface")
    return tuple(item for item in values if item != AI_SUGGEST_OPTION) or (DEFAULT_SURFACE,)


# 선택지를 4개로 줄이며 '기타'로 옮긴 값. 기타 입력의 키워드로 기존 분류 코드를 되살려
# 추천 색·프로젝트 유형·플랫폼 판단이 이전과 같게 동작하게 한다. 저장된 원래 답은 바꾸지 않는다.
OTHER_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "solution_family": {
        "developer_tool": ("개발자", "개발 도구", "CLI", "SDK", "MCP", "플러그인"),
    },
    "primary_surface": {
        "desktop_app": ("PC", "데스크톱", "데스크탑", "윈도우", "Windows", "macOS", "Mac"),
        "chat_bot": ("메신저", "챗봇", "카카오톡", "카톡", "슬랙", "Slack", "텔레그램", "디스코드"),
        "onsite_device": ("키오스크", "태블릿", "현장 기기", "POS"),
    },
    "app_domain_hint": {
        "fitness": ("건강", "운동", "헬스", "PT", "피트니스", "다이어트"),
        "community": ("소통", "커뮤니티", "채팅", "모임"),
        "content": ("콘텐츠", "블로그", "게시", "뉴스"),
        "education": ("교육", "학습", "강의", "공부"),
        "finance": ("돈", "가계", "금융", "자산"),
        "productivity": ("기록", "메모", "할 일", "생산성"),
    },
}


def _with_other_keywords(value: object, question_id: str) -> tuple[str, ...]:
    """선택값에 기타 입력에서 찾은 분류 코드를 덧붙인다(중복 제거, 순서 유지)."""

    values = [item for item in _values(value) if item]
    text = _other(value)
    if text:
        for code, keywords in OTHER_KEYWORDS.get(question_id, {}).items():
            if any(_contains_keyword(text, keyword) for keyword in keywords):
                values.append(code)
    return tuple(dict.fromkeys(values))


def _contains_keyword(text: str, keyword: str) -> bool:
    if keyword.isascii():
        pattern = rf"(?<![A-Za-z]){re.escape(keyword)}(?![A-Za-z])"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    return keyword in text


def _confirmed_text(
    design: Answers, intake_id: str, option_labels: Mapping[str, Mapping[str, str]]
) -> str:
    """확인 답을 문장으로 읽는다. 선택값은 option_labels 문장으로 바꾸고, 라벨 없는
    자리표시 코드(AI_SUGGESTION 등)는 버려 1차 AI 추정값으로 넘어가게 한다."""

    question_id = f"confirm_{intake_id}"
    value = design.get(question_id)
    if value is None:
        return ""
    labels = option_labels.get(question_id, {})
    picked = [labels.get(item, item) for item in _values(value)]
    return _first(
        _other(value), ", ".join(item for item in picked if item not in CONFIRM_PLACEHOLDERS)
    )


def _success_text(intake: Answers) -> str:
    signals = [item for item in _values(intake.get("success_signals")) if item != AI_SUGGEST_OPTION]
    labels = [LABELS["success_signals"].get(item, item) for item in signals]
    return _join(labels + [_text(intake.get("success_amount"))])


def _work_type(intake: Answers) -> str:
    """``maintenance``(구조·문서 정리)는 후속 문항의 세부 유형으로 해석한다."""

    work_type = _text(intake.get("work_type")) or "new_project"
    if work_type != MAINTENANCE_WORK:
        return work_type
    return _text(intake.get("maintenance_kind")) or "refactoring"


def _tech_stack(value: object) -> tuple[str, bool]:
    custom = _other(value)
    if custom:
        return custom, False
    text = _text(value)
    if text == EXISTING_PROJECT_STACK:
        return "지금 프로젝트의 기술 그대로 사용", False
    if not text or text in {AI_RECOMMENDED_STACK, LEGACY_AI_STACK}:
        return LEGACY_AI_STACK, True
    return text, False


def _scope_features(
    intake: Answers,
    design: Answers,
    work_type: str,
    goal: str,
    labels: Mapping[str, str],
) -> tuple[str, ...]:
    must = design.get("design_must_features")
    if must is not None:
        features = [labels.get(item, item) for item in _values(must)]
        extra = _other(must)
        if extra:
            features.extend(_split(extra))
        if features:
            return tuple(features)
    legacy = _text(intake.get("mvp_scope"))
    if legacy:
        return tuple(_split(legacy)) or (legacy,)
    detail_id = WORK_TYPE_REQUIRED_DETAIL.get(work_type)
    detail = _text(intake.get(detail_id)) if detail_id else ""
    source = _first(detail, goal)
    return tuple(_split(source)) or (source or "핵심 흐름",)


def _split(text: str) -> list[str]:
    parts = re.split(r"[\n,;·/]|(?:\d+[.)])", text)
    return [item.strip(" -•\t") for item in parts if item.strip(" -•\t")]


def _values(value: object) -> list[str]:
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return selected_values(value)
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()] if value else []
    return []


def _other(value: object) -> str:
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return other_text(value)
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, AdaptiveWizardSelectionAnswer):
        return _join([*value.selected, value.other_text or ""])
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).strip()


def _join(items: list[str]) -> str:
    return " · ".join(item for item in items if item)


def _first(*items: str) -> str:
    return next((item for item in items if item), "")
