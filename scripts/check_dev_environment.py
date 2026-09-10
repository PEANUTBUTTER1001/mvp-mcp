"""개발·MCP·브라우저 테스트 선행 도구를 변경 없이 점검한다."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def _probe(name: str, command: list[str], required: bool = True) -> dict[str, object]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"name": name, "status": "MISSING", "required": required}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        return {
            "name": name,
            "status": "FAILED",
            "required": required,
            "reason": str(exc),
        }
    return {
        "name": name,
        "status": "READY" if result.returncode == 0 else "FAILED",
        "required": required,
        "command": command,
        "returncode": result.returncode,
        "version": (result.stdout or result.stderr).splitlines()[:1],
    }


def _chromium_probe() -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:
        return {"name": "chromium-launch", "status": "FAILED", "required": True, "reason": str(exc)}
    return {"name": "chromium-launch", "status": "READY", "required": True}


def main() -> int:
    probes = [
        {"name": "python", "status": "READY", "required": True, "version": sys.version},
        _probe("uv", ["uv", "--version"]),
        _probe("node", ["node", "--version"], required=False),
        _probe("npx", ["npx", "--version"], required=False),
        _probe("mcp-cli", ["mcp", "--help"]),
        _probe("playwright", ["playwright", "--version"], required=False),
        _chromium_probe(),
    ]
    print(json.dumps(probes, ensure_ascii=False, indent=2))
    return int(any(item["required"] and item["status"] != "READY" for item in probes))


if __name__ == "__main__":
    raise SystemExit(main())
