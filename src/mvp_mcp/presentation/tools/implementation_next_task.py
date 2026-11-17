"""구현 AI가 다음에 할 TASK와 필요한 명세만 받는 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.implementation_usecase import GetNextImplementationTaskUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_implementation_next_task_tool(
    mcp: FastMCP, use_case: GetNextImplementationTaskUseCase
) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    @safe_tool
    def implementation_next_task(run_id: str) -> str:
        """반영된 문서 패키지에서 선행 작업이 끝난 다음 TASK와 그 명세만 반환한다.

        연결 TEST가 모두 PASS면 완료로 본다. 남은 작업이 없으면 ALL_DONE, 진행할 수 없으면
        BLOCKED와 이유를 돌려준다. 문서 전체를 읽지 말고 이 결과로 구현하라.
        """

        return use_case(run_id).model_dump_json(indent=2)
