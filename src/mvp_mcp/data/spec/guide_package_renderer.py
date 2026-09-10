"""Markdown·OpenAPI·HTML 렌더러를 하나의 패키지 Port로 조합한다."""

from __future__ import annotations

import hashlib
import json

from mvp_mcp.domain.spec.documentation_model import (
    PrototypePreview,
    RenderedDocumentationPackage,
)
from mvp_mcp.domain.spec.model import SpecDraft
from mvp_mcp.domain.spec.tier_policy import select_profile

from .guide_document_renderer import GuideDocumentRenderer
from .html_prototype_renderer import HtmlPrototypeRenderer
from .openapi_renderer import OpenApiRenderer


class GuidePackageRendererImpl:
    def __init__(
        self,
        markdown: GuideDocumentRenderer,
        openapi: OpenApiRenderer,
        prototype: HtmlPrototypeRenderer,
    ) -> None:
        self._markdown = markdown
        self._openapi = openapi
        self._prototype = prototype

    def render(self, draft: SpecDraft) -> RenderedDocumentationPackage:
        profile = select_profile(draft.documentation)
        files = self._markdown.render(draft, profile)
        if draft.documentation.http_api_mode.value != "없음":
            files["api/openapi.yaml"] = self._openapi.render(draft)
        source_hash: str | None = None
        if draft.documentation.prototype_preview is PrototypePreview.REQUIRED:
            source_hash = self._prototype_hash(draft)
            files["prototype/index.html"] = self._prototype.render(draft, source_hash)
        return RenderedDocumentationPackage(
            profile=profile,
            files=files,
            source_contract_sha256=source_hash,
        )

    @staticmethod
    def _prototype_hash(draft: SpecDraft) -> str:
        design = draft.design_contract
        assert design is not None
        snapshot = {
            "goal": draft.intake.get("goal", ""),
            "target_users": draft.intake.get("target_users", ""),
            "requirements": [
                item.model_dump(mode="json")
                for item in sorted(draft.requirements, key=lambda value: value.id)
            ],
            "flows": [item.model_dump(mode="json") for item in design.user_flows],
            "screens": [item.model_dump(mode="json") for item in design.screens],
            "interfaces": [item.model_dump(mode="json") for item in design.interfaces],
            "data_entities": [item.model_dump(mode="json") for item in design.data_entities],
            "rules": [item.model_dump(mode="json") for item in design.business_rules],
            "errors": [item.model_dump(mode="json") for item in design.error_states],
            "documentation": draft.documentation.model_dump(mode="json"),
            "architecture_decisions": design.type_sections,
        }
        canonical = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
