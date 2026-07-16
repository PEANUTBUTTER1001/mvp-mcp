"""MVP 명세 읽기 전용 유스케이스.

단순 조회이므로 실패 구조화(``_run_stage``)는 쓰지 않는다. Resource 노출과 진행 상태
조회에 사용된다. 리포지토리 인터페이스(Port)에만 의존한다.
"""

from __future__ import annotations

from .intake import INTAKE_QUESTIONS
from .model import DomainTemplate, ProjectType, Question, SpecDraft
from .repository import SpecRepository, TemplateRepository
from .templates_data import QUESTION_BANK


class GetIntakeQuestionsUseCase:
    """의도 파악(discovery) 질문을 반환한다(선행 단계, 상태 불필요)."""

    def __call__(self) -> list[Question]:
        return list(INTAKE_QUESTIONS)


class GetMissingInfoUseCase:
    """초안에서 아직 미충족인 필수 필드의 질문을 반환한다."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str) -> list[Question]:
        draft = self._specs.find_by_id(spec_id)
        if draft is None:
            return []
        template = self._templates.get(draft.project_type)
        if template is None:
            return []
        return [
            QUESTION_BANK[field]
            for field in template.required_fields
            if field not in draft.answers and field in QUESTION_BANK
        ]


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
