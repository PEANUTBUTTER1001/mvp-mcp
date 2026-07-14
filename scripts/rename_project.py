#!/usr/bin/env python3
"""템플릿 개명 스크립트 — ``mcp_server`` 를 실제 프로젝트 이름으로 일괄 치환한다.

이 템플릿을 새 폴더로 복사한 뒤 **한 번만** 실행하면 6단계 개명이 끝난다.
stdlib 만 사용하므로 Windows(sed 없음)에서도 그대로 동작한다.

사용법(프로젝트 루트에서):
    python scripts/rename_project.py weather
    python scripts/rename_project.py weather-mcp --dry-run   # 미리보기(변경 안 함)
    python scripts/rename_project.py weather --drop-template-docs  # 템플릿 설명문서 삭제

입력 ``weather`` (또는 ``weather-mcp``)로부터 아래를 유도해 치환한다:
    mcp_server  → weather_mcp     (패키지/import)
    mcp-server  → weather-mcp     (배포명/콘솔 스크립트)
    MCPSERVER_  → WEATHER_        (환경변수 접두사)
    MCPServer   → Weather         (서버명/클래스; MCPServerError → WeatherError 자동)
그리고 ``src/mcp_server/`` 디렉터리를 ``src/weather_mcp/`` 로 옮긴다.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 프로젝트 루트: <root>/scripts/rename_project.py → parents[1] == <root>
ROOT = Path(__file__).resolve().parents[1]

# 내용 치환에서 제외할 디렉터리(생성물·VCS 등).
_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "node_modules",
    "output",
    "build",
    "dist",
}

# 내용 치환에서 제외할 파일(템플릿 자체 설명 문서 + 이 스크립트).
# 이 문서들은 "mcp_server 를 이렇게 개명하라"는 설명이라 치환하면 내용이 깨진다.
_SKIP_FILES = {"TEMPLATE.md", "ARCHITECTURE_REVIEW.md", "rename_project.py"}

# 텍스트로 취급할 확장자(그 외는 UTF-8 디코딩 시도 실패 시 자동 스킵).
_TEXT_SUFFIXES = {
    ".py",
    ".toml",
    ".md",
    ".yml",
    ".yaml",
    ".cfg",
    ".ini",
    ".txt",
    ".json",
    "",  # Dockerfile 등 확장자 없는 파일
}


def derive_names(raw: str) -> dict[str, str]:
    """입력 이름에서 개명에 쓸 4가지 형태를 유도한다."""
    base = raw.strip().lower()
    base = re.sub(r"[-_ ]?mcp$", "", base)  # 끝의 -mcp/_mcp 제거
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")  # 슬러그 → snake
    if not base:
        sys.exit("오류: 유효한 이름이 아닙니다. 예: weather, weather-mcp")
    pascal = "".join(part.capitalize() for part in base.split("_"))
    return {
        "package": f"{base}_mcp",  # mcp_server →
        "dist": f"{base}-mcp",  # mcp-server →
        "prefix": f"{base.upper().replace('_', '')}_",  # MCPSERVER_ →
        "pascal": pascal,  # MCPServer →
    }


def _replacements(names: dict[str, str]) -> list[tuple[str, str]]:
    """(찾을 토큰, 바꿀 토큰) 목록. 대소문자가 달라 서로 충돌하지 않는다.

    ``MCPServer`` 를 먼저 바꾸면 ``MCPServerError`` 도 함께 처리된다.
    """
    return [
        ("MCPSERVER_", names["prefix"]),
        ("MCPServer", names["pascal"]),
        ("mcp_server", names["package"]),
        ("mcp-server", names["dist"]),
    ]


def _iter_text_files() -> list[Path]:
    """치환 대상 텍스트 파일을 수집한다(제외 규칙 적용)."""
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name in _SKIP_FILES:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        files.append(path)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="템플릿을 새 프로젝트 이름으로 개명한다.")
    parser.add_argument("name", help="새 프로젝트 이름 (예: weather 또는 weather-mcp)")
    parser.add_argument("--dry-run", action="store_true", help="변경하지 않고 무엇이 바뀔지만 출력")
    parser.add_argument(
        "--drop-template-docs",
        action="store_true",
        help="개명 후 템플릿 설명문서(TEMPLATE.md·ARCHITECTURE_REVIEW.md) 삭제",
    )
    args = parser.parse_args()

    pkg_dir = ROOT / "src" / "mcp_server"
    if not pkg_dir.is_dir():
        sys.exit("오류: src/mcp_server 가 없습니다. 이미 개명했거나 위치가 다릅니다.")

    names = derive_names(args.name)
    repls = _replacements(names)

    print("개명 계획:")
    print(f"  mcp_server  → {names['package']}")
    print(f"  mcp-server  → {names['dist']}")
    print(f"  MCPSERVER_  → {names['prefix']}")
    print(f"  MCPServer   → {names['pascal']}  (MCPServerError → {names['pascal']}Error)")
    print(f"  디렉터리     src/mcp_server → src/{names['package']}")
    print()

    changed_files = 0
    for path in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # 바이너리/읽기 불가 파일은 건너뛴다.
        new_text = text
        for old, new in repls:
            new_text = new_text.replace(old, new)
        if new_text != text:
            changed_files += 1
            rel = path.relative_to(ROOT)
            print(f"  {'[미리보기] ' if args.dry_run else '수정 '}{rel}")
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")

    if args.dry_run:
        print(f"\n[미리보기] {changed_files}개 파일 수정 예정(디렉터리 이동 포함). 변경 없음.")
        return

    # 패키지 디렉터리 이동.
    new_pkg_dir = ROOT / "src" / names["package"]
    pkg_dir.rename(new_pkg_dir)
    print(f"\n디렉터리 이동: src/mcp_server → src/{names['package']}")

    if args.drop_template_docs:
        for doc in ("TEMPLATE.md", "ARCHITECTURE_REVIEW.md"):
            target = ROOT / doc
            if target.exists():
                target.unlink()
                print(f"삭제: {doc}")

    print(f"\n완료: {changed_files}개 파일 수정. 다음을 순서대로 실행해 검증하세요:")
    print("  uv sync")
    print("  uv run ruff check --fix   # 개명으로 흐트러진 import 정렬 자동 교정")
    print("  uv run pytest")
    print("개명 스크립트는 이제 삭제해도 됩니다: scripts/rename_project.py")


if __name__ == "__main__":
    main()
