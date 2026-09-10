"""현재 저장소 계약을 기존 개인 Codex 플러그인 원본에 동기화한다."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin-path", type=Path, required=True)
    parser.add_argument("--mcp-executable", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    plugin = args.plugin_path.resolve()
    executable = args.mcp_executable.resolve()
    manifest_path = plugin / ".codex-plugin" / "plugin.json"
    skill_path = plugin / "skills" / "mvpmcp" / "SKILL.md"
    mcp_path = plugin / ".mcp.json"

    if plugin.name != "mvpmcp" or not manifest_path.is_file():
        raise SystemExit(f"검증된 mvpmcp 플러그인 원본이 아닙니다: {plugin}")
    if not executable.is_file():
        raise SystemExit(f"MCP 실행 파일을 찾을 수 없습니다: {executable}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("name") != "mvpmcp":
        raise SystemExit("plugin.json name이 mvpmcp가 아닙니다.")
    project = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))
    manifest["version"] = project["project"]["version"]
    manifest["description"] = "Generate validated Human-AI repository documentation packages."
    interface = manifest.setdefault("interface", {})
    interface["shortDescription"] = "Generate a validated .mvpmcp documentation package."
    interface["longDescription"] = (
        "Runs one web Wizard, applies recommended low-risk defaults, validates traceability, "
        "and previews an approval-gated .mvpmcp documentation package."
    )

    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        (repository / "integrations" / "codex" / "SKILL.md").read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    mcp_path.write_text(
        json.dumps(
            {"mcpServers": {"mvp-mcp": {"command": executable.as_posix(), "args": []}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
