"""기본 단일 웹 Wizard 설문 흐름 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mvp_mcp.data.spec.spec_repository_impl import InMemorySpecRepository
from mvp_mcp.data.spec.survey_session_repository_impl import InMemorySurveySessionRepository
from mvp_mcp.data.spec.template_repository_impl import InMemoryTemplateRepository
from mvp_mcp.domain.spec.model import ProjectType, WebSurveyAnswer
from mvp_mcp.domain.spec.survey import SurveySession
from mvp_mcp.domain.spec.usecase import (
    FinalizeSpecUseCase,
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


def test_survey_submission_can_scope_and_finalize_without_more_questions() -> None:
    specs = InMemorySpecRepository()
    templates = InMemoryTemplateRepository()
    draft, survey = SubmitWebSurveyUseCase(
        templates, specs, _FixedClock(), _SurveyForm(_app_survey())
    )("초기 요청", "C:/project")
    assert draft.id is not None

    scoped = ScopeMvpUseCase(specs, templates)(draft.id, survey.requested_features)
    final = FinalizeSpecUseCase(specs, templates)(draft.id)

    assert scoped.status == "scoped"
    assert "문제/불편: 기록이 흩어져 비교하기 어렵다." in final.context
    assert "식당 등록" in final.context


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


def test_survey_page_uses_choice_buttons_and_six_document_copy() -> None:
    page = _render_page("식당 평가 앱", "test-token")

    assert "select.multiple ? 'checkbox' : 'radio'" in _CHOICE_ENHANCEMENT
    assert "MVP 범위와 6개 실행 계약 문서를 생성합니다." in page
    assert "6개 실행 계약 문서를 생성하고 있습니다." in page
    assert 'id="custom-tech-stack"' in page
    assert "updateCustomTechStack" in _CHOICE_ENHANCEMENT


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
