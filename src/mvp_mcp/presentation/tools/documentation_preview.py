"""가이드 문서 패키지 preview Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.documentation_usecase import PreviewDocumentationUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_preview_tool(
    mcp: FastMCP, use_case: PreviewDocumentationUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_preview(spec_id: str) -> str:
        """대상 저장소는 수정하지 않고 표준 문서·OpenAPI·선택적 HTML과 manifest를 렌더링한다."""
        return use_case(spec_id).model_dump_json(indent=2)
