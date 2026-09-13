"""Run-scoped 후보 설계 계약 갱신 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_lifecycle_usecase import (
    UpdateCandidateArchitectureUseCase,
)
from mvp_mcp.domain.spec.model import DesignContract
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_update_candidate_architecture_tool(
    mcp: FastMCP, use_case: UpdateCandidateArchitectureUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_update_candidate_architecture(
        run_id: str,
        expected_run_version: int,
        contract: DesignContract,
    ) -> str:
        """Run 소유 설계를 갱신하고 전달·검증·릴리스 후보 계약을 재검토 상태로 전환한다."""

        return use_case(run_id, expected_run_version, contract).model_dump_json(indent=2)
