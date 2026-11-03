"""서버 발급 Run 경로의 후보 Markdown package I/O 구현체."""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.domain.spec.candidate_file_model import CandidateFileMetadata
from mvp_mcp.domain.spec.candidate_package_model import CandidatePackageSource
from mvp_mcp.domain.spec.candidate_package_policy import allowed_candidate_paths


class CandidatePackageRepository:
    """``<output>/runs/<run_id>/candidate`` 밖의 후보 파일은 절대 읽지 않는다."""

    _locks: dict[str, threading.RLock] = {}
    _locks_guard = threading.Lock()

    def __init__(self, output_dir: str) -> None:
        self._output_root = Path(output_dir).resolve()

    def ensure_workspace(self, run_id: str) -> str:
        root = self._candidate_root(run_id)
        root.mkdir(parents=True, exist_ok=True)
        if _is_link(root):
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
        if _is_link(root):
            raise PipelineError(
                "candidate_package",
                "candidate root는 symlink/reparse 경로일 수 없습니다.",
                "candidate 경로의 링크를 제거한 뒤 다시 시도하세요.",
            )

        files: dict[str, str] = {}
        for directory, directories, names in os.walk(root, followlinks=False):
            current = Path(directory)
            for child in directories:
                if _is_link(current / child):
                    raise PipelineError(
                        "candidate_package",
                        "candidate package 안에 symlink/reparse 디렉터리를 둘 수 없습니다.",
                        "실제 UTF-8 문서 파일만 candidate_root에 작성하세요.",
                    )
            for name in names:
                path = current / name
                if _is_link(path) or not path.is_file():
                    raise PipelineError(
                        "candidate_package",
                        "candidate package 안에 symlink/reparse 파일을 둘 수 없습니다.",
                        "실제 UTF-8 문서 파일만 candidate_root에 작성하세요.",
                    )
                if name.startswith(".mvpmcp-write-") and name.endswith(".tmp"):
                    continue  # atomic writer의 프로세스 중단 잔여물은 package가 아니다.
                relative = self._safe_relative(root, path)
                if path.stat().st_size > 1_000_000:
                    raise PipelineError(
                        "candidate_package",
                        f"candidate 파일이 1,000,000바이트 제한을 넘습니다: {relative}",
                        "문서·계약 파일을 분리하거나 불필요한 내용을 제거하세요.",
                    )
                try:
                    files[relative] = path.read_bytes().decode("utf-8")
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

    @contextmanager
    def exclusive(self, run_id: str) -> Iterator[None]:
        """같은 Run의 writer/validate/preview/apply/lifecycle을 프로세스 간 보호한다."""
        root = Path(self.ensure_workspace(run_id))
        lock_path = root.parent / ".candidate.lock"
        with self._locks_guard:
            lock = self._locks.setdefault(str(lock_path), threading.RLock())
        with lock:
            if _is_link(lock_path) or (lock_path.exists() and lock_path.stat().st_nlink > 1):
                raise PipelineError("candidate_write", "안전하지 않은 Run 잠금 파일입니다.")
            with lock_path.open("a+b") as handle:
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                try:
                    if sys.platform == "win32":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise PipelineError(
                        "candidate_write",
                        "다른 프로세스가 같은 Run을 처리 중입니다.",
                        "현재 요청 완료 후 같은 요청으로 다시 시도하세요.",
                    ) from exc
                try:
                    yield
                finally:
                    handle.seek(0)
                    if sys.platform == "win32":
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def write_file(
        self,
        run_id: str,
        candidate_root: str,
        relative_path: str,
        content: str,
        expected_sha256: str | None,
    ) -> CandidateFileMetadata:
        """이미 exclusive를 보유한 UseCase의 hash 조건부 파일 교체. 셸 실행 없음."""
        root = self._candidate_root(run_id)
        if Path(candidate_root).resolve() != root or relative_path not in allowed_candidate_paths():
            raise PipelineError("candidate_write", "허용되지 않은 후보 경로입니다.")
        path = self._safe_destination(root, relative_path)
        encoded = content.encode("utf-8")
        if len(encoded) > 1_000_000:
            raise PipelineError("candidate_write", "후보 파일은 1,000,000바이트 이하여야 합니다.")
        source = self.read(run_id, candidate_root)
        if relative_path not in source.files and len(source.files) >= 32:
            raise PipelineError("candidate_write", "후보 파일 수는 32개 이하여야 합니다.")
        _assert_file_hash(path, expected_sha256)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            descriptor, name = tempfile.mkstemp(
                dir=path.parent, prefix=".mvpmcp-write-", suffix=".tmp"
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            # 임시 파일을 준비하는 동안 바뀐 부모 경로/외부 파일도 교체 전에 확인한다.
            self._safe_destination(root, relative_path)
            _assert_file_hash(path, expected_sha256)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return CandidateFileMetadata(
            relative_path=relative_path,
            sha256=hashlib.sha256(encoded).hexdigest(),
            byte_count=len(encoded),
        )

    def write_generated(self, run_id: str, candidate_root: str, files: dict[str, str]) -> None:
        """같은 본문만 멱등적으로 허용하고 사용자 수정 파일은 덮어쓰지 않는다."""
        root = self._candidate_root(run_id)
        if Path(candidate_root).resolve() != root:
            raise PipelineError(
                "candidate_package",
                "Run에 기록된 candidate root가 서버 발급 경로와 다릅니다.",
                "candidate_root를 변경하지 말고 run 상태를 다시 확인하세요.",
            )
        root.mkdir(parents=True, exist_ok=True)
        for relative, content in files.items():
            path = self._safe_destination(root, relative)
            if path.is_file() and path.read_text(encoding="utf-8") != content:
                raise PipelineError(
                    "candidate_package",
                    f"생성 디자인 산출물이 이미 수정되었습니다: {relative}",
                    "새 run을 시작하거나 현재 candidate의 디자인 문서를 검토하세요.",
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

    def _candidate_root(self, run_id: str) -> Path:
        if not _safe_segment(run_id):
            raise PipelineError(
                "candidate_package",
                "run_id에 candidate 경로로 사용할 수 없는 문자가 있습니다.",
                "서버가 반환한 run_id를 그대로 사용하세요.",
            )
        configured = self._output_root / "runs" / run_id / "candidate"
        for segment in (configured, configured.parent, configured.parent.parent):
            if _is_link(segment):
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
    def _safe_destination(root: Path, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or not pure.parts
            or str(pure) != relative
            or "\\" in relative
            or ":" in relative
            or "\x00" in relative
        ):
            raise PipelineError(
                "candidate_package",
                "candidate 파일 상대 경로가 안전하지 않습니다.",
                "허용된 상대 경로만 사용하세요.",
            )
        destination = root.joinpath(*pure.parts)
        for segment in (
            root,
            *[root.joinpath(*pure.parts[:i]) for i in range(1, len(pure.parts) + 1)],
        ):
            if _is_link(segment):
                raise PipelineError("candidate_write", "symlink/reparse 경로는 사용할 수 없습니다.")
        if root not in destination.resolve().parents:
            raise PipelineError(
                "candidate_package",
                "candidate 파일이 서버 발급 root 밖을 가리킵니다.",
                "candidate_root 밖 파일은 사용할 수 없습니다.",
            )
        return destination

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


def _is_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _assert_file_hash(path: Path, expected: str | None) -> None:
    if _is_link(path) or (path.exists() and not path.is_file()):
        raise PipelineError("candidate_write", "일반 후보 파일만 교체할 수 있습니다.")
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if actual != expected:
        raise PipelineError(
            "candidate_write_conflict",
            f"후보 파일 변경 충돌: current_sha256={actual}",
            "최신 파일을 검토하고 새 idempotency_key와 현재 파일 hash로 다시 요청하세요.",
        )
