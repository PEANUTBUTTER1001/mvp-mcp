"""가이드 기반 문서 품질 게이트 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.documentation_usecase import ValidateDocumentationUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_validate_tool(
    mcp: FastMCP, use_case: ValidateDocumentationUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
    )
    @safe_tool
    def documentation_validate(spec_id: str) -> str:
        """문서 프로파일·추적성·단계 게이트를 검사하고 JSON 결과를 반환한다."""
        return use_case(spec_id).model_dump_json(indent=2)
