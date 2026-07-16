"""명세 초안·템플릿 영속화 인터페이스.

구조적 타이핑(``Protocol``)으로 정의하여 Domain 이 특정 저장소 구현에 의존하지 않도록
한다. 구현체는 ``data`` 레이어가 담당하며, 인메모리를 SQLite 등으로 교체해도 도메인은
그대로다.
"""

from __future__ import annotations

from typing import Protocol

from .model import DomainTemplate, ProjectType, SpecDraft


class TemplateRepository(Protocol):
    """유형별 템플릿을 조회한다(읽기 전용)."""

    def get(self, project_type: ProjectType) -> DomainTemplate | None:
        """유형에 해당하는 템플릿을 반환한다. 없으면 ``None``."""
        ...

    def list_all(self) -> list[DomainTemplate]:
        """등록된 모든 템플릿을 반환한다."""
        ...


class SpecRepository(Protocol):
    """명세 초안을 저장/조회한다."""

    def save(self, draft: SpecDraft) -> str:
        """초안을 저장하고, id 가 없으면 새로 부여해 그 id 를 반환한다."""
        ...

    def find_by_id(self, spec_id: str) -> SpecDraft | None:
        """id 로 초안 단건을 조회한다. 없으면 ``None``."""
        ...
