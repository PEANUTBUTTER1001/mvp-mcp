"""MVP 명세 쓰기 유스케이스.

세션 흐름(start → answer → scope → finalize)의 오케스트레이션만 담당한다. 모든 협력자는
생성자에서 인터페이스(Port)로 주입받으며 구현체는 알지 못한다. 실패 가능 단계는
``_run_stage`` 로 감싸 ``PipelineError(stage, reason, hint)`` 로 구조화한다.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from secrets import token_urlsafe
from typing import TypeVar

from mvp_mcp.core.exceptions import MvpError, PipelineError

from . import checklist
from .delivery_quality import validate_bundle
from .model import (
    BundleValidationResult,
    DeliveryTestCase,
    DesignContract,
    DomainTemplate,
    ExportedDocuments,
    ExportedMvpBundle,
    ExportSpecRequest,
    FinalSpec,
    ImplementationTask,
    MvpBundleRequest,
    Priority,
    ProjectType,
    Question,
    Requirement,
    RequirementInput,
    SpecDraft,
    SpecRequest,
    VerificationEvidence,
    VerificationStatus,
    WebQuestionAnswer,
    WebSurveyAnswer,
)
from .output_format import render_bundle_context, render_context
from .ports import (
    Clock,
    DocumentExporter,
    MvpBundleExporter,
    SurveySessionRepository,
    WebQuestionForm,
    WebSurveyForm,
    WebSurveySessionForm,
)
from .repository import SpecRepository, TemplateRepository
from .survey import SurveySession
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


class AskWebQuestionUseCase:
    """초안 생성 전 discovery 단계에도 재사용하는 단일 웹 질문 호출."""

    def __init__(self, question_form: WebQuestionForm) -> None:
        self._form = question_form

    def __call__(self, question: Question) -> WebQuestionAnswer:
        answer = _run_stage(
            "web_question",
            lambda: self._form.ask(question),
            "로컬 브라우저가 열렸는지와 질문 화면의 응답을 확인하세요.",
        )
        AskNextWebQuestionUseCase._validate_answer(question, answer)
        return answer


class SubmitWebSurveyUseCase:
    """단일 웹 설문을 받고 유형별 필수 답변을 한 번에 초안으로 만든다."""

    def __init__(
        self,
        template_repo: TemplateRepository,
        spec_repo: SpecRepository,
        clock: Clock,
        survey_form: WebSurveyForm,
    ) -> None:
        self._templates = template_repo
        self._specs = spec_repo
        self._clock = clock
        self._form = survey_form

    def __call__(self, user_request: str, project_root: str) -> tuple[SpecDraft, WebSurveyAnswer]:
        survey = _run_stage(
            "web_survey",
            lambda: self._form.ask(user_request),
            "로컬 브라우저에 열린 설문을 작성하고 제출하세요.",
        )
        template = _require_template(self._templates, survey.project_type)
        required_answers = survey.template_answers()
        missing = [field for field in template.required_fields if not required_answers.get(field)]
        if missing:
            raise PipelineError(
                "validate",
                f"유형별 필수 답변이 비어 있습니다: {', '.join(missing)}",
                "설문의 필수 항목을 모두 작성하세요.",
            )
        draft = SpecDraft(
            project_type=survey.project_type,
            user_request=survey.user_request,
            project_root=project_root,
            answers=required_answers,
            intake={
                "problem": survey.problem,
                "goal": survey.goal,
                "constraints": survey.constraints,
                "reference": survey.reference,
                "target_users": survey.target_users,
                "core_workflows": survey.core_workflows,
                "data_and_rules": survey.data_and_rules,
                "required_screens": survey.required_screens,
                "failure_behavior": survey.failure_behavior,
                "success_metrics": survey.success_metrics,
                "open_decisions": survey.open_decisions,
            },
            created_at=self._clock.now(),
        )
        new_id = _run_stage(
            "persist",
            lambda: self._specs.save(draft),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        return draft.model_copy(update={"id": new_id}), survey


class BeginWebSurveyUseCase:
    """브라우저 입력을 기다리지 않고 30분 유효 Wizard 세션을 시작한다."""

    def __init__(
        self,
        sessions: SurveySessionRepository,
        form: WebSurveySessionForm,
        clock: Clock,
        timeout_seconds: int,
    ) -> None:
        self._sessions = sessions
        self._form = form
        self._clock = clock
        self._timeout_seconds = timeout_seconds

    def __call__(self, user_request: str, project_root: str) -> tuple[SurveySession, str]:
        now = self._clock.now()
        session = SurveySession(
            id=token_urlsafe(24),
            user_request=user_request,
            project_root=project_root,
            expires_at=now + timedelta(seconds=self._timeout_seconds),
        )
        self._sessions.save(session)
        url = _run_stage(
            "web_survey",
            lambda: self._form.open(session.id, user_request),
            "로컬 브라우저가 열렸는지 확인하세요.",
        )
        return session, url


class SubmitWebSurveyAnswerUseCase:
    """Wizard POST가 검증한 답변을 제출 상태로 전환한다."""

    def __init__(self, sessions: SurveySessionRepository, clock: Clock) -> None:
        self._sessions = sessions
        self._clock = clock

    def __call__(self, session_id: str, answer: WebSurveyAnswer) -> SurveySession:
        session = _require_survey_session(self._sessions, session_id)
        session = _expire_survey_if_needed(session, self._clock)
        if session.status != "open":
            raise PipelineError(
                "web_survey", "제출할 수 없는 설문 세션입니다.", "새 Wizard를 시작하세요."
            )
        submitted = session.model_copy(update={"status": "submitted", "answer": answer})
        self._sessions.save(submitted)
        return submitted


class GetWebSurveyStatusUseCase:
    """제출 완료 여부를 부작용 없이 확인한다."""

    def __init__(self, sessions: SurveySessionRepository, clock: Clock) -> None:
        self._sessions = sessions
        self._clock = clock

    def __call__(self, session_id: str) -> SurveySession:
        return _expire_survey_if_needed(
            _require_survey_session(self._sessions, session_id), self._clock
        )


class ResumeWebSurveyUseCase:
    """제출된 설문을 한 번만 명세 초안으로 변환한다."""

    def __init__(
        self,
        sessions: SurveySessionRepository,
        template_repo: TemplateRepository,
        spec_repo: SpecRepository,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._templates = template_repo
        self._specs = spec_repo
        self._clock = clock

    def __call__(self, session_id: str) -> tuple[SpecDraft, WebSurveyAnswer]:
        session = _expire_survey_if_needed(
            _require_survey_session(self._sessions, session_id), self._clock
        )
        if session.status != "submitted" or session.answer is None:
            raise PipelineError(
                "web_survey",
                "아직 제출된 설문이 없습니다.",
                "Wizard를 제출한 뒤 다시 재개하세요.",
            )
        answer = session.answer
        template = _require_template(self._templates, answer.project_type)
        required_answers = answer.template_answers()
        missing = [field for field in template.required_fields if not required_answers.get(field)]
        if missing:
            raise PipelineError(
                "validate",
                f"유형별 필수 답변이 비어 있습니다: {', '.join(missing)}",
                "설문을 다시 확인하세요.",
            )
        draft = SpecDraft(
            project_type=answer.project_type,
            user_request=answer.user_request,
            project_root=session.project_root,
            answers=required_answers,
            intake={
                "problem": answer.problem,
                "goal": answer.goal,
                "constraints": answer.constraints,
                "reference": answer.reference,
            },
            created_at=self._clock.now(),
        )
        spec_id = _run_stage(
            "persist", lambda: self._specs.save(draft), "저장소 쓰기 권한을 확인하세요."
        )
        self._sessions.save(session.model_copy(update={"status": "consumed"}))
        return draft.model_copy(update={"id": spec_id}), answer


def _require_survey_session(sessions: SurveySessionRepository, session_id: str) -> SurveySession:
    session = sessions.find_by_id(session_id)
    if session is None:
        raise PipelineError(
            "web_survey", "설문 세션을 찾을 수 없습니다.", "새 Wizard를 시작하세요."
        )
    return session


def _expire_survey_if_needed(session: SurveySession, clock: Clock) -> SurveySession:
    if session.status == "open" and clock.now() >= session.expires_at:
        return session.model_copy(update={"status": "expired"})
    return session


class AskNextWebQuestionUseCase:
    """다음 미충족 질문을 로컬 웹 화면에서 받고 초안에 반영한다."""

    def __init__(
        self,
        spec_repo: SpecRepository,
        template_repo: TemplateRepository,
        question_form: WebQuestionForm,
    ) -> None:
        self._specs = spec_repo
        self._templates = template_repo
        self._form = question_form
        self._answer = AnswerQuestionUseCase(spec_repo, template_repo)

    def __call__(self, spec_id: str) -> tuple[SpecDraft, list[Question], WebQuestionAnswer]:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, spec_id),
            "start_spec 로 세션을 먼저 시작하세요.",
        )
        template = _require_template(self._templates, draft.project_type)
        remaining = _questions_for(template, draft.answers)
        if not remaining:
            raise PipelineError(
                "validate",
                "웹 화면으로 물을 남은 질문이 없습니다.",
                "scope_mvp 를 호출해 MVP 범위를 확정하세요.",
            )
        question = remaining[0]
        answer = _run_stage(
            "web_question",
            lambda: self._form.ask(question),
            "로컬 브라우저가 열렸는지와 질문 화면의 응답을 확인하세요.",
        )
        self._validate_answer(question, answer)
        updated, next_questions = self._answer(spec_id, question.field, answer.value)
        return updated, next_questions, answer

    @staticmethod
    def _validate_answer(question: Question, answer: WebQuestionAnswer) -> None:
        if not question.options:
            return
        if answer.value in question.options:
            return
        if question.allows_other and answer.value.startswith("기타: "):
            return
        raise PipelineError(
            "validate",
            f"허용되지 않은 선택값입니다: {answer.value}",
            "제시된 선택지 또는 '기타' 상세 입력을 사용하세요.",
        )


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


class RegisterRequirementsUseCase:
    """서버가 요구사항 ID를 부여하고 P0 수용 기준을 강제한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str, values: list[RequirementInput]) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        requirements = [
            Requirement(id=f"REQ-{index:03d}", **value.model_dump())
            for index, value in enumerate(values, start=1)
        ]
        if not requirements:
            raise PipelineError(
                "validate", "요구사항이 비어 있습니다.", "P0 요구사항을 등록하세요."
            )
        incomplete_p0 = [
            item.title
            for item in requirements
            if item.priority is Priority.P0 and len(item.acceptance_criteria) < 2
        ]
        if incomplete_p0:
            raise PipelineError(
                "validate",
                f"P0 요구사항의 수용 기준이 부족합니다: {', '.join(incomplete_p0)}",
                "P0 요구사항마다 수용 기준을 2개 이상 등록하세요.",
            )
        updated = draft.model_copy(update={"requirements": requirements})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


