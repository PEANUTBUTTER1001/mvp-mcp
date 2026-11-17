"""TASK 하나의 요구사항·수용 기준·TEST·파일 범위를 반환하는 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.implementation_usecase import GetImplementationTaskContextUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_implementation_task_context_tool(
    mcp: FastMCP, use_case: GetImplementationTaskContextUseCase
) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    @safe_tool
    def implementation_task_context(run_id: str, task_id: str) -> str:
        """지정한 TASK에 연결된 명세만 반환한다. bytes는 이번에 읽는 명세 크기다."""

        return use_case(run_id, task_id).model_dump_json(indent=2)
