"""구조화 설계 계약 등록 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.model import DesignContract
from mvp_mcp.domain.spec.usecase import RegisterDesignContractUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_architecture_tool(
    mcp: FastMCP, use_case: RegisterDesignContractUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_register_architecture(spec_id: str, contract: DesignContract) -> str:
        """화면·흐름·데이터·인터페이스·규칙·오류와 ASR/ADR 상세를 등록한다."""
        draft = use_case(spec_id, contract)
        return f'{{"spec_id":"{draft.id}","next_action":"documentation_register_delivery"}}'
