"""MVP 명세 쓰기 유스케이스.

세션 흐름(start → answer → scope → finalize)의 오케스트레이션만 담당한다. 모든 협력자는
생성자에서 인터페이스(Port)로 주입받으며 구현체는 알지 못한다. 실패 가능 단계는
``_run_stage`` 로 감싸 ``PipelineError(stage, reason, hint)`` 로 구조화한다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from mvp_mcp.core.exceptions import MvpError, PipelineError

from . import checklist
from .model import (
    DomainTemplate,
    FinalSpec,
    ProjectType,
    Question,
    SpecDraft,
    SpecRequest,
)
from .output_format import render_context
from .ports import Clock
from .repository import SpecRepository, TemplateRepository
from .templates_data import ETC_MAX_FEATURES, QUESTION_BANK, WEB_FRONTEND

_T = TypeVar("_T")


def _run_stage(stage: str, action: Callable[[], _T], hint: str) -> _T:
    """단계를 실행하고, 실패 시 단계 정보를 담은 ``PipelineError`` 로 재던진다."""
    try:
        return action()
    except PipelineError:
        raise  # 이미 구조화된 실패는 그대로 전파.
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
    """유형 템플릿을 적용해 명세 세션을 시작한다."""

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
        # known_info 중 required_fields 에 해당하는 것만 채택(추측 값 유입 차단).
        answers = {k: v for k, v in request.known_info.items() if k in template.required_fields}
        draft = SpecDraft(
            project_type=request.project_type,
            user_request=request.user_request,
            answers=answers,
            created_at=self._clock.now(),
        )
        new_id = _run_stage(
            "persist",
            lambda: self._specs.save(draft),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        saved = draft.model_copy(update={"id": new_id})
        return saved, _questions_for(template, saved.answers)


class AnswerQuestionUseCase:
    """질문 하나에 대한 답을 초안에 반영한다."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str, field: str, value: str) -> tuple[SpecDraft, list[Question]]:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, spec_id),
            "start_spec 로 세션을 먼저 시작하세요.",
        )
        template = _require_template(self._templates, draft.project_type)
        if field not in template.required_fields:
            raise PipelineError(
                "validate",
                f"이 유형에 없는 필드입니다: {field}",
                f"필수 필드: {', '.join(template.required_fields)}",
            )
        updated_answers = {**draft.answers, field: value}
        updated = draft.model_copy(update={"answers": updated_answers})
        _run_stage(
            "persist",
            lambda: self._specs.save(updated),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        return updated, _questions_for(template, updated.answers)


class ScopeMvpUseCase:
    """⑥ 요청 기능을 MVP 범위로 판정한다(포함/컷+사유)."""

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
        # 기본 포함 = 템플릿 코어 기능. 요청 중 코어에 있는 것은 이미 포함.
        features = list(template.core_features)
        deferred: list[str] = []
        for feature in requested:
            if feature in template.core_features:
                continue  # 이미 포함.
            if feature in template.excluded_features:
                deferred.append(f"{feature} — MVP 범위 밖(핵심 이후 확장)")
            else:
                deferred.append(f"{feature} — MVP 이후 검토")
        return features, deferred

    @staticmethod
    def _scope_etc(requested: list[str]) -> tuple[list[str], list[str]]:
        # ETC: 템플릿이 없으므로 요청 기능 중 최대 N개만 승인, 초과분은 컷.
        features = requested[:ETC_MAX_FEATURES]
        deferred = [
            f"{feature} — MVP 범위 초과(최대 {ETC_MAX_FEATURES}개)"
            for feature in requested[ETC_MAX_FEATURES:]
        ]
        return features, deferred


class FinalizeSpecUseCase:
    """⑨ 품질 검증 후 최종 컨텍스트를 렌더링한다."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str) -> FinalSpec:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, spec_id),
            "start_spec 로 세션을 먼저 시작하세요.",
        )
        template = _require_template(self._templates, draft.project_type)

        issues = checklist.validate(draft, template)
        if issues:
            raise PipelineError(
                "checklist",
                "; ".join(issues),
                "미통과 항목을 해결한 뒤 다시 finalize_spec 을 호출하세요.",
            )

        tech_stack = self._resolve_stack(draft, template)
        finalized = draft.model_copy(update={"tech_stack": tech_stack, "status": "finalized"})
        _run_stage(
            "persist",
            lambda: self._specs.save(finalized),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        context = render_context(
            finalized,
            template.display_name,
            template.output_sections,
            template.output_guide,
        )
        return FinalSpec(draft=finalized, context=context)

    @staticmethod
    def _resolve_stack(draft: SpecDraft, template: DomainTemplate) -> dict[str, str]:
        # 사용자가 "직접 지정"을 택하면 서버는 스택을 추측하지 않는다(빈 dict → 컨텍스트
        # 에서 "사용자 지정" 지시로 처리). §0 역할 분담: 스택 매핑은 클라이언트 LLM 의 몫.
        if draft.answers.get("tech_stack") == "직접 지정":
            return {}
        stack = dict(template.default_stack)
        # platform 답변이 "웹" 이면 frontend 를 웹 프레임워크로 치환.
        if draft.answers.get("platform") == "웹":
            stack["frontend"] = WEB_FRONTEND
        return stack
