"""Run-scoped 후보 릴리스 기록 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_lifecycle_usecase import RecordCandidateReleaseUseCase
from mvp_mcp.domain.spec.model import ReleaseRecord
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_record_candidate_release_tool(
    mcp: FastMCP, use_case: RecordCandidateReleaseUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
    )
    @safe_tool
    def documentation_record_candidate_release(
        run_id: str,
        expected_run_version: int,
        record: ReleaseRecord,
        idempotency_key: str,
    ) -> str:
        """Run 소유 릴리스·롤백 기록을 append-only로 추가한다.

        RELEASED는 모든 TEST PASS가 필요하다.
        """

        return use_case(run_id, expected_run_version, record, idempotency_key).model_dump_json(
            indent=2
        )
