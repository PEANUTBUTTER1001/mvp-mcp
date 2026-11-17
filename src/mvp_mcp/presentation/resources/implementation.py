"""구현 단계 추적성 Resource 어댑터."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.domain.spec.implementation_usecase import GetImplementationTraceUseCase


def register_implementation_resources(
    mcp: FastMCP, trace_use_case: GetImplementationTraceUseCase
) -> None:
    @mcp.resource("spec://runs/{run_id}/trace", mime_type="application/json")
    def implementation_trace_resource(run_id: str) -> str:
        """요구사항 → TASK → TEST → 최신 실행 상태 추적표와 PASS/FAIL/NOT_RUN 집계."""
        try:
            return trace_use_case(run_id).model_dump_json(indent=2)
        except PipelineError as exc:
            return json.dumps({"error": exc.reason, "hint": exc.hint}, ensure_ascii=False)
