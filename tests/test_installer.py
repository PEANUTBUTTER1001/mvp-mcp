"""클론 후 한 줄 설치 스크립트(scripts/install.py): 서비스별 등록·멱등·dry-run·손상 파일 보호."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PROTOTYPE = (
    _ROOT / "integrations" / "claude" / "plugin" / "skills" / "mvpmcpprototype" / "SKILL.md"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mvp_install", _ROOT / "scripts" / "install.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mvp_install"] = module
    spec.loader.exec_module(module)
    return module


install = _load()


class FakeClaude:
    """claude CLI 대역: 등록 상태를 기억하고 호출 순서를 기록한다."""

    def __init__(self, server: bool = False, market: bool = False, plugin: bool = False) -> None:
        self.server, self.market, self.plugin = server, market, plugin
        self.calls: list[list[str]] = []

    def __call__(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        command = list(args)[1:]
        self.calls.append(command)
        out, code = "", 0
        match command[:3]:
            case ["mcp", "get", _]:
                code = 0 if self.server else 1
            case ["mcp", "add", _]:
                self.server = True
            case ["plugin", "marketplace", "list"]:
                out = "mvpmcp-local" if self.market else ""
            case ["plugin", "marketplace", "add"]:
                self.market = True
            case ["plugin", "list", *_]:
                out = "mvpmcp@mvpmcp-local" if self.plugin else ""
            case ["plugin", "install", _]:
                self.plugin = True
        return subprocess.CompletedProcess(list(args), code, out, "")

    def changes(self) -> list[str]:
        writes = [call for call in self.calls if not {"get", "list"} & set(call[:3])]
        return [" ".join(call[:2]) for call in writes]


def _which(*names: str):  # type: ignore[no-untyped-def]
    available = {"uv", *names}
    return lambda name: f"/bin/{name}" if name in available else None


def _run(home: Path, fake: FakeClaude | None = None, *extra: str, which=None) -> int:  # type: ignore[no-untyped-def]
    args = ["--home", str(home), "--claude-config-dir", str(home / "desktop"), *extra]
    return int(install.main(args, runner=fake or FakeClaude(), which=which or _which("claude")))


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_claude_registers_server_market_plugin_then_updates_on_rerun(tmp_path: Path) -> None:
    fake = FakeClaude()

    assert _run(tmp_path, fake, "--host", "claude") == 0
    assert fake.changes() == ["mcp add", "plugin marketplace", "plugin install"]
    add = next(call for call in fake.calls if call[:2] == ["mcp", "add"])
    directory = add[add.index("--directory") + 1]
    assert Path(directory).is_absolute() and "\\" not in directory
    assert add[-2:] == ["run", "mvp-mcp"]

    fake.calls.clear()
    assert _run(tmp_path, fake, "--host", "claude") == 0
    assert fake.changes() == ["plugin update"]


def test_claude_skips_server_registered_in_desktop_config(tmp_path: Path) -> None:
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    config = {"mcpServers": {"mvp": {"command": "uv", "args": ["run", "mvp-mcp"]}}}
    (desktop / "claude_desktop_config.json").write_text(json.dumps(config), encoding="utf-8")
    fake = FakeClaude()

    assert _run(tmp_path, fake, "--host", "claude") == 0
    assert not any(call[:2] == ["mcp", "get"] or call[:2] == ["mcp", "add"] for call in fake.calls)


def test_codex_appends_server_once_with_backup_and_copies_skills(tmp_path: Path) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text('model = "gpt"\n[mcp_servers.other]\ncommand = "x"', encoding="utf-8")

    assert _run(tmp_path, None, "--host", "codex") == 0
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["model"] == "gpt" and "other" in parsed["mcp_servers"]
    server = parsed["mcp_servers"]["mvp-mcp"]
    assert server["command"] == "uv" and server["args"][-2:] == ["run", "mvp-mcp"]
    assert len(list(config.parent.glob("config.toml.bak-*"))) == 1
    skills = tmp_path / ".codex" / "skills"
    assert (skills / "mvpmcp" / "SKILL.md").read_text(encoding="utf-8") == (
        _ROOT / "integrations" / "codex" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert (skills / "mvpmcpprototype" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == _PROTOTYPE.read_text(encoding="utf-8")

    before = _snapshot(tmp_path)
    assert _run(tmp_path, None, "--host", "codex") == 0
    assert _snapshot(tmp_path) == before
    assert config.read_text(encoding="utf-8").count("[mcp_servers.mvp-mcp]") == 1


def test_antigravity_keeps_existing_servers_and_adds_only_mvp_mcp(tmp_path: Path) -> None:
    config = tmp_path / ".gemini" / "antigravity" / "mcp_config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"git": {"command": "git-mcp"}}}), "utf-8")

    assert _run(tmp_path, None, "--host", "antigravity") == 0
    servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
    assert servers["git"] == {"command": "git-mcp"}
    assert servers["mvp-mcp"]["args"][-2:] == ["run", "mvp-mcp"]
    for name in ("mvpmcp", "mvpmcpprototype"):
        assert (config.parent / "skills" / name / "SKILL.md").is_file()


def test_antigravity_empty_or_bom_config_counts_as_empty(tmp_path: Path) -> None:
    # Antigravity는 ~/.gemini/config/mcp_config.json을 0바이트로 미리 만들어 두기도 한다.
    config = tmp_path / ".gemini" / "config" / "mcp_config.json"
    config.parent.mkdir(parents=True)
    config.write_text("", encoding="utf-8")

    assert _run(tmp_path, None, "--host", "antigravity") == 0
    assert "mvp-mcp" in json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
    assert (config.parent / "skills" / "mvpmcp" / "SKILL.md").is_file()

    bom = tmp_path / "bom"
    bom_config = bom / ".gemini" / "config" / "mcp_config.json"
    bom_config.parent.mkdir(parents=True)
    bom_config.write_text('{"mcpServers": {}}', encoding="utf-8-sig")
    assert _run(bom, None, "--host", "antigravity") == 0
    assert "mvp-mcp" in json.loads(bom_config.read_text(encoding="utf-8"))["mcpServers"]


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".gemini" / "config").mkdir(parents=True)
    before = _snapshot(tmp_path)
    fake = FakeClaude()

    assert _run(tmp_path, fake, "--dry-run") == 0
    assert _snapshot(tmp_path) == before
    assert fake.changes() == []


def test_broken_config_is_reported_and_left_untouched(tmp_path: Path) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    config.write_text("[[[broken", encoding="utf-8")

    assert _run(tmp_path, None, "--host", "codex") == 1
    assert config.read_text(encoding="utf-8") == "[[[broken"
    assert not list(config.parent.glob("config.toml.bak-*"))


def test_missing_uv_or_no_host_exits_with_guidance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, None, which=lambda name: None) == 1
    assert "uv를 찾을 수 없습니다" in capsys.readouterr().out
    assert _run(tmp_path, None, which=_which()) == 1
    assert "--host" in capsys.readouterr().out


def test_root_launchers_run_installer_with_correct_line_endings() -> None:
    windows = (_ROOT / "install.cmd").read_bytes()
    unix = (_ROOT / "install.sh").read_bytes()

    assert b"uv run scripts/install.py %*" in windows and b'cd /d "%~dp0"' in windows
    assert b'exec uv run scripts/install.py "$@"' in unix and unix.startswith(
        b"#!/usr/bin/env sh\n"
    )
    assert b"\r\n" not in unix
    attributes = (_ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.sh text eol=lf" in attributes and "*.cmd text eol=crlf" in attributes
