"""경로 안전·파일명 새니타이즈 보안 게이트(순수 함수).

파일시스템을 다루는 어댑터가 공통으로 사용한다. 프레임워크 의존성 없이
stdlib(``pathlib``/``re``)만 사용한다. 파일을 읽거나 쓰지 않는 MCP 서버라면 이 모듈을
삭제해도 된다.
"""

from __future__ import annotations

import re
from pathlib import Path

# 스캔/순회에서 제외할 디렉터리 이름(가상환경·VCS·캐시·서드파티 설치물 등).
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "site-packages",
        "dist-packages",
        ".idea",
        ".vscode",
        "build",
        "dist",
        ".tox",
        ".eggs",
    }
)

# 민감 파일명(비밀·자격증명 등) — 노출/스캔 차단.
_SENSITIVE_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        ".pypirc",
        ".netrc",
        ".npmrc",
        "credentials",
        "secrets.yaml",
        "secrets.yml",
    }
)
_SENSITIVE_SUFFIXES: tuple[str, ...] = (".pem", ".key", ".pfx", ".p12")

# 파일명에 허용하지 않는 문자(경로 구분자·예약 문자·제어 문자).
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_within_root(path: Path, root: Path) -> bool:
    """``path`` 가 ``root`` 경계 안에 있으면 True. 심볼릭 링크는 거부한다(경로 탈출 방지)."""
    try:
        if path.is_symlink():
            return False
        resolved = path.resolve()
        root_resolved = root.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved == root_resolved or root_resolved in resolved.parents


def is_sensitive(path: Path) -> bool:
    """민감 파일(.env·키·자격증명 등)이면 True."""
    lowered = path.name.lower()
    if lowered in _SENSITIVE_NAMES:
        return True
    if lowered.startswith(".env"):
        return True
    return path.suffix.lower() in _SENSITIVE_SUFFIXES


def is_excluded_dir(name: str) -> bool:
    """순회에서 제외할 디렉터리 이름이면 True(숨김 디렉터리 포함)."""
    if name in (".", ".."):
        return False
    return name in EXCLUDED_DIRS or name.startswith(".")


def sanitize_filename(name: str, *, fallback: str = "output", max_length: int = 120) -> str:
    """경로 구분자/예약 문자를 제거해 안전한 단일 파일명으로 만든다.

    경로 탈출(``..``)·디렉터리 분리·예약 문자를 모두 무력화하여, 출력은 항상 출력
    디렉터리 직속의 단일 파일명이 되도록 보장한다.
    """
    candidate = name.replace("\\", "/").replace("/", "_")
    candidate = _UNSAFE_CHARS.sub("_", candidate)
    candidate = candidate.replace("..", "_")
    candidate = re.sub(r"\s+", " ", candidate).strip()
    candidate = candidate[:max_length].strip("_ .")
    return candidate or fallback
