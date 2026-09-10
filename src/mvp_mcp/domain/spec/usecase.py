"""MVP 명세 쓰기 유스케이스.

세션 흐름(start → answer → scope → finalize)의 오케스트레이션만 담당한다. 모든 협력자는
생성자에서 인터페이스(Port)로 주입받으며 구현체는 알지 못한다. 실패 가능 단계는
``_run_stage`` 로 감싸 ``PipelineError(stage, reason, hint)`` 로 구조화한다.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from secrets import token_urlsafe
from typing import Literal, TypeVar

from mvp_mcp.core.exceptions import MvpError, PipelineError

from .documentation_model import (
    AuthCapability,
    AuthMethod,
    OtherRisk,
    PaymentRisk,
    PersonalDataType,
    TernaryDecision,
)
from .model import (
    DeliveryTestCase,
    DesignContract,
    DomainTemplate,
    ImplementationTask,
    Priority,
    ProjectType,
    Question,
    RecommendedDecision,
    ReleaseRecord,
    Requirement,
    RequirementInput,
    RequirementKind,
    SpecDraft,
    SpecRequest,
    VerificationEvidence,
    VerificationStatus,
    WebQuestionAnswer,
    WebSurveyAnswer,
)
from .ports import (
    Clock,
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
        draft = _web_survey_draft(survey, project_root, template, self._clock)
        new_id = _run_stage(
            "persist",
            lambda: self._specs.save(draft),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        return draft.model_copy(update={"id": new_id}), survey


def _web_survey_draft(
    answer: WebSurveyAnswer,
    project_root: str,
    template: DomainTemplate,
    clock: Clock,
) -> SpecDraft:
    """Wizard 답변을 6문서 흐름에서 재사용할 초안으로 변환한다."""
    submitted_answers = answer.template_answers()
    answer, recommended = _resolve_recommended_survey_defaults(answer)
    detail_defaults = _recommended_detail_defaults(answer)
    for field, value in detail_defaults.items():
        if not getattr(answer, field):
            recommended.append(
                RecommendedDecision(
                    field=field,
                    value=value,
                    reason=(
                        "선택 입력이 비어 있어 프로젝트 유형과 요청 내용에 맞는 "
                        "보수적 기본값을 적용했다."
                    ),
                    confidence="medium",
                )
            )
    answer = answer.model_copy(
        update={field: getattr(answer, field) or value for field, value in detail_defaults.items()}
    )
    return SpecDraft(
        project_type=answer.project_type,
        user_request=answer.user_request,
        project_root=project_root,
        answers=submitted_answers,
        tech_stack=_resolve_web_survey_stack(answer, template),
        intake={
            "problem": answer.problem,
            "goal": answer.goal,
            "constraints": answer.constraints,
            "reference": answer.reference,
            "target_users": answer.target_users,
            "core_workflows": answer.core_workflows,
            "data_and_rules": answer.data_and_rules,
            "required_screens": answer.required_screens,
            "failure_behavior": answer.failure_behavior,
            "success_metrics": answer.success_metrics,
            "open_decisions": answer.open_decisions,
        },
        documentation=answer.documentation,
        recommended_decisions=recommended,
        created_at=clock.now(),
    )


def _resolve_recommended_survey_defaults(
    answer: WebSurveyAnswer,
) -> tuple[WebSurveyAnswer, list[RecommendedDecision]]:
    """되돌릴 수 있는 미정값을 보수적인 프로젝트별 기본값으로 확정한다."""
    documentation = answer.documentation
    request = answer.user_request.casefold()
    local = documentation.deployment_scope.value == "로컬 실험"
    file_work = any(keyword in request for keyword in ("이미지", "파일", "업로드", "dataset"))
    payment_work = any(keyword in request for keyword in ("결제", "구매", "주문", "payment"))
    updates: dict[str, object] = {}
    decisions: list[RecommendedDecision] = []

    def decide(
        field: str,
        value: str,
        reason: str,
        confidence: Literal["high", "medium", "low"] = "high",
    ) -> None:
        decisions.append(
            RecommendedDecision(
                field=field,
                value=value,
                reason=reason,
                confidence=confidence,
            )
        )

    if AuthCapability.UNDECIDED in documentation.auth_capabilities:
        capabilities = (
            [AuthCapability.NONE] if local else [AuthCapability.LOGIN, AuthCapability.SESSION]
        )
        updates["auth_capabilities"] = capabilities
        updates["auth_methods"] = [] if local else [AuthMethod.PASSWORD]
        decide(
            "auth_capabilities",
            ", ".join(item.value for item in capabilities),
            "로컬 실험은 인증 없음, 공유·배포 환경은 최소 로그인과 세션을 기본으로 한다.",
        )
    elif AuthMethod.UNDECIDED in documentation.auth_methods:
        updates["auth_methods"] = [AuthMethod.PASSWORD]
        decide(
            "auth_methods",
            AuthMethod.PASSWORD.value,
            "외부 인증 공급자 의존성이 없는 최소 로그인 방식을 기본으로 한다.",
        )

    if PersonalDataType.UNDECIDED in documentation.personal_data_types:
        personal = [PersonalDataType.USER_CONTENT] if file_work else [PersonalDataType.NONE]
        updates["personal_data_types"] = personal
        decide(
            "personal_data_types",
            ", ".join(item.value for item in personal),
            "파일·이미지 입력은 사용자 콘텐츠로 보수적으로 분류한다.",
            "medium",
        )

    if documentation.payment_risk is PaymentRisk.UNDECIDED:
        payment = PaymentRisk.PRESENT if payment_work else PaymentRisk.ABSENT
        updates["payment_risk"] = payment
        decide(
            "payment_risk",
            payment.value,
            "요청에 결제·주문 신호가 있을 때만 고가치 자산 위험을 활성화한다.",
            "medium",
        )

    if OtherRisk.UNDECIDED in documentation.other_risks:
        risks: list[OtherRisk] = []
        if file_work:
            risks.extend([OtherRisk.FILE_UPLOAD, OtherRisk.EXTERNAL_INPUT])
        if documentation.http_api_mode.value != "없음":
            risks.append(OtherRisk.PUBLIC_API)
        risks = list(dict.fromkeys(risks)) or [OtherRisk.NONE]
        updates["other_risks"] = risks
        decide(
            "other_risks",
            ", ".join(item.value for item in risks),
            "파일 입력과 HTTP 경계를 기준으로 적용 가능한 위험을 보수적으로 활성화한다.",
            "medium",
        )

    if documentation.recovery_need is TernaryDecision.UNDECIDED:
        recovery = (
            TernaryDecision.REQUIRED
            if documentation.storage_need.value == "필요" or not local
            else TernaryDecision.NOT_REQUIRED
        )
        updates["recovery_need"] = recovery
        decide(
            "recovery_need",
            recovery.value,
            "영속 저장 또는 공유·운영 배포에는 백업·롤백 계획이 필요하다.",
        )

    if updates:
        documentation = documentation.model_copy(update=updates)
        answer = answer.model_copy(update={"documentation": documentation})
    return answer, decisions


def _recommended_detail_defaults(answer: WebSurveyAnswer) -> dict[str, str]:
    """선택 상세 입력을 문서화 가능한 최소 권장값으로 채운다."""
    project = {
        ProjectType.ML_PROJECT: "데이터·모델 실험 담당자",
        ProjectType.DATA_PIPELINE: "데이터 처리 담당자",
        ProjectType.MCP_SERVER: "MCP 도구 사용자와 유지보수 Agent",
    }.get(answer.project_type, "핵심 기능을 직접 사용하는 사용자")
    workflow = " → ".join(answer.requested_features)
    return {
        "constraints": "명시된 추가 제약 없음. MVP 범위와 안전한 기본 설정을 우선한다.",
        "target_users": project,
        "core_workflows": workflow,
        "data_and_rules": "사용자 입력을 검증하고 원본을 보존하며 변경 이력을 추적한다.",
        "required_screens": "핵심 흐름, 빈 상태, 진행 상태, 오류·복구 상태를 제공한다.",
        "failure_behavior": "입력을 보존하고 실패 원인과 안전한 재시도 방법을 표시한다.",
        "success_metrics": "대표 데이터로 핵심 흐름을 중단 없이 완료하고 결과를 재현할 수 있다.",
    }


def _resolve_web_survey_stack(answer: WebSurveyAnswer, template: DomainTemplate) -> dict[str, str]:
    """선택 또는 직접 입력한 스택을 문서용 구조화 값으로 만든다."""
    if answer.tech_stack == "직접 지정":
        return {"사용자 지정": answer.custom_tech_stack}
    stack = dict(template.default_stack)
    if answer.platform == "웹":
        stack["frontend"] = WEB_FRONTEND
    return stack


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
        draft = _web_survey_draft(answer, session.project_root, template, self._clock)
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
    """요구사항을 원자적으로 등록·개정하고 안정적인 ID를 유지한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(
        self,
        spec_id: str,
        values: list[RequirementInput],
        mode: Literal["upsert", "replace"] = "upsert",
    ) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        if draft.status not in {"scoped", "confirmed"}:
            raise PipelineError(
                "validate",
                "MVP 범위를 먼저 확정해야 합니다.",
                "documentation_collect_intake를 완료한 뒤 요구사항을 등록하세요.",
            )
        if not values:
            raise PipelineError(
                "validate", "요구사항이 비어 있습니다.", "P0 요구사항을 등록하세요."
            )
        incomplete_p0 = [
            item.title
            for item in values
            if item.priority is Priority.P0 and len(item.acceptance_criteria) < 2
        ]
        if incomplete_p0:
            raise PipelineError(
                "validate",
                f"P0 요구사항의 수용 기준이 부족합니다: {', '.join(incomplete_p0)}",
                "P0 요구사항마다 수용 기준을 2개 이상 등록하세요.",
            )
        existing_by_key = {(item.kind, item.title.casefold()): item for item in draft.requirements}
        counters = self._requirement_counters(draft.requirements)
        incoming: list[Requirement] = []
        for value in values:
            existing = existing_by_key.get((value.kind, value.title.casefold()))
            if existing is not None:
                incoming.append(Requirement(id=existing.id, **value.model_dump()))
                continue
            prefix = value.kind.value
            counters[value.kind] += 1
            incoming.append(
                Requirement(id=f"{prefix}-{counters[value.kind]:03d}", **value.model_dump())
            )

        requirements = incoming
        if mode == "upsert":
            incoming_keys = {(item.kind, item.title.casefold()) for item in incoming}
            requirements = [
                item
                for item in draft.requirements
                if (item.kind, item.title.casefold()) not in incoming_keys
            ] + incoming

        update: dict[str, object] = {"requirements": requirements}
        if draft.scope_confirmed:
            update.update(
                {
                    "design_contract": None,
                    "tasks": [],
                    "test_cases": [],
                    "verification": [],
                    "revision": draft.revision + 1,
                }
            )
        updated = draft.model_copy(update=update)
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated

    @staticmethod
    def _requirement_counters(requirements: list[Requirement]) -> dict[RequirementKind, int]:
        counters = {kind: 0 for kind in RequirementKind}
        for item in requirements:
            suffix = item.id.rsplit("-", 1)[-1]
            if suffix.isdigit():
                counters[item.kind] = max(counters[item.kind], int(suffix))
        return counters


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
        task_identifiers = [item.id for item in tasks]
        test_identifiers = [item.id for item in tests]
        if len(task_identifiers) != len(set(task_identifiers)):
            raise PipelineError(
                "validate", "중복된 TASK-ID가 있습니다.", "TASK-ID를 고유하게 지정하세요."
            )
        if len(test_identifiers) != len(set(test_identifiers)):
            raise PipelineError(
                "validate", "중복된 TEST-ID가 있습니다.", "TEST-ID를 고유하게 지정하세요."
            )
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
                "BIZ/FR/NFR/DATA/SEC ID 참조를 확인하세요.",
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
        existing = {(item.test_id, item.executed_at, item.status) for item in draft.verification}
        additions = [
            item
            for item in evidence
            if (item.test_id, item.executed_at, item.status) not in existing
        ]
        updated = draft.model_copy(update={"verification": [*draft.verification, *additions]})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated


