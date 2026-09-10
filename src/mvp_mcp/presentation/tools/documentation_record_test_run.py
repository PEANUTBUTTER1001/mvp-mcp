"""실제 테스트 실행 증거 기록 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.model import VerificationEvidence
from mvp_mcp.domain.spec.usecase import RecordVerificationUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_test_run_tool(mcp: FastMCP, use_case: RecordVerificationUseCase) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_record_test_run(spec_id: str, runs: list[VerificationEvidence]) -> str:
        """실행된 TEST 결과만 append하고 증거 없는 PASS를 거부한다."""
        draft = use_case(spec_id, runs)
        return f'{{"spec_id":"{draft.id}","recorded_runs":{len(runs)}}}'
