"""Run-scoped 후보 TASK·TEST 전달 계약 갱신 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_lifecycle_usecase import UpdateCandidateDeliveryUseCase
from mvp_mcp.domain.spec.model import DeliveryTestCase, ImplementationTask
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_update_candidate_delivery_tool(
    mcp: FastMCP, use_case: UpdateCandidateDeliveryUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_update_candidate_delivery(
        run_id: str,
        expected_run_version: int,
        tasks: list[ImplementationTask],
        tests: list[DeliveryTestCase],
    ) -> str:
        """Run 소유 TASK·TEST 계약을 갱신하고 검증·릴리스 후보 기록을 재검토 상태로 전환한다."""

        return use_case(run_id, expected_run_version, tasks, tests).model_dump_json(indent=2)