class ConfirmScopeUseCase:
    """사용자 확인 전 설계·내보내기를 막는 명시적 게이트."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        if draft.status != "scoped" or not draft.requirements:
            raise PipelineError(
                "validate",
                "MVP 범위와 요구사항을 먼저 확정해야 합니다.",
                "scope_mvp와 요구사항 등록을 완료하세요.",
            )
        updated = draft.model_copy(update={"scope_confirmed": True, "status": "confirmed"})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


class RegisterDesignContractUseCase:
    """상세 설계 계약을 초안에 고정한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str, contract: DesignContract) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        if not draft.scope_confirmed:
            raise PipelineError(
                "validate",
                "범위를 확정한 뒤에만 상세 설계를 등록할 수 있습니다.",
                "confirm_scope를 먼저 호출하세요.",
            )
        updated = draft.model_copy(update={"design_contract": contract})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


class RegisterDeliveryContractUseCase:
    """작업·테스트가 등록된 요구사항만 참조하도록 검증한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(
        self, spec_id: str, tasks: list[ImplementationTask], tests: list[DeliveryTestCase]
    ) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        valid_ids = {item.id for item in draft.requirements}
        task_refs = [ref for item in tasks for ref in item.requirement_ids]
        test_refs = [ref for item in tests for ref in item.requirement_ids]
        refs = task_refs + test_refs
        if (
            not tasks
            or not tests
            or not refs
            or not set(refs) <= valid_ids
            or valid_ids - set(task_refs)
            or valid_ids - set(test_refs)
        ):
            raise PipelineError(
                "validate",
                "작업·테스트의 요구사항 연결이 올바르지 않습니다.",
                "REQ-ID 참조를 확인하세요.",
            )
        updated = draft.model_copy(update={"tasks": tasks, "test_cases": tests})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


class RecordVerificationUseCase:
    """실제 테스트 근거만 인수 보고서에 기록한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str, evidence: list[VerificationEvidence]) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        valid_ids = {item.id for item in draft.test_cases}
        if not evidence or any(item.test_id not in valid_ids for item in evidence):
            raise PipelineError(
                "validate", "검증 결과가 테스트 계약과 연결되지 않습니다.", "TEST-ID를 확인하세요."
            )
        updated = draft.model_copy(update={"verification": evidence})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


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


