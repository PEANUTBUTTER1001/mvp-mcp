"""MVP 명세 Resource용 읽기 전용 유스케이스."""

from __future__ import annotations

from .model import DomainTemplate, ProjectType, SpecDraft
from .repository import SpecRepository, TemplateRepository


class GetDraftUseCase:
    """id 로 초안 단건을 조회한다(Resource 노출용)."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str) -> SpecDraft | None:
        return self._specs.find_by_id(spec_id)


class ListProjectTypesUseCase:
    """지원하는 모든 프로젝트 유형 템플릿을 반환한다(Resource 노출용)."""

    def __init__(self, template_repo: TemplateRepository) -> None:
        self._templates = template_repo

    def __call__(self) -> list[DomainTemplate]:
        return self._templates.list_all()


class GetTemplateUseCase:
    """유형 하나의 템플릿을 조회한다(Resource 노출용)."""

    def __init__(self, template_repo: TemplateRepository) -> None:
        self._templates = template_repo

    def __call__(self, project_type: ProjectType) -> DomainTemplate | None:
        return self._templates.get(project_type)
