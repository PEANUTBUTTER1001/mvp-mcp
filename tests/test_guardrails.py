"""실행 가능한 아키텍처 가드레일.

문서로만 있는 규칙은 지켜지지 않는다. 여기서 규칙을 **테스트로** 강제한다:

1. 계층 의존 방향(presentation → data → domain → core)을 import-linter 로 검증.
2. 기대한 Tool 이 실제로 서버에 등록됐는지 검증(등록 누락 방지).

새 도구를 추가하면 아래 ``EXPECTED_TOOLS`` 에 이름을 더한다. 그러면 등록을 빠뜨렸을 때
테스트가 실패해 알려준다.
"""

from __future__ import annotations

from pathlib import Path

from importlinter.api import use_cases

from mcp_server.main import build

# 이 프로젝트에 존재해야 하는 Tool 이름(도구 추가 시 여기에 등록).
EXPECTED_TOOLS = {"create_note", "search_note"}

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_layer_dependency_contract_holds() -> None:
    """계층 의존 방향 계약(import-linter)을 위반하지 않는다."""
    ok = use_cases.lint_imports(config_filename=str(_PYPROJECT))
    assert ok, "계층 의존 방향 위반: 낮은 레이어가 높은 레이어를 import 했습니다."


def test_expected_tools_are_registered() -> None:
    """build() 가 기대한 Tool 을 모두 등록한다(등록 누락 방지)."""
    server = build()
    registered = {tool.name for tool in server._tool_manager.list_tools()}
    assert EXPECTED_TOOLS <= registered, f"등록 누락: {EXPECTED_TOOLS - registered}"
