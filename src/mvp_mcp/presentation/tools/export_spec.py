"""export_spec Tool 어댑터 (얇은 어댑터)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.model import ExportSpecRequest
from mvp_mcp.domain.spec.usecase import ExportSpecUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_export_spec_tool(mcp: FastMCP, use_case: ExportSpecUseCase) -> None:
    """완성된 기획서·실행 명세서를 Markdown 파일로 저장하는 Tool을 등록한다."""

    @mcp.tool()
    @safe_tool
    def export_spec(
        spec_id: str,
        proposal_markdown: str,
        plan_markdown: str,
        summary_items: list[str] | None = None,
    ) -> str:
        """최종화된 명세의 기획서와 실행 명세서를 Markdown 파일로 저장한다."""
        result = use_case(
            ExportSpecRequest(
                spec_id=spec_id,
                proposal_markdown=proposal_markdown,
                plan_markdown=plan_markdown,
                summary_items=summary_items or [],
            )
        )
        proposal_path = result.proposal_path.replace("\\", "/")
        plan_path = result.plan_path.replace("\\", "/")
        summary = ""
        if summary_items:
            summary = "\n\n포함 내용:\n" + "\n".join(f"- {item}" for item in summary_items)
        return (
            "기획서와 구현서를 만들었습니다.\n\n"
            f"- [기획서]({proposal_path})\n"
            f"- [구현서]({plan_path})"
            f"{summary}"
        )
