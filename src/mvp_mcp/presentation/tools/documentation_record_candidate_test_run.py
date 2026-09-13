"""Run-scoped 후보 테스트 증거 기록 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_lifecycle_usecase import RecordCandidateTestRunUseCase
from mvp_mcp.domain.spec.model import VerificationEvidence
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_record_candidate_test_run_tool(
    mcp: FastMCP, use_case: RecordCandidateTestRunUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
    )
    @safe_tool
    def documentation_record_candidate_test_run(
        run_id: str,
        expected_run_version: int,
        runs: list[VerificationEvidence],
        idempotency_key: str,
    ) -> str:
        """Run 소유 TEST 증거를 append-only로 기록한다. 같은 idempotency_key 재시도는 안전하다."""

        return use_case(run_id, expected_run_version, runs, idempotency_key).model_dump_json(
            indent=2
        )
