"""실행 가능한 아키텍처 가드레일.

문서로만 있는 규칙은 지켜지지 않는다. 여기서 규칙을 **테스트로** 강제한다:

1. 계층 의존 방향(presentation → data → domain → core)을 import-linter 로 검증.
2. 기대한 Tool 이 실제로 서버에 등록됐는지 검증(등록 누락 방지).

새 도구를 추가하면 아래 ``EXPECTED_TOOLS`` 에 이름을 더한다. 그러면 등록을 빠뜨렸을 때
테스트가 실패해 알려준다.
"""

from __future__ import annotations

import ast
from pathlib import Path

from importlinter.api import use_cases

from mvp_mcp.main import build

# 새 candidate 흐름의 공개 기본 계약이다.
CANONICAL_DOCUMENTATION_TOOLS = {
    "documentation_start_adaptive_wizard",
    "documentation_submit_adaptive_wizard_answers",
    "documentation_wizard_run_status",
    "documentation_validate_package",
    "documentation_preview_package",
    "documentation_apply_package",
    "documentation_package_status",
    "documentation_update_candidate_requirements",
    "documentation_update_candidate_architecture",
    "documentation_update_candidate_delivery",
    "documentation_record_candidate_test_run",
    "documentation_record_candidate_release",
}

# Run-scoped candidate lifecycle로 대체되어 이번 breaking release에서 제거한 Tool이다.
REMOVED_DIRECT_REPLACEMENT_TOOLS = {
    "documentation_validate",
    "documentation_preview",
    "documentation_apply",
    "documentation_start",
    "answer_question",
    "documentation_register_requirements",
    "documentation_register_architecture",
    "documentation_register_delivery",
    "documentation_record_test_run",
    "documentation_record_release",
}

EXPECTED_TOOLS = CANONICAL_DOCUMENTATION_TOOLS

REMOVED_LEGACY_TOOLS = {
    *REMOVED_DIRECT_REPLACEMENT_TOOLS,
    "start_spec",
    "finalize_spec",
    "export_spec",
    "validate_mvp_bundle",
    "export_mvp_bundle",
    "get_mvp_bundle_context",
    "documentation_collect_intake",
    "ask_elicitation_question",
    "ask_web_question",
    "ask_next_web_question",
}

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_layer_dependency_contract_holds() -> None:
    """계층 의존 방향 계약(import-linter)을 위반하지 않는다."""
    ok = use_cases.lint_imports(config_filename=str(_PYPROJECT))
    assert ok, "계층 의존 방향 위반: 낮은 레이어가 높은 레이어를 import 했습니다."


def test_only_main_imports_data_implementations() -> None:
    """Composition Root 외 production 계층은 data 구현체를 직접 참조하지 않는다."""
    package_root = _PYPROJECT.parent / "src" / "mvp_mcp"
    violations: list[str] = []
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(package_root)
        if relative == Path("main.py") or relative.parts[0] == "data":
            continue
        if _imports_data_implementation(path):
            violations.append(str(relative))

    assert not violations, f"main.py 외 data 구현체 import: {violations}"


def _imports_data_implementation(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith("mvp_mcp.data") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("mvp_mcp.data"):
                return True
    return False


def test_expected_tools_are_registered() -> None:
    """공개 Tool inventory가 Run-scoped canonical 집합과 정확히 일치한다."""
    server = build()
    registered = {tool.name for tool in server._tool_manager.list_tools()}
    assert registered == EXPECTED_TOOLS, f"Tool inventory 차이: {registered ^ EXPECTED_TOOLS}"
    assert not (
        REMOVED_LEGACY_TOOLS & registered
    ), f"구형 문서 Tool이 남아 있습니다: {REMOVED_LEGACY_TOOLS & registered}"


def test_cutover_guidance_is_consistent_across_public_docs() -> None:
    root = _PYPROJECT.parent
    documents = [
        "README.md",
        "HANDOFF.md",
        "progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md",
        "integrations/codex/SKILL.md",
        "integrations/claude/SKILL.md",
        "integrations/gemini/GEMINI.md",
    ]
    for relative in documents:
        content = (root / relative).read_text(encoding="utf-8")
        assert "Run-scoped candidate lifecycle" in content, f"신규 lifecycle 안내 누락: {relative}"
        assert "제거 완료" in content, f"breaking cutover 안내 누락: {relative}"


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
        "src/mvp_mcp/presentation/tools/ask_web_question.py",
        "src/mvp_mcp/presentation/tools/ask_next_web_question.py",
        "src/mvp_mcp/presentation/tools/ask_elicitation_question.py",
        "src/mvp_mcp/presentation/tools/documentation_collect_intake.py",
        "src/mvp_mcp/presentation/tools/answer_question.py",
        "src/mvp_mcp/presentation/tools/documentation_apply.py",
        "src/mvp_mcp/presentation/tools/documentation_preview.py",
        "src/mvp_mcp/presentation/tools/documentation_record_release.py",
        "src/mvp_mcp/presentation/tools/documentation_record_test_run.py",
        "src/mvp_mcp/presentation/tools/documentation_register_architecture.py",
        "src/mvp_mcp/presentation/tools/documentation_register_delivery.py",
        "src/mvp_mcp/presentation/tools/documentation_register_requirements.py",
        "src/mvp_mcp/presentation/tools/documentation_start.py",
        "src/mvp_mcp/presentation/tools/documentation_validate.py",
        "src/mvp_mcp/domain/spec/documentation_usecase.py",
        "src/mvp_mcp/presentation/web/local_adaptive_wizard_form.py",
        "src/mvp_mcp/presentation/web/local_question_form.py",
        "src/mvp_mcp/presentation/web/local_survey_form.py",
    ]
    assert not [relative for relative in removed if (root / relative).exists()]


def test_documentation_tools_publish_safety_annotations() -> None:
    tools = {tool.name: tool for tool in build()._tool_manager.list_tools()}
    destructive = {
        "documentation_apply_package",
        # safe_auto_apply는 이 Tool 안에서 실제 .mvpmcp write를 수행할 수 있다.
        "documentation_preview_package",
    }
    for name in EXPECTED_TOOLS:
        if not name.startswith("documentation_"):
            continue
        assert tools[name].annotations is not None, f"Tool annotation 누락: {name}"
        assert tools[name].annotations.destructiveHint is (name in destructive)
    assert tools["documentation_package_status"].annotations.readOnlyHint is True


def test_client_facing_tools_publish_continuation_and_revision_contracts() -> None:
    tools = {tool.name: tool for tool in build()._tool_manager.list_tools()}
    adaptive = tools["documentation_start_adaptive_wizard"]
    submit = tools["documentation_submit_adaptive_wizard_answers"]
    run_status = tools["documentation_wizard_run_status"]
    package_status = tools["documentation_package_status"]
    package_validate = tools["documentation_validate_package"]
    requirements = tools["documentation_update_candidate_requirements"]

    assert requirements.parameters["properties"]["mode"]["default"] == "upsert"
    assert "expected_run_version" in requirements.parameters["properties"]
    assert "phase" in adaptive.parameters["properties"]
    assert "질문 schema" in (adaptive.description or "")
    assert "answers" in submit.parameters["properties"]
    assert run_status.annotations is not None
    assert run_status.annotations.readOnlyHint is True
    assert package_status.annotations is not None
    assert package_status.annotations.readOnlyHint is True
    assert "candidate_revision" in package_validate.parameters["properties"]
