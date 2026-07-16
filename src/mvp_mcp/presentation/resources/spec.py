"""MVP 명세 MCP Resource 어댑터 (얇은 어댑터).

읽기 전용 데이터를 URI 로 노출한다. 비즈니스 로직 없이 UseCase 로 위임하고 JSON
문자열로 직렬화한다.

- ``spec://project-types``      유형 목록 + display_name + 판별 힌트
- ``spec://templates/{type}``   해당 유형 DomainTemplate 직렬화
- ``spec://drafts/{spec_id}``   초안 현재 상태
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.model import DomainTemplate, ProjectType, SpecDraft
from mvp_mcp.domain.spec.query import (
    GetDraftUseCase,
    GetTemplateUseCase,
    ListProjectTypesUseCase,
)


def _dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def register_resources(
    mcp: FastMCP,
    list_types_use_case: ListProjectTypesUseCase,
    get_template_use_case: GetTemplateUseCase,
    get_draft_use_case: GetDraftUseCase,
) -> None:
    """spec Resource(유형 목록/템플릿/초안)를 등록한다."""

    @mcp.resource("spec://project-types")
    def project_types_resource() -> str:
        """지원 유형 목록과 각 유형의 판별 힌트를 JSON 으로 반환한다."""
        templates = list_types_use_case()
        payload = [
            {
                "type": t.type.value,
                "display_name": t.display_name,
                "core_features": t.core_features,
            }
            for t in templates
        ]
        return _dumps(payload)

    @mcp.resource("spec://templates/{type}")
    def template_resource(type: str) -> str:
        """유형 하나의 템플릿을 JSON 으로 반환한다. 없으면 오류 객체."""
        try:
            project_type = ProjectType(type)
        except ValueError:
            return _dumps({"error": f"지원하지 않는 유형: {type}"})
        template = get_template_use_case(project_type)
        if template is None:
            return _dumps({})
        return _dumps(_template_to_dict(template))

    @mcp.resource("spec://drafts/{spec_id}")
    def draft_resource(spec_id: str) -> str:
        """초안 현재 상태를 JSON 으로 반환한다. 없으면 ``{}``."""
        draft = get_draft_use_case(spec_id)
        if draft is None:
            return _dumps({})
        return _dumps(_draft_to_dict(draft))


def _template_to_dict(template: DomainTemplate) -> dict[str, object]:
    return {
        "type": template.type.value,
        "display_name": template.display_name,
        "core_features": template.core_features,
        "excluded_features": template.excluded_features,
        "default_stack": template.default_stack,
        "required_fields": template.required_fields,
    }


def _draft_to_dict(draft: SpecDraft) -> dict[str, object]:
    return {
        "id": draft.id,
        "project_type": draft.project_type.value,
        "user_request": draft.user_request,
        "answers": draft.answers,
        "features": draft.features,
        "deferred": draft.deferred,
        "tech_stack": draft.tech_stack,
        "status": draft.status,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }
