"""요구사항 등록·범위 확정 Tool."""

from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.model import RequirementInput
from mvp_mcp.domain.spec.usecase import ConfirmScopeUseCase, RegisterRequirementsUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_requirements_tool(
    mcp: FastMCP,
    register: RegisterRequirementsUseCase,
    confirm: ConfirmScopeUseCase,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_register_requirements(
        spec_id: str,
        requirements: list[RequirementInput],
        mode: Literal["upsert", "replace"] = "upsert",
    ) -> str:
        """요구사항을 원자적으로 upsert/replace하고 후속 계약을 안전하게 무효화한다."""
        updated = register(spec_id, requirements, mode)
        confirmed = updated if updated.scope_confirmed else confirm(spec_id)
        return json.dumps(
            {
                "spec_id": confirmed.id,
                "requirement_ids": [item.id for item in updated.requirements],
                "revision": confirmed.revision,
                "downstream_contracts_invalidated": updated.scope_confirmed,
                "next_action": "documentation_register_architecture",
            },
            ensure_ascii=False,
        )
