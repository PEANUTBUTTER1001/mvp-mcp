"""finalize_spec Tool 어댑터 (얇은 어댑터).

통과 시 최종 컨텍스트 전문을 반환한다. 품질 미통과 시 UseCase 가 던지는
``PipelineError(stage="checklist")`` 를 ``@safe_tool`` 이 안내 문구로 변환한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import FinalizeSpecUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_finalize_spec_tool(mcp: FastMCP, use_case: FinalizeSpecUseCase) -> None:
    """명세 최종화 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def finalize_spec(spec_id: str) -> str:
        """품질 검증을 통과하면 LLM 에게 전달할 최종 명세 컨텍스트를 반환한다."""
        result = use_case(spec_id)
        return result.context
