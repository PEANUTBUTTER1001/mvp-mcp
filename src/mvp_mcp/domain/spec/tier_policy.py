"""가이드 S/A/B 티어 활성화와 프로파일 선택 정책."""

from __future__ import annotations

from dataclasses import dataclass

from .documentation_model import DocumentationIntake, DocumentProfile


@dataclass(frozen=True)
class TierDecision:
    tier: str
    area: str
    active: bool
    reason: str


def select_profile(intake: DocumentationIntake) -> DocumentProfile:
    return intake.profile


def evaluate_tiers(intake: DocumentationIntake) -> tuple[TierDecision, ...]:
    return (
        TierDecision("S", "핵심 문서", True, "모든 일반 MVP에 적용"),
        TierDecision("A", "UI", bool(intake.ui_surfaces), "사용자 화면 선택 결과"),
        TierDecision(
            "A", "HTTP API", intake.http_api_mode.value != "없음", "HTTP API 제공·변경 여부"
        ),
        TierDecision("A", "저장소", intake.storage_need.value == "필요", "영속 저장소 여부"),
        TierDecision("A", "배포", intake.deployment_scope.value != "로컬 실험", "배포 범위"),
        TierDecision("B", "보안·개인정보", intake.security_active, "Wizard 위험 신호"),
        TierDecision("B", "데이터 마이그레이션", intake.migration_active, "기존 데이터 변경"),
        TierDecision(
            "B", "운영 복구", intake.recovery_need.value != "불필요", "복구 필요 또는 미정"
        ),
    )
