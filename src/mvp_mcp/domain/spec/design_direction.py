"""Wizard 답변을 디자인 SSOT의 최소 계약으로 정규화한다."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .model import (
    DesignContract,
    DesignDecisionStatus,
    DesignDirection,
    LayoutArchetype,
    ResponsivePriority,
)

_AVOID = [
    "근거 없는 KPI 카드, 가짜 차트, 활동 피드를 만들지 않는다.",
    "모든 영역을 둥근 카드로 감싸지 않는다.",
    "그라데이션·유리 효과·큰 그림자는 제품 근거가 있을 때만 쓴다.",
    "색상보다 타이포그래피·여백·정렬로 위계를 만든다.",
]


def build_product_design_contract(
    intake: Mapping[str, str], answers: Mapping[str, str]
) -> DesignContract | None:
    if intake.get("solution_family") != "product_application":
        return None
    tasks = [
        item.strip(" -•")
        for item in re.split(r"[\n,;·]|(?:\d+[.)])", answers.get("design_frequent_user_tasks", ""))
        if item.strip(" -•")
    ]
    tasks = tasks or ["핵심 작업을 빠르게 시작하고 결과를 확인한다."]
    surface = intake.get("primary_surface", "")
    color_answer = answers.get("design_color_source", "")
    match = re.search(r"#[0-9a-fA-F]{6}", color_answer)
    seed = match.group(0).upper() if match else "#0F766E"
    responsive = answers.get("design_web_behavior", "")
    priority = (
        ResponsivePriority(responsive)
        if responsive in {item.value for item in ResponsivePriority}
        else (
            ResponsivePriority.MOBILE
            if surface in {"android_app", "ios_app", "cross_platform_app"}
            else ResponsivePriority.BALANCED
        )
    )
    layout = (
        LayoutArchetype.LIST_DETAIL
        if any(word in " ".join(tasks) for word in ("목록", "기록", "검토", "관리"))
        else LayoutArchetype.WORKSPACE
    )
    return DesignContract(
        visual_direction=DesignDirection(
            product_category=intake.get("app_domain_hint", "제품 앱"),
            core_user=intake.get("affected_users", "핵심 사용자"),
            frequent_user_tasks=tasks,
            primary_user_job=tasks[0],
            layout_archetype=layout,
            platform_grammar=(
                "apple"
                if surface == "ios_app"
                else "material_3" if surface == "android_app" else "web_neutral"
            ),
            responsive_priority=priority,
            visual_tone=answers.get("design_visual_tone", "")
            or "차분하고 정돈된 작업 도구; 장식보다 정보 위계와 조작의 명확성을 우선한다.",
            avoid_patterns=_AVOID,
            seed_color=seed,
            color_status=(
                DesignDecisionStatus.CONFIRMED if match else DesignDecisionStatus.RECOMMENDED
            ),
            decision_statuses={
                "frequent_user_tasks": DesignDecisionStatus.CONFIRMED,
                "seed_color": (
                    DesignDecisionStatus.CONFIRMED if match else DesignDecisionStatus.RECOMMENDED
                ),
                "layout_archetype": DesignDecisionStatus.RECOMMENDED,
            },
            rationale={
                "layout_archetype": "반복 작업을 시작하고 결과·상태를 확인하는 흐름을 우선한다.",
                "seed_color": "사용자 색상이 없으면 상태 색상과 혼동이 적은 청록 계열을 권장한다.",
            },
        )
    )
