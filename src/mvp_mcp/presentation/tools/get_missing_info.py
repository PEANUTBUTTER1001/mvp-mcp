"""get_missing_info Tool 어댑터 (얇은 어댑터)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.query import GetMissingInfoUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_next_question


def register_get_missing_info_tool(mcp: FastMCP, use_case: GetMissingInfoUseCase) -> None:
    """미충족 정보 조회 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def get_missing_info(spec_id: str) -> str:
        """아직 미충족인 필수 정보의 질문을 재조회한다."""
        questions = use_case(spec_id)
        return format_next_question(questions)
