"""기본 단일 웹 Wizard 설문 흐름 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.survey_session_repository_impl import InMemorySurveySessionRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.documentation_model import (
    AuthCapability,
    DocumentProfile,
    OtherRisk,
    PaymentRisk,
    PersonalDataType,
    PrototypePreview,
    TernaryDecision,
    UiSurface,
)
from mvp_mcp.domain.spec.model import ProjectType, WebSurveyAnswer
from mvp_mcp.domain.spec.survey import SurveySession
from mvp_mcp.domain.spec.usecase import (
    ResumeWebSurveyUseCase,
    ScopeMvpUseCase,
    SubmitWebSurveyAnswerUseCase,
    SubmitWebSurveyUseCase,
)
from mvp_mcp.presentation.web.local_survey_form import (
    _CHOICE_ENHANCEMENT,
    LocalWebSurveyForm,
    _render_page,
)


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1)


class _SurveyForm:
    def __init__(self, answer: WebSurveyAnswer) -> None:
        self.answer = answer
        self.requests: list[str] = []

    def ask(self, user_request: str) -> WebSurveyAnswer:
        self.requests.append(user_request)
        return self.answer


def _app_survey() -> WebSurveyAnswer:
    return WebSurveyAnswer(
        project_type=ProjectType.ETC,
        user_request="식당 체크리스트 평가 앱",
        problem="기록이 흩어져 비교하기 어렵다.",
        goal="방문 기록을 일관되게 관리한다.",
        purpose="개인 프로젝트",
        tech_stack="기본 스택 사용",
        platform="웹",
        auth_method="없음",
        realtime="불필요",
        requested_features=["식당 등록", "체크리스트 평가", "후기 작성"],
        constraints="2주 안에 완성",
    )


def test_submit_survey_creates_complete_draft_and_preserves_intake() -> None:
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    form = _SurveyForm(_app_survey())

    draft, survey = SubmitWebSurveyUseCase(templates, specs, _FixedClock(), form)(
        "초기 요청", "C:/project"
    )

    assert draft.id is not None
    assert draft.project_root == "C:/project"
    assert form.requests == ["초기 요청"]
    assert draft.answers == {
        "purpose": "개인 프로젝트",
        "tech_stack": "기본 스택 사용",
        "platform": "웹",
        "auth_method": "없음",
        "realtime": "불필요",
    }
    assert draft.intake["problem"] == survey.problem
    assert draft.intake["constraints"] == "2주 안에 완성"
    assert draft.tech_stack["frontend"] == "React (Next.js)"


def test_direct_tech_stack_is_required_and_preserved_in_draft() -> None:
    with pytest.raises(ValueError, match="직접 지정한 기술 스택"):
        WebSurveyAnswer(
            project_type=ProjectType.ETC,
            user_request="식당 체크리스트 평가 앱",
            problem="기록이 흩어져 비교하기 어렵다.",
            goal="방문 기록을 일관되게 관리한다.",
            purpose="개인 프로젝트",
            tech_stack="직접 지정",
            platform="웹",
            auth_method="없음",
            realtime="불필요",
            requested_features=["식당 등록"],
        )

    answer = _app_survey().model_copy(
        update={"tech_stack": "직접 지정", "custom_tech_stack": "SvelteKit, Go, SQLite"}
    )
    draft, _ = SubmitWebSurveyUseCase(
        InMemoryTemplateRepository(), InMemorySpecRepository(), _FixedClock(), _SurveyForm(answer)
    )("초기 요청", "C:/project")

    assert draft.tech_stack == {"사용자 지정": "SvelteKit, Go, SQLite"}


def test_survey_submission_can_scope_without_more_questions() -> None:
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    draft, survey = SubmitWebSurveyUseCase(
        templates, specs, _FixedClock(), _SurveyForm(_app_survey())
    )("초기 요청", "C:/project")
    assert draft.id is not None

    scoped = ScopeMvpUseCase(specs, templates)(draft.id, survey.requested_features)
    assert scoped.status == "scoped"
    assert scoped.intake["problem"] == "기록이 흩어져 비교하기 어렵다."
    assert "식당 등록" in scoped.features


def test_undecided_survey_values_use_conservative_recommended_defaults() -> None:
    answer = WebSurveyAnswer(
        project_type=ProjectType.ML_PROJECT,
        user_request="이미지 파일을 업로드해 분류 모델을 학습한다.",
        problem="도구가 분리되어 있다.",
        goal="하나의 파이프라인으로 통합한다.",
        purpose="개인 프로젝트",
        tech_stack="기본 스택 사용",
        requested_features=["이미지 업로드", "모델 학습"],
        data_source="CSV/파일",
        task_type="분류",
        deployment_target="배치 파이프라인",
        documentation={
            "auth_capabilities": ["계획 미정"],
            "personal_data_types": ["계획 미정"],
            "payment_risk": "계획 미정",
            "other_risks": ["계획 미정"],
            "recovery_need": "계획 미정",
        },
    )
    draft, _ = SubmitWebSurveyUseCase(
        InMemoryTemplateRepository(),
        InMemorySpecRepository(),
        _FixedClock(),
        _SurveyForm(answer),
    )("초기 요청", "C:/project")

    assert draft.documentation.auth_capabilities == [AuthCapability.NONE]
    assert draft.documentation.personal_data_types == [PersonalDataType.USER_CONTENT]
    assert draft.documentation.payment_risk is PaymentRisk.ABSENT
    assert draft.documentation.other_risks == [OtherRisk.FILE_UPLOAD, OtherRisk.EXTERNAL_INPUT]
    assert draft.documentation.recovery_need is TernaryDecision.NOT_REQUIRED
    assert not draft.documentation.has_pending_decision
    assert {item.field for item in draft.recommended_decisions} >= {
        "auth_capabilities",
        "personal_data_types",
        "payment_risk",
        "other_risks",
        "recovery_need",
        "target_users",
        "failure_behavior",
    }


def test_survey_requires_fields_for_selected_type() -> None:
    with pytest.raises(ValueError, match="유형별 필수"):
        WebSurveyAnswer(
            project_type=ProjectType.MCP_SERVER,
            user_request="MCP",
            problem="문제",
            goal="목표",
            purpose="개인 프로젝트",
            tech_stack="기본 스택 사용",
            requested_features=["도구"],
        )


def test_local_survey_maps_app_and_splits_features() -> None:
    answer = LocalWebSurveyForm._validate_submission(
        "초기 요청",
        {
            "project_type": "app",
            "user_request": "식당 평가 앱",
            "problem": "기록 문제",
            "goal": "관리",
            "purpose": "개인 프로젝트",
            "tech_stack": "기본 스택 사용",
            "platform": "웹",
            "auth_method": "없음",
            "realtime": "불필요",
            "requested_features": "식당 등록,\n후기 작성",
        },
    )

    assert answer.project_type is ProjectType.ETC
    assert answer.requested_features == ["식당 등록", "후기 작성"]


def test_local_survey_maps_governance_multiselect_and_prototype() -> None:
    answer = LocalWebSurveyForm._validate_submission(
        "이미지 라벨링 도구",
        {
            "project_type": "ml",
            "user_request": "이미지 라벨링 도구",
            "problem": "도구 분리",
            "goal": "학습 흐름 통합",
            "purpose": "회사 프로젝트",
            "tech_stack": "기본 스택 사용",
            "requested_features": "라벨링, 학습",
            "data_source": "CSV/파일",
            "task_type": "분류",
            "deployment_target": "배치 파이프라인",
            "change_type": "신규 개발",
            "deployment_scope": "내부 사용",
            "ui_surfaces": ["웹", "관리자 UI"],
            "http_api_mode": "신규 제공",
            "storage_need": "필요",
            "storage_types": ["DB", "파일"],
            "existing_data_change": "변경하지 않음",
            "auth_capabilities": ["로그인", "역할·권한"],
            "auth_methods": ["SSO"],
            "personal_data_types": ["계정 식별자", "사용자 콘텐츠"],
            "payment_risk": "없음",
            "other_risks": ["파일 업로드", "외부 입력"],
            "recovery_need": "필요",
            "prototype_preview": "필요",
        },
    )

    assert answer.documentation.ui_surfaces == [UiSurface.WEB, UiSurface.ADMIN]
    assert answer.documentation.profile is DocumentProfile.MVP_6_SECURITY
    assert answer.documentation.prototype_preview is PrototypePreview.REQUIRED
    assert answer.platform == "웹, 관리자 UI"


def test_survey_page_uses_choice_buttons_and_six_document_copy() -> None:
    page = _render_page("식당 평가 앱", "test-token")

    assert "select.multiple ? 'checkbox' : 'radio'" in _CHOICE_ENHANCEMENT
    assert "MVP 범위와 6개 실행 계약 문서를 생성합니다." in page
    assert "문서 계약을 검증하고 preview를 준비합니다." in page
    assert 'id="custom-tech-stack"' in page
    assert "updateCustomTechStack" in _CHOICE_ENHANCEMENT
    assert 'name="prototype_preview"' in page
    assert "HTML 프로토타입 보기" in page
    assert "new FormData(form),values={}" in page


def test_resume_survey_preserves_detailed_intake_fields() -> None:
    sessions = InMemorySurveySessionRepository()
    specs = InMemorySpecRepository()
    answer = _app_survey().model_copy(
        update={
            "target_users": "주말마다 식당을 기록하는 개인",
            "core_workflows": "등록 → 방문 기록 → 재방문 전 조회",
            "data_and_rules": "평점은 1~5점 정수",
            "required_screens": "목록, 상세, 빈 상태, 오류 상태",
            "failure_behavior": "입력을 유지하고 재시도",
            "success_metrics": "핵심 흐름을 한 세션에 완료",
            "open_decisions": "후기 없이 저장 가능 여부",
        }
    )
    sessions.save(
        SurveySession(
            id="session-1",
            user_request=answer.user_request,
            project_root="C:/project",
            expires_at=_FixedClock().now() + timedelta(minutes=30),
        )
    )
    SubmitWebSurveyAnswerUseCase(sessions, _FixedClock())("session-1", answer)

    draft, _ = ResumeWebSurveyUseCase(sessions, InMemoryTemplateRepository(), specs, _FixedClock())(
        "session-1"
    )

    assert draft.intake["target_users"] == "주말마다 식당을 기록하는 개인"
    assert draft.intake["open_decisions"] == "후기 없이 저장 가능 여부"
