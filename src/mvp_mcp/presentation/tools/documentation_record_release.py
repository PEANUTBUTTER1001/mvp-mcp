"""실제 릴리스·롤백 기록 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.model import ReleaseRecord
from mvp_mcp.domain.spec.usecase import RecordReleaseUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_release_tool(mcp: FastMCP, use_case: RecordReleaseUseCase) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_record_release(spec_id: str, record: ReleaseRecord) -> str:
        """필수 TEST PASS 이후 실제 REL 결과와 재현 증거를 append한다."""
        draft = use_case(spec_id, record)
        return f'{{"spec_id":"{draft.id}","release_id":"{record.id}"}}'
