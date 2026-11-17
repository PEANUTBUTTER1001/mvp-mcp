"""Wizard 답변을 디자인 SSOT의 최소 계약으로 정규화한다."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal

from .adaptive_wizard_model import AdaptiveWizardSelectionAnswer
from .intake_view import MOBILE_SURFACES, answer_text, answer_values, build_intake_view
from .model import (
    DesignContract,
    DesignDecisionStatus,
    DesignDirection,
    DesignPlatform,
    ErrorState,
    LayoutArchetype,
    ResponsivePriority,
    ScreenSpec,
    UserFlow,
)

_AVOID = [
    "근거 없는 KPI 카드, 가짜 차트, 활동 피드를 만들지 않는다.",
    "모든 영역을 둥근 카드로 감싸지 않는다.",
    "그라데이션·유리 효과·큰 그림자는 제품 근거가 있을 때만 쓴다.",
    "색상보다 타이포그래피·여백·정렬로 위계를 만든다.",
]
_DEFAULT_SEED = "#0F766E"
FREQUENT_TASKS_ID = "design_frequent_user_tasks"
MAX_CONTRACT_SCREENS = 5
"""디자인 계약 화면 수 상한. 넘는 자주 하는 작업은 frequent_user_tasks에만 남는다."""
_SCREEN_STATES = ("기본", "빈 상태", "저장 중", "저장 성공", "입력 오류")
_HEX = re.compile(r"#[0-9a-fA-F]{6}")
_TONE_LABELS = {
    "calm": "차분함",
    "trust": "믿음직함",
    "lively": "활기차고 친근함",
    "friendly": "친근함",
    "pro": "전문적",
}
_DESKTOP_LIKE = {"desktop_app", "onsite_device"}


def build_product_design_contract(
    intake: Mapping[str, object],
    answers: Mapping[str, object],
    option_labels: Mapping[str, Mapping[str, str]] | None = None,
) -> DesignContract | None:
    """1차·2차 답변(구·신 형식 모두)을 디자인 계약으로 만든다."""

    view = build_intake_view(intake, answers, option_labels=option_labels)
    if not view.is_product:
        return None
    tasks = frequent_tasks(answers, option_labels) or [
        "핵심 작업을 빠르게 시작하고 결과를 확인한다."
    ]
    surfaces = set(view.surfaces)
    seed, origin = _seed_color(answers)
    confirmed_color = origin == "user"
    responsive = answer_text(answers.get("design_web_behavior"))
    priority = (
        ResponsivePriority(responsive)
        if responsive in {item.value for item in ResponsivePriority}
        else (ResponsivePriority.MOBILE if view.mobile_only else ResponsivePriority.BALANCED)
    )
    layout = (
        LayoutArchetype.LIST_DETAIL
        if any(word in " ".join(tasks) for word in ("목록", "기록", "검토", "관리"))
        else LayoutArchetype.WORKSPACE
    )
    primary_job = tasks[0]
    return DesignContract(
        visual_direction=DesignDirection(
            product_category=" ".join(
                value for value in (view.domain_text or "제품 앱", view.target_context) if value
            ),
            core_user=view.users,
            frequent_user_tasks=tasks,
            primary_user_job=primary_job,
            layout_archetype=layout,
            platform_grammar=_platform_grammar(surfaces),
            platform_targets=_platform_targets(surfaces),
            responsive_priority=priority,
            visual_tone=_visual_tone(answers.get("design_visual_tone"))
            or "차분하고 정돈된 작업 도구; 장식보다 정보 위계와 조작의 명확성을 우선한다.",
            avoid_patterns=_AVOID,
            seed_color=seed,
            color_status=(
                DesignDecisionStatus.CONFIRMED
                if confirmed_color
                else DesignDecisionStatus.RECOMMENDED
            ),
            color_origin=origin,
            decision_statuses={
                "frequent_user_tasks": DesignDecisionStatus.CONFIRMED,
                "seed_color": (
                    DesignDecisionStatus.CONFIRMED
                    if confirmed_color
                    else DesignDecisionStatus.RECOMMENDED
                ),
                "layout_archetype": DesignDecisionStatus.RECOMMENDED,
                "platform_targets": DesignDecisionStatus.RECOMMENDED,
            },
            rationale={
                "layout_archetype": "반복 작업을 시작하고 결과·상태를 확인하는 흐름을 우선한다.",
                "seed_color": _seed_rationale(origin),
                "platform_targets": (
                    "주 제공 화면과 실제 입력 환경을 기준으로 필요한 프로파일만 선택한다."
                ),
            },
        ),
        screens=_screens(tasks, view.goal or primary_job),
        user_flows=_user_flows(tasks),
        error_states=[
            ErrorState(
                trigger=view.problem or "입력값을 확인할 수 없음",
                user_message="입력 내용을 확인한 뒤 다시 시도하세요.",
                recovery="오류가 표시된 입력 또는 그룹을 수정하고 저장을 다시 시도한다.",
            )
        ],
    )


def frequent_tasks(
    answers: Mapping[str, object],
    option_labels: Mapping[str, Mapping[str, str]] | None = None,
) -> list[str]:
    """자주 하는 작업 답을 사람이 읽는 작업 목록으로 만든다.

    선택형 답은 option 코드(예: check_now) 대신 ``option_labels`` 표시명을 쓰고, 기타 입력과
    서술형 답은 줄·쉼표·번호·띄운 가운뎃점으로 나눈다("오늘·내일 예보 확인"은 한 작업).
    """

    value = answers.get(FREQUENT_TASKS_ID)
    labels = (option_labels or {}).get(FREQUENT_TASKS_ID, {})
    if isinstance(value, (list, AdaptiveWizardSelectionAnswer)):
        picked = [labels.get(item, item) for item in answer_values(value)]
        extra = getattr(value, "other_text", None)
        return _split_tasks(", ".join([*picked, *([extra] if extra else [])]))
    return _split_tasks(answer_text(value))


def _split_tasks(text: str) -> list[str]:
    return [
        item.strip(" -•")
        for item in re.split(r"[\n,;]|\s+·\s+|(?:\d+[.)])", text)
        if item.strip(" -•")
    ]


def _screens(tasks: list[str], goal: str) -> list[ScreenSpec]:
    """자주 하는 작업마다 화면 하나(최대 ``MAX_CONTRACT_SCREENS``). 작업이 하나면 핵심 작업 화면."""

    if len(tasks) < 2:
        return [
            ScreenSpec(
                name="핵심 작업",
                route="/",
                purpose=goal,
                ui_elements=tasks[:3],
                states=list(_SCREEN_STATES),
            )
        ]
    return [
        ScreenSpec(
            name=task,
            route="/" if index == 0 else f"/task-{index + 1}",
            purpose=goal if index == 0 else f"{task}을(를) 빠르게 끝내고 결과를 확인해요.",
            ui_elements=[task],
            states=list(_SCREEN_STATES),
        )
        for index, task in enumerate(tasks[:MAX_CONTRACT_SCREENS])
    ]


def _user_flows(tasks: list[str]) -> list[UserFlow]:
    single = len(tasks) < 2
    return [
        UserFlow(
            name=task,
            steps=[
                "핵심 화면 진입" if single else f"{task} 화면 진입",
                task,
                "결과와 저장 상태 확인",
            ],
            exception_paths=["입력 오류를 해당 입력 또는 그룹에서 수정한 뒤 다시 시도"],
        )
        for task in tasks[: 1 if single else MAX_CONTRACT_SCREENS]
    ]


ColorOrigin = Literal["ai_recommended", "user", "default"]


def _seed_color(answers: Mapping[str, object]) -> tuple[str, ColorOrigin]:
    """(seed, origin). 직접 입력한 HEX > AI 추천 후보 선택 > 구형 서술 답의 HEX > 기본값."""

    choice = answers.get("design_color_choice")
    if choice is not None:
        custom = getattr(choice, "other_text", None)
        if custom and _HEX.fullmatch(custom.strip()):
            return custom.strip().upper(), "user"
        picked = [item for item in answer_values(choice) if _HEX.fullmatch(item)]
        if picked:
            return picked[0].upper(), "ai_recommended"
    legacy = _HEX.search(answer_text(answers.get("design_color_source")))
    if legacy:
        return legacy.group(0).upper(), "user"
    return _DEFAULT_SEED, "default"


def _seed_rationale(origin: str) -> str:
    return {
        "user": "사용자가 직접 지정한 색상을 보존하고 접근성 대비만 보정한다.",
        "ai_recommended": "분야에 맞춰 AI가 추천한 후보 중 사용자가 고른 색상이다.",
    }.get(origin, "사용자 색상이 없으면 상태 색상과 혼동이 적은 청록 계열을 권장한다.")


def _visual_tone(value: object) -> str:
    labels = [_TONE_LABELS.get(item, item) for item in answer_values(value)]
    extra = getattr(value, "other_text", None)
    if labels and not isinstance(value, str):
        return " · ".join(labels + ([extra] if extra else []))
    return answer_text(value)


def _platform_targets(surfaces: set[str]) -> list[DesignPlatform]:
    targets: list[DesignPlatform] = []
    if "web_app" in surfaces:
        return [DesignPlatform.WEB, DesignPlatform.MOBILE, DesignPlatform.DESKTOP]
    if surfaces & MOBILE_SURFACES:
        targets.append(DesignPlatform.MOBILE)
    if "cross_platform_app" in surfaces or surfaces & _DESKTOP_LIKE:
        targets.append(DesignPlatform.DESKTOP)
    return targets or [DesignPlatform.WEB]


def _platform_grammar(surfaces: set[str]) -> str:
    if surfaces == {"ios_app"}:
        return "apple"
    if surfaces == {"android_app"}:
        return "material_3"
    return "web_neutral"
