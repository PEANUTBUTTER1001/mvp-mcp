"""scope_mvp Tool 어댑터 (얇은 어댑터)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_scope


def register_scope_mvp_tool(mcp: FastMCP, use_case: ScopeMvpUseCase) -> None:
    """MVP 범위 제한 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def scope_mvp(spec_id: str, requested_features: list[str] | None = None) -> str:
        """요청 기능을 MVP 범위로 판정한다(포함/컷+사유)."""
        draft = use_case(spec_id, requested_features or [])
        return format_scope(draft)
