"""제출 완료까지 기다리는 단일 페이지 웹 Wizard Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import SubmitWebSurveyUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_ask_web_survey_tool(
    mcp: FastMCP,
    submit: SubmitWebSurveyUseCase,
) -> None:
    """제출 완료까지 기다리는 기본 Wizard Tool을 등록한다."""

    @mcp.tool()
    @safe_tool
    def ask_web_survey(user_request: str, project_root: str) -> str:
        """MVP Wizard 제출을 기다려 같은 호출에서 명세 초안을 만든다."""
        draft, survey = submit(user_request, project_root)
        return (
            f"웹 Wizard 제출 완료 → spec_id={draft.id}\n"
            f"프로젝트 유형: {draft.project_type.value}\n"
            f"요청 기능: {', '.join(survey.requested_features)}\n\n"
            "별도 재개 호출 없이 바로 scope_mvp → register_requirements → confirm_scope → "
            "register_design_contract → register_delivery_contract → get_mvp_bundle_context → "
            "validate_mvp_bundle → export_mvp_bundle 순서로 진행하세요."
        )
