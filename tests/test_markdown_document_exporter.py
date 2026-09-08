"""파일시스템 Markdown Exporter 테스트."""

from __future__ import annotations

from pathlib import Path

from mvp_mcp.data.spec.markdown_document_exporter import MarkdownDocumentExporter
from mvp_mcp.domain.spec.model import ExportSpecRequest


def test_exporter_writes_documents_and_replaces_only_same_spec(tmp_path: Path) -> None:
    """명세별 폴더에 저장하며 같은 명세의 두 파일만 최신 본문으로 교체한다."""
    exporter = MarkdownDocumentExporter(str(tmp_path))
    first = exporter.export(
        ExportSpecRequest(
            spec_id="spec-1", proposal_markdown="# 기획 v1", plan_markdown="# 구현 v1"
        )
    )
    exporter.export(
        ExportSpecRequest(
            spec_id="spec-2", proposal_markdown="# 다른 기획", plan_markdown="# 다른 구현"
        )
    )
    updated = exporter.export(
        ExportSpecRequest(
            spec_id="spec-1", proposal_markdown="# 기획 v2", plan_markdown="# 구현 v2"
        )
    )

    assert Path(first.proposal_path).read_text(encoding="utf-8") == "# 기획 v2"
    assert Path(updated.plan_path).read_text(encoding="utf-8") == "# 구현 v2"
    assert (tmp_path / "spec-2" / "proposal.md").read_text(encoding="utf-8") == "# 다른 기획"


def test_exporter_rejects_path_traversal_spec_id(tmp_path: Path) -> None:
    """명세 ID가 출력 루트 밖을 가리키면 저장하지 않는다."""
    exporter = MarkdownDocumentExporter(str(tmp_path))
    request = ExportSpecRequest(
        spec_id="../outside", proposal_markdown="# 기획", plan_markdown="# 구현"
    )

    try:
        exporter.export(request)
    except ValueError as exc:
        assert "출력 디렉터리 밖" in str(exc)
    else:
        raise AssertionError("경로 이탈 spec_id를 거부해야 합니다.")
