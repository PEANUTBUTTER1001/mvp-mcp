"""비차단 단일 페이지 웹 Wizard Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import (
    BeginWebSurveyUseCase,
    GetWebSurveyStatusUseCase,
    ResumeWebSurveyUseCase,
)
from mvp_mcp.presentation._safe import safe_tool


def register_ask_web_survey_tool(
    mcp: FastMCP,
    begin: BeginWebSurveyUseCase,
    status: GetWebSurveyStatusUseCase,
    resume: ResumeWebSurveyUseCase,
) -> None:
    """Wizard 시작·상태·재개 Tool을 등록한다."""

    @mcp.tool()
    @safe_tool
    def ask_web_survey(user_request: str, project_root: str) -> str:
        """MVP Wizard를 즉시 열고 blocking 없이 설문 세션을 시작한다."""
        session, url = begin(user_request, project_root)
        return (
            f"웹 Wizard 시작됨: session_id={session.id}\n"
            f"유효 시간: {session.expires_at.isoformat()}\n"
            f"URL: {url}\n\n"
            "제출 결과는 서버에 보관됩니다. 클라이언트가 자동 재개를 지원하면 resume_web_survey를 "
            "호출하고, 지원하지 않으면 get_web_survey_status로 상태를 확인한 뒤 재개하세요."
        )

    @mcp.tool()
    @safe_tool
    def get_web_survey_status(session_id: str) -> str:
        """설문 제출·만료·소비 상태를 조회한다."""
        session = status(session_id)
        return f"설문 상태: {session.status}; 만료 시각: {session.expires_at.isoformat()}"

    @mcp.tool()
    @safe_tool
    def resume_web_survey(session_id: str) -> str:
        """제출된 설문을 초안으로 변환하고 이후 문서 생성 흐름을 시작한다."""
        draft, survey = resume(session_id)
        return (
            f"웹 설문 재개 완료 → spec_id={draft.id}\n"
            f"프로젝트 유형: {draft.project_type.value}\n"
            f"요청 기능: {', '.join(survey.requested_features)}\n\n"
            "이제 scope_mvp → register_requirements → confirm_scope → "
            "register_design_contract → register_delivery_contract → get_mvp_bundle_context → "
            "validate_mvp_bundle → export_mvp_bundle 순서로 진행하세요."
        )
