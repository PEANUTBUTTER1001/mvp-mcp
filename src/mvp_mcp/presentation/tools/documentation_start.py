"""가이드 기반 문서 세션 시작 Tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.documentation_model import (
    DocumentationIntake,
    DocumentProfile,
    Prototype4Attestation,
)
from mvp_mcp.domain.spec.model import ProjectType, SpecRequest
from mvp_mcp.domain.spec.usecase import ScopeMvpUseCase, StartSpecUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_start_tool(
    mcp: FastMCP, use_case: StartSpecUseCase, scope: ScopeMvpUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    )
    @safe_tool
    def documentation_start(
        user_request: str,
        project_root: str,
        project_type: str = "etc",
        known_info: dict[str, str] | None = None,
        requested_profile: str = "MVP_6",
        prototype4_attestations: list[str] | None = None,
        requested_features: list[str] | None = None,
    ) -> str:
        """수동 문서 세션을 시작한다. 4문서는 명시 선택과 4개 확인 진술이 필요하다."""
        documentation = DocumentationIntake(
            requested_profile=DocumentProfile(requested_profile),
            prototype4_attestations=[
                Prototype4Attestation(item) for item in (prototype4_attestations or [])
            ],
        )
        draft, questions = use_case(
            SpecRequest(
                project_type=ProjectType.coerce(project_type),
                user_request=user_request,
                project_root=project_root,
                known_info=known_info or {},
                documentation=documentation,
            )
        )
        if questions:
            missing = [item.field for item in questions]
            return json.dumps(
                {
                    "spec_id": draft.id,
                    "profile": draft.documentation.profile.value,
                    "status": "collecting",
                    "next_action": "documentation_collect_intake",
                    "missing_fields": missing,
                    "remaining_questions": len(questions),
                },
                ensure_ascii=False,
            )
        scoped = scope(draft.id or "", requested_features or [user_request])
        return json.dumps(
            {
                "spec_id": scoped.id,
                "profile": scoped.documentation.profile.value,
                "status": "scoped",
                "next_action": "documentation_register_requirements",
                "remaining_questions": 0,
            },
            ensure_ascii=False,
        )
