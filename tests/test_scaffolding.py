"""스캐폴딩 검증 테스트.

서버 부팅, 입력 스키마 강제, 의존성 역전(Domain 무의존)을 확인한다. 이 테스트는
도메인이 바뀌어도 그대로 유지해 아키텍처 규칙을 지키게 한다.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest
from pydantic import ValidationError

import mcp_server.domain as domain_pkg
from mcp_server.domain.note.model import NoteRequest
from mcp_server.main import build


def test_build_returns_fastmcp_server() -> None:
    """build() 가 예외 없이 FastMCP 인스턴스를 구성한다."""
    from mcp.server.fastmcp import FastMCP

    server = build()
    assert isinstance(server, FastMCP)


def test_note_request_rejects_blank_title() -> None:
    """필수 필드 누락/공백은 ValidationError 로 차단된다."""
    with pytest.raises(ValidationError):
        NoteRequest(title="")


def test_note_request_accepts_defaults() -> None:
    """본문은 생략 가능하며 기본값은 빈 문자열이다."""
    req = NoteRequest(title="제목")
    assert req.title == "제목"
    assert req.body == ""


def test_domain_has_no_framework_imports() -> None:
    """domain 패키지의 어떤 모듈도 프레임워크를 import 하지 않는다."""
    forbidden = {"mcp", "pydantic_settings", "sqlalchemy", "jinja2"}
    for mod in pkgutil.walk_packages(domain_pkg.__path__, prefix="mcp_server.domain."):
        module = importlib.import_module(mod.name)
        imported = set(getattr(module, "__dict__", {}).keys())
        for name in forbidden:
            assert name not in imported, f"{mod.name} 가 {name} 을(를) import 함"
