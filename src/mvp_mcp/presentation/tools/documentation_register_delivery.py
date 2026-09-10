"""TASK·TEST 전달 계약 등록 Tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.model import DeliveryTestCase, ImplementationTask
from mvp_mcp.domain.spec.usecase import RegisterDeliveryContractUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_delivery_tool(
    mcp: FastMCP, use_case: RegisterDeliveryContractUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_register_delivery(
        spec_id: str,
        tasks: list[ImplementationTask],
        tests: list[DeliveryTestCase],
    ) -> str:
        """TASK와 TEST를 요구사항 ID에 연결하고 검증 가능한 전달 계약을 만든다."""
        draft = use_case(spec_id, tasks, tests)
        return json.dumps(
            {
                "spec_id": draft.id,
                "task_ids": [item.id for item in draft.tasks],
                "test_ids": [item.id for item in draft.test_cases],
                "next_action": "documentation_validate",
            },
            ensure_ascii=False,
        )