class RecordReleaseUseCase:
    """실제 릴리스·롤백 결과를 기존 이력을 지우지 않고 추가한다."""

    def __init__(self, spec_repo: SpecRepository) -> None:
        self._specs = spec_repo

    def __call__(self, spec_id: str, record: ReleaseRecord) -> SpecDraft:
        draft = _require_draft(self._specs, spec_id)
        if any(item.id == record.id for item in draft.releases):
            raise PipelineError(
                "validate", "이미 사용한 REL ID입니다.", "새 날짜·일련번호의 REL ID를 사용하세요."
            )
        if record.status.value == "RELEASED":
            latest: dict[str, VerificationEvidence] = {}
            for item in draft.verification:
                latest[item.test_id] = item
            missing = [
                test.id
                for test in draft.test_cases
                if test.id not in latest or latest[test.id].status is not VerificationStatus.PASS
            ]
            if missing:
                raise PipelineError(
                    "release_gate",
                    f"PASS가 아닌 필수 테스트가 있습니다: {', '.join(missing)}",
                    "TEST_PLAN에 실제 PASS 증거를 기록한 뒤 릴리스를 등록하세요.",
                )
        updated = draft.model_copy(update={"releases": [*draft.releases, record]})
        _run_stage("persist", lambda: self._specs.save(updated), "저장소 쓰기 권한을 확인하세요.")
        return updated
