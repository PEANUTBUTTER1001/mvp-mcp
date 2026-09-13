"""서버 발급 Run 경로의 후보 Markdown package I/O 구현체."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.domain.spec.candidate_package_model import CandidatePackageSource


class CandidatePackageRepository:
    """``<output>/runs/<run_id>/candidate`` 밖의 후보 파일은 절대 읽지 않는다."""

    def __init__(self, output_dir: str) -> None:
        self._output_root = Path(output_dir).resolve()

    def ensure_workspace(self, run_id: str) -> str:
        root = self._candidate_root(run_id)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise PipelineError(
                "candidate_package",
                "candidate root는 symlink/reparse 경로일 수 없습니다.",
                "새 run으로 다시 시작하거나 서버 출력 경로를 확인하세요.",
            )
        return str(root)

    def read(self, run_id: str, candidate_root: str) -> CandidatePackageSource:
        root = self._candidate_root(run_id)
        if Path(candidate_root).resolve() != root:
            raise PipelineError(
                "candidate_package",
                "Run에 기록된 candidate root가 서버 발급 경로와 다릅니다.",
                "candidate_root를 Tool 입력으로 바꾸지 말고 run 상태를 다시 확인하세요.",
            )
        if not root.exists():
            return CandidatePackageSource(candidate_root=str(root))
        if root.is_symlink():
            raise PipelineError(
                "candidate_package",
                "candidate root는 symlink/reparse 경로일 수 없습니다.",
                "candidate 경로의 링크를 제거한 뒤 다시 시도하세요.",
            )

        files: dict[str, str] = {}
        for directory, directories, names in os.walk(root, followlinks=False):
            current = Path(directory)
            for child in directories:
                if (current / child).is_symlink():
                    raise PipelineError(
                        "candidate_package",
                        "candidate package 안에 symlink/reparse 디렉터리를 둘 수 없습니다.",
                        "실제 UTF-8 문서 파일만 candidate_root에 작성하세요.",
                    )
            for name in names:
                path = current / name
                if path.is_symlink():
                    raise PipelineError(
                        "candidate_package",
                        "candidate package 안에 symlink/reparse 파일을 둘 수 없습니다.",
                        "실제 UTF-8 문서 파일만 candidate_root에 작성하세요.",
                    )
                relative = self._safe_relative(root, path)
                if path.stat().st_size > 1_000_000:
                    raise PipelineError(
                        "candidate_package",
                        f"candidate 파일이 1 MiB 제한을 넘습니다: {relative}",
                        "문서·계약 파일을 분리하거나 불필요한 내용을 제거하세요.",
                    )
                try:
                    files[relative] = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise PipelineError(
                        "candidate_package",
                        f"candidate 파일은 UTF-8 텍스트여야 합니다: {relative}",
                        "바이너리·이미지 대신 UTF-8 Markdown, YAML, HTML만 작성하세요.",
                    ) from exc
        if len(files) > 32:
            raise PipelineError(
                "candidate_package",
                "candidate package 파일 수가 32개 제한을 넘습니다.",
                "현재 문서 계약에 포함되는 파일만 candidate_root에 두세요.",
            )
        return CandidatePackageSource(candidate_root=str(root), files=files)

    def _candidate_root(self, run_id: str) -> Path:
        if not _safe_segment(run_id):
            raise PipelineError(
                "candidate_package",
                "run_id에 candidate 경로로 사용할 수 없는 문자가 있습니다.",
                "서버가 반환한 run_id를 그대로 사용하세요.",
            )
        configured = self._output_root / "runs" / run_id / "candidate"
        for segment in (configured, configured.parent, configured.parent.parent):
            if segment.exists() and segment.is_symlink():
                raise PipelineError(
                    "candidate_package",
                    "candidate 경로의 중간 디렉터리는 symlink/reparse일 수 없습니다.",
                    "서버 출력 경로 아래의 실제 디렉터리만 사용하세요.",
                )
        root = configured.resolve()
        if self._output_root not in root.parents:
            raise PipelineError(
                "candidate_package",
                "candidate root가 서버 출력 디렉터리 밖을 가리킵니다.",
                "서버 출력 경로 설정을 확인하세요.",
            )
        return root

    @staticmethod
    def _safe_relative(root: Path, path: Path) -> str:
        resolved = path.resolve()
        if root not in resolved.parents:
            raise PipelineError(
                "candidate_package",
                "candidate 파일이 서버 발급 root 밖을 가리킵니다.",
                "candidate_root 밖 파일은 사용할 수 없습니다.",
            )
        relative = resolved.relative_to(root).as_posix()
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise PipelineError(
                "candidate_package",
                "candidate 파일 상대 경로가 안전하지 않습니다.",
                "허용된 상대 경로만 사용하세요.",
            )
        return relative


def _safe_segment(value: str) -> bool:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    return bool(value) and all(char in allowed for char in value)
