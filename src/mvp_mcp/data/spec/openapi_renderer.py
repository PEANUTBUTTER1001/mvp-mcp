"""구조화된 HTTP 인터페이스에서 단일 OpenAPI SSOT를 렌더링한다."""

from __future__ import annotations

import re

from mvp_mcp.domain.spec.model import SpecDraft


class OpenApiRenderer:
    def render(self, draft: SpecDraft) -> str:
        interfaces = [
            item
            for item in (draft.design_contract.interfaces if draft.design_contract else [])
            if "http" in item.kind.lower() or "api" in item.kind.lower()
        ]
        if not interfaces:
            interfaces = []
        lines = [
            "openapi: 3.1.0",
            "info:",
            f"  title: {self._yaml(draft.user_request)}",
            "  version: 0.1.0",
            "  description: DRAFT contract; generation does not imply deployment.",
            "paths:",
        ]
        if not interfaces:
            lines.extend(
                [
                    "  /health:",
                    "    get:",
                    "      operationId: healthCheck",
                    "      responses:",
                    "        '200':",
                    "          description: Service health",
                ]
            )
        for index, item in enumerate(interfaces, start=1):
            slug = re.sub(r"[^a-z0-9]+", "-", item.name.lower()).strip("-") or f"operation-{index}"
            lines.extend(
                [
                    f"  /{slug}:",
                    "    post:",
                    f"      operationId: operation{index}",
                    f"      summary: {self._yaml(item.purpose)}",
                    "      requestBody:",
                    "        required: true",
                    "        content:",
                    "          application/json:",
                    "            schema:",
                    "              type: object",
                    f"              description: {self._yaml(item.input_summary)}",
                    "      responses:",
                    "        '200':",
                    f"          description: {self._yaml(item.output_summary)}",
                    "        '400':",
                    f"          description: {self._yaml('; '.join(item.error_cases))}",
                ]
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _yaml(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
