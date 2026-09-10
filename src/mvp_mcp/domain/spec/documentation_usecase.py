"""가이드 기반 문서 검증·미리보기·적용 유스케이스."""

from __future__ import annotations

from mvp_mcp.core.exceptions import PipelineError

from .documentation_model import (
    DocumentationApplyResult,
    DocumentationPreview,
    DocumentationValidationResult,
)
from .ports import GuidePackageRenderer, RepositoryDocumentationExporter
from .repository import SpecRepository
from .stage_gate import validate_documentation


def _draft(repo: SpecRepository, spec_id: str):  # type: ignore[no-untyped-def]
    draft = repo.find_by_id(spec_id)
    if draft is None:
        raise PipelineError(
            "load", "명세 세션을 찾을 수 없습니다.", "documentation_start부터 실행하세요."
        )
    return draft


class ValidateDocumentationUseCase:
    def __init__(self, specs: SpecRepository) -> None:
        self._specs = specs

    def __call__(self, spec_id: str) -> DocumentationValidationResult:
        return validate_documentation(_draft(self._specs, spec_id))


class PreviewDocumentationUseCase:
    def __init__(
        self,
        specs: SpecRepository,
        renderer: GuidePackageRenderer,
        exporter: RepositoryDocumentationExporter,
    ) -> None:
        self._specs = specs
        self._renderer = renderer
        self._exporter = exporter

    def __call__(self, spec_id: str) -> DocumentationPreview:
        draft = _draft(self._specs, spec_id)
        result = validate_documentation(draft)
        if not result.bundle_valid or not result.implementation_ready:
            details = result.issues + result.blocking_items
            raise PipelineError(
                "quality_gate",
                "; ".join(details),
                "누락·미확정 계약을 해결한 뒤 documentation_validate를 다시 실행하세요.",
            )
        package = self._renderer.render(draft)
        return self._exporter.preview(spec_id, draft.project_root, package)


class ApplyDocumentationUseCase:
    def __init__(self, exporter: RepositoryDocumentationExporter) -> None:
        self._exporter = exporter

    def __call__(
        self,
        preview_id: str,
        manifest_sha256: str,
        approved_by: str,
        approval_note: str,
    ) -> DocumentationApplyResult:
        if not approved_by.strip() or not approval_note.strip():
            raise PipelineError(
                "approval",
                "적용 승인자와 승인 메모가 필요합니다.",
                "preview 내용을 확인한 사용자의 이름과 승인 범위를 입력하세요.",
            )
        return self._exporter.apply(
            preview_id, manifest_sha256, approved_by.strip(), approval_note.strip()
        )
