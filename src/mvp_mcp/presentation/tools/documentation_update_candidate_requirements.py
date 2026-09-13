"""Run-scoped 후보 요구사항 갱신 Tool."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_lifecycle_usecase import (
    UpdateCandidateRequirementsUseCase,
)
from mvp_mcp.domain.spec.model import RequirementInput
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_update_candidate_requirements_tool(
    mcp: FastMCP, use_case: UpdateCandidateRequirementsUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_update_candidate_requirements(
        run_id: str,
        expected_run_version: int,
        requirements: list[RequirementInput],
        mode: Literal["upsert", "replace"] = "upsert",
    ) -> str:
        """Run 소유 요구사항을 갱신하고 설계 이후 후보 계약을 재검토 상태로 전환한다."""

        return use_case(run_id, expected_run_version, requirements, mode).model_dump_json(indent=2)