class ExportSpecUseCase:
    """최종화된 명세의 문서를 파일시스템에 내보낸다."""

    def __init__(self, spec_repo: SpecRepository, exporter: DocumentExporter) -> None:
        self._specs = spec_repo
        self._exporter = exporter

    def __call__(self, request: ExportSpecRequest) -> ExportedDocuments:
        draft = _run_stage(
            "load",
            lambda: _require_draft(self._specs, request.spec_id),
            "start_spec 로 세션을 먼저 시작하세요.",
        )
        if draft.status != "finalized":
            raise PipelineError(
                "validate",
                "최종화되지 않은 명세는 내보낼 수 없습니다.",
                "scope_mvp 뒤 finalize_spec 을 먼저 호출하세요.",
            )
        return _run_stage(
            "export",
            lambda: self._exporter.export(request),
            "출력 디렉터리의 쓰기 권한과 디스크 여유 공간을 확인하세요.",
        )


class ExportMvpBundleUseCase:
    """확정된 실행 계약을 활성 프로젝트의 mvpmcp 폴더에 저장한다."""

    def __init__(self, spec_repo: SpecRepository, exporter: MvpBundleExporter) -> None:
        self._specs = spec_repo
        self._exporter = exporter

    def __call__(self, request: MvpBundleRequest) -> ExportedMvpBundle:
        draft = _require_draft(self._specs, request.spec_id)
        if (
            not draft.project_root
            or not draft.scope_confirmed
            or not draft.tasks
            or not draft.test_cases
        ):
            raise PipelineError(
                "validate",
                "6문서 내보내기 조건이 충족되지 않았습니다.",
                "범위·작업·테스트 계약을 확인하세요.",
            )
        issues = validate_bundle(draft, request)
        if issues:
            raise PipelineError(
                "quality_gate",
                "; ".join(issues),
                "누락된 설계 계약·추적성·문서 섹션을 보완한 뒤 다시 내보내세요.",
            )
        verification = _render_verification_report(draft)
        return _run_stage(
            "export",
            lambda: self._exporter.export(draft.project_root, request, verification),
            "프로젝트 루트의 mvpmcp 폴더 쓰기 권한을 확인하세요.",
        )


