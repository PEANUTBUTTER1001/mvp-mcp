"""적응형 Wizard Run 상태의 영속 Port."""

from __future__ import annotations

from typing import Protocol

from .adaptive_wizard_model import AdaptiveWizardRun


class AdaptiveWizardRunRepository(Protocol):
    """요청 멱등성과 optimistic version을 보장하는 Run 저장소."""

    def create_or_get(self, run: AdaptiveWizardRun) -> tuple[AdaptiveWizardRun, bool]:
        """같은 request_key면 기존 Run, 아니면 새 Run과 생성 여부를 반환한다."""
        ...

    def find_by_id(self, run_id: str) -> AdaptiveWizardRun | None:
        """불투명 Run ID로 현재 snapshot을 조회한다."""
        ...

    def save(self, run: AdaptiveWizardRun, expected_version: int) -> AdaptiveWizardRun:
        """직전 version과 일치할 때만 다음 version을 저장한다."""
        ...
