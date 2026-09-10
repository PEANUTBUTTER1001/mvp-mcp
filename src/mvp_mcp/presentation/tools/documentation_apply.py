"""승인된 preview를 `.mvpmcp/`에 적용하는 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.documentation_usecase import ApplyDocumentationUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_apply_tool(mcp: FastMCP, use_case: ApplyDocumentationUseCase) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False)
    )
    @safe_tool
    def documentation_apply(
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> str:
        """승인된 preview/hash만 적용하며 unmanaged 파일은 덮어쓰지 않는다."""
        return use_case(preview_id, manifest_sha256, approved_by, approval_note).model_dump_json(
            indent=2
        )
