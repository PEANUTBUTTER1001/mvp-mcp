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

from mvp_mcp.main import build

# 이 프로젝트에 존재해야 하는 Tool 이름(도구 추가 시 여기에 등록).
EXPECTED_TOOLS = {
    "ask_elicitation_question",
    "ask_web_question",
    "documentation_validate",
    "documentation_preview",
    "documentation_apply",
    "documentation_start",
    "documentation_collect_intake",
    "documentation_register_requirements",
    "documentation_register_architecture",
    "documentation_register_delivery",
    "documentation_record_test_run",
    "documentation_record_release",
}

REMOVED_LEGACY_TOOLS = {
    "start_spec",
    "finalize_spec",
    "export_spec",
    "validate_mvp_bundle",
    "export_mvp_bundle",
    "get_mvp_bundle_context",
}

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
    assert not (
        REMOVED_LEGACY_TOOLS & registered
    ), f"구형 문서 Tool이 남아 있습니다: {REMOVED_LEGACY_TOOLS & registered}"


def test_legacy_document_export_modules_are_deleted() -> None:
    root = Path(__file__).resolve().parents[1]
    removed = [
        "src/mvp_mcp/presentation/tools/finalize_spec.py",
        "src/mvp_mcp/presentation/tools/export_spec.py",
        "src/mvp_mcp/presentation/tools/delivery.py",
        "src/mvp_mcp/data/spec/markdown_document_exporter.py",
        "src/mvp_mcp/domain/spec/delivery_quality.py",
        "src/mvp_mcp/domain/spec/output_format.py",
        "src/mvp_mcp/presentation/tools/ask_web_survey.py",
    ]
    assert not [relative for relative in removed if (root / relative).exists()]


def test_documentation_tools_publish_safety_annotations() -> None:
    tools = {tool.name: tool for tool in build()._tool_manager.list_tools()}
    for name in EXPECTED_TOOLS:
        if not name.startswith("documentation_"):
            continue
        assert tools[name].annotations is not None, f"Tool annotation 누락: {name}"
        assert tools[name].annotations.destructiveHint is (name == "documentation_apply")
    assert tools["documentation_validate"].annotations.readOnlyHint is True


def test_client_facing_tools_publish_continuation_and_revision_contracts() -> None:
    tools = {tool.name: tool for tool in build()._tool_manager.list_tools()}
    intake = tools["documentation_collect_intake"]
    requirements = tools["documentation_register_requirements"]
    manual_start = tools["documentation_start"]

    assert intake.description is not None
    assert "같은 턴" in intake.description
    assert requirements.parameters["properties"]["mode"]["default"] == "upsert"
    assert "requested_features" in manual_start.parameters["properties"]
