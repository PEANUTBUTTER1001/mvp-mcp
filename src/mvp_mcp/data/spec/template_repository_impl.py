"""템플릿 리포지토리 구현체.

``templates_data.TEMPLATES`` (순수 데이터)를 읽어 ``TemplateRepository`` Port 를
구현한다. 유형 확충은 ``templates_data.py`` 에 항목만 추가하면 이 구현체가 자동으로
노출한다.
"""

from __future__ import annotations

from mvp_mcp.domain.spec.model import DomainTemplate, ProjectType
from mvp_mcp.domain.spec.templates_data import TEMPLATES


class InMemoryTemplateRepository:
    """정적 템플릿 데이터를 조회하는 리포지토리."""

    def get(self, project_type: ProjectType) -> DomainTemplate | None:
        return TEMPLATES.get(project_type)

    def list_all(self) -> list[DomainTemplate]:
        return list(TEMPLATES.values())