class ValidateMvpBundleUseCase:
    """파일 저장 없이 6문서 품질 게이트 결과를 반환한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, request: MvpBundleRequest) -> BundleValidationResult:
        draft = _require_draft(self._specs, request.spec_id)
        issues = validate_bundle(draft, request)
        return BundleValidationResult(passed=not issues, issues=issues)


class GetMvpBundleContextUseCase:
    """LLM이 6문서를 상세하게 작성하도록 현재 계약 기반 컨텍스트를 제공한다."""

    def __init__(self, spec_repo: SpecRepository, template_repo: TemplateRepository) -> None:
        self._specs = spec_repo
        self._templates = template_repo

    def __call__(self, spec_id: str) -> str:
        draft = _require_draft(self._specs, spec_id)
        template = _require_template(self._templates, draft.project_type)
        if draft.design_contract is None:
            raise PipelineError(
                "validate",
                "상세 설계 계약이 없습니다.",
                "register_design_contract를 먼저 호출하세요.",
            )
        return render_bundle_context(draft, template.display_name)


def _render_verification_report(draft: SpecDraft) -> str:
    """증거가 없으면 NOT_RUN을 유지하는 검증 보고서를 렌더링한다."""
    rows = {item.test_id: item for item in draft.verification}
    lines = ["# MVP 검증 보고서", "", "| 테스트 | 상태 | 근거 |", "|---|---|---|"]
    for test in draft.test_cases:
        item = rows.get(test.id)
        status = item.status.value if item else VerificationStatus.NOT_RUN.value
        evidence = item.evidence if item else "구현·테스트 미실행"
        lines.append(f"| {test.id} | {status} | {evidence} |")
    return "\n".join(lines) + "\n"
