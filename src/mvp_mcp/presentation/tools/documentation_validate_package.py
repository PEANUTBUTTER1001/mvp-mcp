"""Run 전용 candidate package의 결정적 검증 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_package_usecase import ValidateCandidatePackageUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_validate_package_tool(
    mcp: FastMCP, use_case: ValidateCandidatePackageUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_validate_package(
        run_id: str,
        run_version: int,
        candidate_revision: str,
    ) -> str:
        """서버 발급 candidate root만 검사하고, 성공 revision을 Run에 결속한다."""

        return use_case(run_id, run_version, candidate_revision).model_dump_json(indent=2)
