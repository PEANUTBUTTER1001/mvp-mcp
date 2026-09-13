"""Adaptive Wizard가 공유하는 명세 초안·MVP 범위 유스케이스.

공개 MCP 수명주기는 Run-scoped candidate API가 소유한다. 이 모듈은 Adaptive
Wizard의 draft 생성에 필요한 ``ScopeMvpUseCase``와, 별도 정리 범위인 미등록
``start_spec`` 어댑터가 참조하는 시작 UseCase만 보존한다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from mvp_mcp.core.exceptions import MvpError, PipelineError

from .model import DomainTemplate, ProjectType, Question, SpecDraft, SpecRequest
from .ports import Clock
from .repository import SpecRepository, TemplateRepository
from .templates_data import ETC_MAX_FEATURES, QUESTION_BANK

_T = TypeVar("_T")


def _run_stage(stage: str, action: Callable[[], _T], hint: str) -> _T:
    """단계를 실행하고, 실패 시 단계 정보를 담은 ``PipelineError`` 로 재던진다."""

    try:
        return action()
    except PipelineError:
        raise
    except MvpError as exc:
        raise PipelineError(stage, str(exc), hint) from exc
    except Exception as exc:
        raise PipelineError(stage, f"{type(exc).__name__}: {exc}", hint) from exc


def _questions_for(template: DomainTemplate, answers: dict[str, str]) -> list[Question]:
    """미충족 필수 필드에 대한 질문만 반환한다(질문 최소화 원칙)."""

    return [
        QUESTION_BANK[field]
        for field in template.required_fields
        if field not in answers and field in QUESTION_BANK
    ]


def _require_template(
    template_repo: TemplateRepository, project_type: ProjectType
) -> DomainTemplate:
    template = template_repo.get(project_type)
    if template is None:
        raise PipelineError(
            "template",
            f"지원하지 않는 유형: {project_type.value}",
            "spec://project-types 리소스에서 지원 유형을 확인하세요.",
        )
    return template


def _require_draft(spec_repo: SpecRepository, spec_id: str) -> SpecDraft:
    draft = spec_repo.find_by_id(spec_id)
    if draft is None:
        raise PipelineError(
            "load",
            f"초안을 찾을 수 없습니다: {spec_id}",
            "start_spec 로 세션을 먼저 시작하세요.",
        )
    return draft


class StartSpecUseCase:
    """미등록 ``start_spec`` 어댑터의 기존 초안 생성 지원 구현."""

    def __init__(
        self,
        template_repo: TemplateRepository,
        spec_repo: SpecRepository,
        clock: Clock,
    ) -> None:
        self._templates = template_repo
        self._specs = spec_repo
        self._clock = clock

    def __call__(self, request: SpecRequest) -> tuple[SpecDraft, list[Question]]:
        template = _run_stage(
            "template",
            lambda: _require_template(self._templates, request.project_type),
            "지원 유형인지 확인하세요.",
        )
        answers = {
            key: value
            for key, value in request.known_info.items()
            if key in template.required_fields
        }
        draft = SpecDraft(
            project_type=request.project_type,
            user_request=request.user_request,
            project_root=request.project_root,
            answers=answers,
            created_at=self._clock.now(),
            documentation=request.documentation,
        )
        new_id = _run_stage(
            "persist",
            lambda: self._specs.save(draft),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        saved = draft.model_copy(update={"id": new_id})
        return saved, _questions_for(template, saved.answers)


class ScopeMvpUseCase:
    """요청 기능을 MVP 범위로 판정한다(포함/컷+사유)."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str, requested: list[str]) -> SpecDraft:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, spec_id),
            "start_spec 로 세션을 먼저 시작하세요.",
        )
        template = _require_template(self._templates, draft.project_type)

        if template.type is ProjectType.ETC:
            features, deferred = self._scope_etc(requested)
        else:
            features, deferred = self._scope_templated(template, requested)

        scoped = draft.model_copy(
            update={"features": features, "deferred": deferred, "status": "scoped"}
        )
        _run_stage(
            "persist",
            lambda: self._specs.save(scoped),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        return scoped

    @staticmethod
    def _scope_templated(
        template: DomainTemplate, requested: list[str]
    ) -> tuple[list[str], list[str]]:
        features = list(template.core_features)
        deferred: list[str] = []
        for feature in requested:
            if feature in template.core_features:
                continue
            if feature in template.excluded_features:
                deferred.append(f"{feature} — MVP 범위 밖(핵심 이후 확장)")
            else:
                deferred.append(f"{feature} — MVP 이후 검토")
        return features, deferred

    @staticmethod
    def _scope_etc(requested: list[str]) -> tuple[list[str], list[str]]:
        features = requested[:ETC_MAX_FEATURES]
        deferred = [
            f"{feature} — MVP 범위 초과(최대 {ETC_MAX_FEATURES}개)"
            for feature in requested[ETC_MAX_FEATURES:]
        ]
        return features, deferred
