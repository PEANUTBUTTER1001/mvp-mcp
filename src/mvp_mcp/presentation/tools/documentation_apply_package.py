"""manual_apply 정책의 candidate preview를 반영하는 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_package_usecase import ApplyCandidatePackageUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_apply_package_tool(
    mcp: FastMCP, use_case: ApplyCandidatePackageUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_apply_package(
        run_id: str,
        run_version: int,
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> str:
        """manual_apply Run의 hash-bound preview만 반영한다.

        다른 write_policy는 POLICY_DENIED를 반환한다.
        """

        return use_case(
            run_id,
            run_version,
            preview_id,
            manifest_sha256,
            approved_by,
            approval_note,
        ).model_dump_json(indent=2)
