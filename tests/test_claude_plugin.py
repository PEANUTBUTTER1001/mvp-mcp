"""mvpmcp Claude Code 플러그인(문서 스킬 + 시제품 스킬)·로컬 마켓·Codex 동기화 계약 테스트."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PLUGIN = _ROOT / "integrations" / "claude" / "plugin"
_PROTOTYPE = _PLUGIN / "skills" / "mvpmcpprototype" / "SKILL.md"


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    block = text.split("---\n", 2)[1]
    pairs = (line.split(":", 1) for line in block.splitlines() if ":" in line)
    return {key.strip(): value.strip() for key, value in pairs}


def test_plugin_manifest_matches_project_version() -> None:
    manifest = json.loads((_PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["name"] == "mvpmcp"
    assert manifest["version"] == project["project"]["version"]
    # 서버는 클라이언트에 이미 등록되어 있으므로 플러그인이 중복 등록하지 않는다.
    assert not (_PLUGIN / ".mcp.json").exists()


def test_local_marketplace_points_at_plugin() -> None:
    marketplace = json.loads(
        (_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    entry = marketplace["plugins"][0]

    assert marketplace["owner"]["name"]
    assert entry["name"] == "mvpmcp"
    assert entry["source"].startswith("./") and ".." not in entry["source"]
    assert (_ROOT / entry["source"]).resolve() == _PLUGIN.resolve()


def test_skill_names_match_folders_and_prototype_is_explicit_only() -> None:
    for name in ("mvpmcp", "mvpmcpprototype"):
        assert _frontmatter(_PLUGIN / "skills" / name / "SKILL.md")["name"] == name
    assert _frontmatter(_PROTOTYPE)["disable-model-invocation"] == "true"
    assert not (_ROOT / "integrations" / "claude" / "SKILL.md").exists()


def test_prototype_skill_keeps_original_steps_and_reads_mvpmcp_docs() -> None:
    content = _PROTOTYPE.read_text(encoding="utf-8")

    assert "`.mvpmcp/*/docs/`" in content and "`/mvpmcp:mvpmcp`" in content
    assert "mvp-mcp 도구를 호출하지 않고" in content
    assert content.index("## 방안 찾기") < content.index("# HTML 프로토타입")
    steps = [line for line in content.splitlines() if line[:2] in {f"{n}." for n in range(1, 8)}]
    assert len(steps) == 7
    design = content.split("## 디자인 지침", 1)[1].split("## 완료 보고", 1)[0]
    assert sum(line.startswith("- ") for line in design.splitlines()) == 5
    assert "outputs/" in content


def test_plugin_files_carry_no_personal_paths() -> None:
    files = [*_PLUGIN.rglob("*"), _ROOT / ".claude-plugin" / "marketplace.json"]
    for path in (item for item in files if item.is_file()):
        text = path.read_text(encoding="utf-8")
        assert "C:/Users" not in text and "C:\\Users" not in text, path


def test_codex_sync_copies_prototype_skill(tmp_path: Path) -> None:
    plugin = tmp_path / "mvpmcp"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text('{"name": "mvpmcp"}', encoding="utf-8")
    executable = tmp_path / "mvp-mcp.exe"
    executable.write_text("", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "sync_codex_plugin.py"),
            "--plugin-path",
            str(plugin),
            "--mcp-executable",
            str(executable),
        ],
        check=True,
        capture_output=True,
    )

    copied = plugin / "skills" / "mvpmcpprototype" / "SKILL.md"
    assert copied.read_text(encoding="utf-8") == _PROTOTYPE.read_text(encoding="utf-8")
    assert (plugin / "skills" / "mvpmcp" / "SKILL.md").is_file()
