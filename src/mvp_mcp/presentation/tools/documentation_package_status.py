"""candidate와 실제 `.mvpmcp` 관리 manifest의 읽기 전용 상태 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_package_usecase import GetCandidatePackageStatusUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_package_status_tool(
    mcp: FastMCP, use_case: GetCandidatePackageStatusUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_package_status(run_id: str) -> str:
        """candidate revision, preview binding, 충돌, manifest와 다음 복구 동작을 조회한다."""

        return use_case(run_id).model_dump_json(indent=2)
