"""Wizard 답변을 디자인 SSOT의 최소 계약으로 정규화한다."""

from __future__ import annotations

import re
from collections.abc import Mapping

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
    platform_targets = (
        [DesignPlatform.WEB, DesignPlatform.MOBILE, DesignPlatform.DESKTOP]
        if surface == "web_app"
        else (
            [DesignPlatform.MOBILE, DesignPlatform.DESKTOP]
            if surface == "cross_platform_app"
            else [DesignPlatform.MOBILE]
        )
    )
    primary_job = tasks[0]
    return DesignContract(
        visual_direction=DesignDirection(
            product_category=" ".join(
                value
                for value in (
                    intake.get("app_domain_hint", "제품 앱"),
                    intake.get("target_context", ""),
                )
                if value
            ),
            core_user=intake.get("affected_users", "핵심 사용자"),
            frequent_user_tasks=tasks,
            primary_user_job=primary_job,
            layout_archetype=layout,
            platform_grammar=(
                "apple"
                if surface == "ios_app"
                else "material_3" if surface == "android_app" else "web_neutral"
            ),
            platform_targets=platform_targets,
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
                "platform_targets": DesignDecisionStatus.RECOMMENDED,
            },
            rationale={
                "layout_archetype": "반복 작업을 시작하고 결과·상태를 확인하는 흐름을 우선한다.",
                "seed_color": "사용자 색상이 없으면 상태 색상과 혼동이 적은 청록 계열을 권장한다.",
                "platform_targets": (
                    "주 제공 화면과 실제 입력 환경을 기준으로 필요한 프로파일만 선택한다."
                ),
            },
        ),
        screens=[
            ScreenSpec(
                name="핵심 작업",
                route="/",
                purpose=intake.get("goal", primary_job),
                ui_elements=tasks[:3],
                states=["기본", "빈 상태", "저장 중", "저장 성공", "입력 오류"],
            )
        ],
        user_flows=[
            UserFlow(
                name=primary_job,
                steps=["핵심 화면 진입", primary_job, "결과와 저장 상태 확인"],
                exception_paths=["입력 오류를 해당 입력 또는 그룹에서 수정한 뒤 다시 시도"],
            )
        ],
        error_states=[
            ErrorState(
                trigger=intake.get("problem", "입력값을 확인할 수 없음"),
                user_message="입력 내용을 확인한 뒤 다시 시도하세요.",
                recovery="오류가 표시된 입력 또는 그룹을 수정하고 저장을 다시 시도한다.",
            )
        ],
    )
