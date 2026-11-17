"""대상 프로젝트 루트의 사람 소유 텍스트 파일을 해시 조건부로 원자 교체하는 구현체."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from secrets import token_urlsafe


class ProjectRootTextFileImpl:
    """프로젝트 루트 바로 아래의 허용된 파일만 다룬다. symlink·상위 경로는 거부한다."""

    def __init__(self, allowed_files: frozenset[str] = frozenset({"AGENTS.md"})) -> None:
        self._allowed = allowed_files

    def read(self, project_root: str, relative_path: str) -> str | None:
        path = self._resolve(project_root, relative_path)
        if not path.exists():
            return None
        return path.read_bytes().decode("utf-8")

    def replace_if_unchanged(
        self,
        project_root: str,
        relative_path: str,
        content: str,
        expected_sha256: str | None,
    ) -> bool:
        path = self._resolve(project_root, relative_path)
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if current != expected_sha256:
            return False
        temporary = path.with_name(f".{path.name}.{token_urlsafe(8)}.tmp")
        try:
            temporary.write_bytes(content.encode("utf-8"))
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return True

    def _resolve(self, project_root: str, relative_path: str) -> Path:
        if relative_path not in self._allowed:
            raise ValueError(f"루트 파일 쓰기가 허용되지 않은 경로입니다: {relative_path}")
        root = Path(project_root).resolve()
        if not root.is_dir():
            raise ValueError("프로젝트 루트가 존재하는 디렉터리가 아닙니다.")
        candidate = root / PurePosixPath(relative_path).name
        if candidate.is_symlink():
            raise ValueError("symlink인 루트 파일은 수정할 수 없습니다.")
        path = candidate.resolve()
        if path.parent != root:
            raise ValueError("루트 파일 경로가 프로젝트 루트 밖을 가리킵니다.")
        return path
