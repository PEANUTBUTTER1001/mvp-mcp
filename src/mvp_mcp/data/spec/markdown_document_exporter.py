"""Markdown 최종 문서의 파일시스템 내보내기 구현체."""

from __future__ import annotations

from pathlib import Path

from mvp_mcp.domain.spec.model import (
    ExportedDocuments,
    ExportedMvpBundle,
    ExportSpecRequest,
    MvpBundleRequest,
)


class MarkdownDocumentExporter:
    """명세별 고정 경로에 기획서와 실행 명세서를 저장한다."""

    def __init__(self, output_dir: str) -> None:
        self._output_dir = Path(output_dir).resolve()

    def export(self, request: ExportSpecRequest) -> ExportedDocuments:
        target_dir = (self._output_dir / request.spec_id).resolve()
        if self._output_dir not in target_dir.parents:
            raise ValueError("명세 ID가 출력 디렉터리 밖의 경로를 가리킵니다.")

        target_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = target_dir / "proposal.md"
        plan_path = target_dir / "plan.md"
        proposal_path.write_text(request.proposal_markdown, encoding="utf-8")
        plan_path.write_text(request.plan_markdown, encoding="utf-8")
        return ExportedDocuments(
            proposal_path=str(proposal_path),
            plan_path=str(plan_path),
        )


class ProjectMvpBundleExporter:
    """명시적으로 전달된 프로젝트 루트의 ``mvpmcp`` 폴더만 갱신한다."""

    _FILES = {
        "requirements.md": "requirements_markdown",
        "proposal.md": "proposal_markdown",
        "plan.md": "plan_markdown",
        "backlog.md": "backlog_markdown",
        "test-plan.md": "test_plan_markdown",
    }

    def export(
        self, project_root: str, request: MvpBundleRequest, verification: str
    ) -> ExportedMvpBundle:
        root = Path(project_root).resolve()
        if not root.is_dir():
            raise ValueError("프로젝트 루트가 존재하는 디렉터리가 아닙니다.")
        target = (root / "mvpmcp").resolve()
        if target.parent != root:
            raise ValueError("mvpmcp 출력 경로가 프로젝트 루트 밖을 가리킵니다.")
        target.mkdir(exist_ok=True)
        paths: dict[str, str] = {}
        for filename, field in self._FILES.items():
            path = target / filename
            path.write_text(str(getattr(request, field)), encoding="utf-8")
            paths[filename] = str(path)
        verification_path = target / "verification-report.md"
        verification_path.write_text(verification, encoding="utf-8")
        paths["verification-report.md"] = str(verification_path)
        return ExportedMvpBundle(paths=paths)
