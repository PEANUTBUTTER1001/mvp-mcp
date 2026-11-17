"""루트 AGENTS.md에 구현 Tool 사용 규칙 블록을 미리보기·반영하는 Tool."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.root_agents_link import LinkRootAgentsUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_implementation_link_root_agents_tool(
    mcp: FastMCP, use_case: LinkRootAgentsUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
        )
    )
    @safe_tool
    def implementation_link_root_agents(
        run_id: str,
        mode: Literal["preview", "apply"] = "preview",
        expected_current_sha256: str | None = None,
    ) -> str:
        """프로젝트 루트 AGENTS.md에 mvp-mcp 관리 블록을 넣는다(사용자 동의 필수).

        먼저 mode='preview'로 블록과 current_sha256을 받아 사용자에게 보여 준다. 사용자가
        동의할 때만 mode='apply'와 그 해시를 보낸다. 사람이 쓴 내용은 바꾸지 않는다.
        """

        return use_case(run_id, mode, expected_current_sha256).model_dump_json(indent=2)
