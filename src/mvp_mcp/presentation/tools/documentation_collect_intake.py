"""통합 웹 Wizard 수집 Tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase, SubmitWebSurveyUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_collect_intake_tool(
    mcp: FastMCP,
    submit: SubmitWebSurveyUseCase,
    scope: ScopeMvpUseCase,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_collect_intake(user_request: str, project_root: str) -> str:
        """Wizard 제출까지 기다린다. 반환 즉시 같은 턴에서 next_action을 계속 실행한다."""
        draft, survey = submit(user_request, project_root)
        assert draft.id is not None
        scoped = scope(draft.id, survey.requested_features)
        return json.dumps(
            {
                "submission_status": "submitted",
                "continue_immediately": True,
                "user_message_required": False,
                "spec_id": scoped.id,
                "profile": scoped.documentation.profile.value,
                "prototype_preview": scoped.documentation.prototype_preview.value,
                "recommended_decisions": [
                    item.model_dump(mode="json") for item in scoped.recommended_decisions
                ],
                "next_action": "documentation_register_requirements",
            },
            ensure_ascii=False,
        )
