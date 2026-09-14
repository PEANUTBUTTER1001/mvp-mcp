"""Adaptive Wizard가 공유하는 명세 초안·MVP 범위 유스케이스."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from mvp_mcp.core.exceptions import MvpError, PipelineError

from .model import DomainTemplate, ProjectType, SpecDraft
from .repository import SpecRepository, TemplateRepository
from .templates_data import ETC_MAX_FEATURES

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
            "Adaptive Wizard로 생성된 spec_id인지 확인하세요.",
        )
    return draft


class ScopeMvpUseCase:
    """요청 기능을 MVP 범위로 판정한다(포함/컷+사유)."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str, requested: list[str]) -> SpecDraft:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, spec_id),
            "Adaptive Wizard로 생성된 spec_id인지 확인하세요.",
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
