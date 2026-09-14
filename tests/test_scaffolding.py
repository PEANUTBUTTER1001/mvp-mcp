"""스캐폴딩 검증 테스트.

서버 부팅, 입력 스키마 강제, 의존성 역전(Domain 무의존)을 확인한다. 이 테스트는
도메인이 바뀌어도 그대로 유지해 아키텍처 규칙을 지키게 한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mvp_mcp.domain as domain_pkg
from mvp_mcp.core.security import is_absolute_path
from mvp_mcp.main import build

_FORBIDDEN_DOMAIN_IMPORT_ROOTS = {
    "jinja2",
    "mcp",
    "pathlib",
    "pydantic_settings",
    "sqlalchemy",
    "sqlite3",
}


def test_build_returns_fastmvp_mcp() -> None:
    """build() 가 예외 없이 FastMCP 인스턴스를 구성한다."""
    from mcp.server.fastmcp import FastMCP

    server = build()
    assert isinstance(server, FastMCP)


def test_core_path_policy_accepts_absolute_paths_only() -> None:
    assert is_absolute_path("C:/workspace/mvp-mcp")
    assert is_absolute_path(r"C:\workspace\mvp-mcp")
    assert is_absolute_path("/workspace/mvp-mcp")
    assert not is_absolute_path("C:workspace/mvp-mcp")
    assert not is_absolute_path("relative/project")


def test_domain_has_no_framework_or_filesystem_imports() -> None:
    """Domain은 framework·DB·renderer·filesystem 구현을 직접 import하지 않는다."""
    domain_root = Path(domain_pkg.__file__).parent
    violations: dict[str, list[str]] = {}
    for path in domain_root.rglob("*.py"):
        imported_roots = _import_roots(path)
        forbidden = sorted(imported_roots & _FORBIDDEN_DOMAIN_IMPORT_ROOTS)
        if forbidden:
            violations[str(path.relative_to(domain_root))] = forbidden

    assert not violations, f"domain 금지 import: {violations}"


def _import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", maxsplit=1)[0])
    return roots
