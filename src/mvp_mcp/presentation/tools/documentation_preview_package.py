"""검증된 candidate package preview와 조건부 safe auto apply Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_package_usecase import PreviewCandidatePackageUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_preview_package_tool(
    mcp: FastMCP, use_case: PreviewCandidatePackageUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_preview_package(
        run_id: str,
        run_version: int,
        candidate_revision: str,
    ) -> str:
        """candidate diff를 만들고, safe_auto_apply 시 충돌이 없을 때만 내부 반영한다."""

        return use_case(run_id, run_version, candidate_revision).model_dump_json(indent=2)
