"""클론한 mvp-mcp 저장소를 Claude Code·Codex·Antigravity에 설치한다(다시 실행하면 갱신).

사용: uv run scripts/install.py [--host claude|codex|antigravity] [--dry-run] [--no-server]

- 서버: 각 서비스 설정에 `uv --directory <저장소> run mvp-mcp`를 등록한다(이미 있으면 건너뜀).
- 스킬: Claude Code는 저장소 플러그인(mvpmcp@mvpmcp-local), Codex·Antigravity는 스킬 폴더에
  복사한다.
- 설정 파일은 고치기 전에 `<파일>.bak-<시각>`으로 백업하며, 항목을 추가만 하고 지우지 않는다.

MCP 서버 프로세스가 아닌 별도 설치 도구이므로 결과는 표준출력으로 보고한다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SERVER_NAME = "mvp-mcp"
MARKETPLACE = "mvpmcp-local"
PLUGIN = "mvpmcp@mvpmcp-local"
HOSTS = ("claude", "codex", "antigravity")
REPOSITORY = Path(__file__).resolve().parents[1]

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]
Which = Callable[[str], "str | None"]


def run_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        return subprocess.CompletedProcess(list(args), 127, "", str(error))


def find_command(name: str) -> str | None:
    """Windows에서는 npm이 함께 두는 확장자 없는 셸 스크립트 대신 .exe/.cmd를 고른다."""

    if os.name == "nt":
        for suffix in (".exe", ".cmd", ".bat"):
            if found := shutil.which(name + suffix):
                return found
    return shutil.which(name)


@dataclass
class Report:
    lines: list[str] = field(default_factory=list)
    failed: bool = False

    def add(self, host: str, item: str, status: str) -> None:
        self.lines.append(f"[{host}] {item}: {status}")

    def fail(self, host: str, item: str, reason: str) -> None:
        self.failed = True
        self.add(host, item, f"실패({reason})")


@dataclass(frozen=True)
class Context:
    repository: Path
    home: Path
    desktop_config_dirs: tuple[Path, ...]
    dry_run: bool
    server: bool
    runner: Runner
    claude_bin: str | None
    stamp: str

    @property
    def server_args(self) -> list[str]:
        return ["--directory", self.repository.as_posix(), "run", SERVER_NAME]

    def skill_sources(self, host: str) -> dict[str, Path]:
        integrations = self.repository / "integrations"
        prototype = integrations / "claude" / "plugin" / "skills" / "mvpmcpprototype" / "SKILL.md"
        return {"mvpmcp": integrations / host / "SKILL.md", "mvpmcpprototype": prototype}


def default_desktop_config_dirs(home: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    if appdata := os.environ.get("APPDATA"):
        candidates.append(Path(appdata) / "Claude")
    if local := os.environ.get("LOCALAPPDATA"):
        candidates.extend(sorted(Path(local).glob("Claude-Data/*")))
    candidates.append(home / "Library" / "Application Support" / "Claude")
    candidates.append(home / ".config" / "Claude")
    return tuple(candidates)


def _desktop_has_server(ctx: Context) -> bool:
    for directory in ctx.desktop_config_dirs:
        path = directory / "claude_desktop_config.json"
        try:
            servers = json.loads(_read(path) or "{}").get("mcpServers", {})
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(servers, dict) and any(
            SERVER_NAME in f"{name} {json.dumps(spec)}" for name, spec in servers.items()
        ):
            return True
    return False


def _read(path: Path) -> str:
    """BOM이 붙은 설정 파일(Windows 편집기)도 그대로 읽는다. 없으면 빈 문자열."""

    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def _backup(path: Path, stamp: str) -> None:
    target = path.with_name(f"{path.name}.bak-{stamp}")
    if target.exists():
        raise FileExistsError(f"백업 파일이 이미 있습니다: {target.name}")
    shutil.copy2(path, target)


def _write(ctx: Context, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _backup(path, ctx.stamp)
    path.write_text(text, encoding="utf-8", newline="\n")


def _copy_skills(ctx: Context, report: Report, host: str, skills_dir: Path) -> None:
    for name, source in ctx.skill_sources(host).items():
        target = skills_dir / name / "SKILL.md"
        content = source.read_text(encoding="utf-8")
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            report.add(host, f"스킬 {name}", "건너뜀(최신)")
            continue
        status = "갱신함" if target.exists() else "복사함"
        if ctx.dry_run:
            report.add(host, f"스킬 {name}", f"{status} 예정 → {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        report.add(host, f"스킬 {name}", f"{status} → {target}")


def _change(ctx: Context, report: Report, host: str, item: str, args: list[str], done: str) -> None:
    shown = " ".join([Path(args[0]).stem, *args[1:]])
    if ctx.dry_run:
        report.add(host, item, f"{done} 예정: {shown}")
        return
    result = ctx.runner(args)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        report.fail(host, item, detail[-1] if detail else f"종료 코드 {result.returncode}")
        return
    report.add(host, item, done)


def install_claude(ctx: Context, report: Report) -> None:
    claude = ctx.claude_bin
    if claude is None:
        report.fail("claude", "감지", "claude 명령을 찾을 수 없습니다")
        return
    if ctx.server:
        if _desktop_has_server(ctx):
            report.add("claude", "서버", "건너뜀(Claude 데스크톱 설정에 이미 등록)")
        elif ctx.runner([claude, "mcp", "get", SERVER_NAME]).returncode == 0:
            report.add("claude", "서버", "건너뜀(이미 등록)")
        else:
            add = [claude, "mcp", "add", SERVER_NAME, "-s", "user", "--", "uv", *ctx.server_args]
            _change(ctx, report, "claude", "서버", add, "등록함")
    marketplaces = ctx.runner([claude, "plugin", "marketplace", "list"]).stdout or ""
    if MARKETPLACE in marketplaces:
        report.add("claude", "마켓", "건너뜀(이미 등록)")
    else:
        add = [claude, "plugin", "marketplace", "add", ctx.repository.as_posix()]
        _change(ctx, report, "claude", "마켓", add, "등록함")
    plugins = ctx.runner([claude, "plugin", "list"]).stdout or ""
    action = "update" if PLUGIN in plugins else "install"
    done = "갱신함" if action == "update" else "설치함"
    _change(ctx, report, "claude", "플러그인", [claude, "plugin", action, PLUGIN], done)


def install_codex(ctx: Context, report: Report) -> None:
    codex = ctx.home / ".codex"
    if ctx.server:
        config = codex / "config.toml"
        try:
            text = _read(config)
            servers = tomllib.loads(text).get("mcp_servers", {})
        except (OSError, tomllib.TOMLDecodeError):
            report.fail("codex", "서버", f"{config} 파일 손상 의심, 수정하지 않음")
        else:
            if SERVER_NAME in servers:
                report.add("codex", "서버", "건너뜀(이미 등록)")
            elif ctx.dry_run:
                report.add("codex", "서버", f"등록함 예정 → {config}")
            else:
                block = (
                    f"[mcp_servers.{SERVER_NAME}]\n"
                    f'command = "uv"\n'
                    f"args = {json.dumps(ctx.server_args, ensure_ascii=False)}\n"
                )
                separator = "\n" if text and not text.endswith("\n") else ""
                gap = "\n" if text else ""
                try:
                    _write(ctx, config, f"{text}{separator}{gap}{block}")
                except OSError as error:
                    report.fail("codex", "서버", str(error))
                else:
                    report.add("codex", "서버", f"등록함 → {config}")
    _copy_skills(ctx, report, "codex", codex / "skills")


def _antigravity_config(home: Path) -> Path:
    candidates = [
        home / ".gemini" / "config" / "mcp_config.json",
        home / ".gemini" / "antigravity" / "mcp_config.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return next((path for path in candidates if path.parent.is_dir()), candidates[0])


def install_antigravity(ctx: Context, report: Report) -> None:
    if ctx.server:
        config = _antigravity_config(ctx.home)
        try:
            # 빈 파일(Antigravity가 미리 만들어 두는 경우)은 빈 설정으로 본다.
            data = json.loads(_read(config).strip() or "{}")
            servers = data.setdefault("mcpServers", {})
            if not isinstance(data, dict) or not isinstance(servers, dict):
                raise ValueError
        except (OSError, ValueError, AttributeError):
            report.fail("antigravity", "서버", f"{config} 파일 손상 의심, 수정하지 않음")
        else:
            if SERVER_NAME in servers:
                report.add("antigravity", "서버", "건너뜀(이미 등록)")
            elif ctx.dry_run:
                report.add("antigravity", "서버", f"등록함 예정 → {config}")
            else:
                servers[SERVER_NAME] = {"command": "uv", "args": ctx.server_args}
                text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                try:
                    _write(ctx, config, text)
                except OSError as error:
                    report.fail("antigravity", "서버", str(error))
                else:
                    report.add("antigravity", "서버", f"등록함 → {config}")
    # 스킬 폴더는 MCP 설정 파일과 같은 폴더의 skills/(예: ~/.gemini/config/skills)다.
    skills = _antigravity_config(ctx.home).parent / "skills"
    _copy_skills(ctx, report, "antigravity", skills)


INSTALLERS: dict[str, Callable[[Context, Report], None]] = {
    "claude": install_claude,
    "codex": install_codex,
    "antigravity": install_antigravity,
}
USAGE = {
    "claude": "새 세션에서 /mvpmcp:mvpmcp <아이디어> → 문서 반영 뒤 /mvpmcp:mvpmcpprototype",
    "codex": "mvpmcp 스킬로 문서 생성 → 문서 반영 뒤 mvpmcpprototype 스킬",
    "antigravity": "/skills에서 mvpmcp·mvpmcpprototype 확인 → mvpmcp로 문서 생성 → mvpmcpprototype",
}


def detect_hosts(home: Path, which: Which) -> list[str]:
    found = []
    if which("claude"):
        found.append("claude")
    if (home / ".codex").is_dir() or which("codex"):
        found.append("codex")
    gemini = home / ".gemini"
    if (gemini / "antigravity").is_dir() or (gemini / "config").is_dir():
        found.append("antigravity")
    return found


def main(
    argv: Sequence[str] | None = None,
    runner: Runner = run_command,
    which: Which = find_command,
) -> int:
    parser = argparse.ArgumentParser(description="mvp-mcp 서버와 스킬을 설치·갱신한다.")
    parser.add_argument("--host", action="append", choices=HOSTS, help="대상 서비스(여러 번 지정)")
    parser.add_argument("--dry-run", action="store_true", help="바꿀 내용만 보여 준다")
    parser.add_argument("--no-server", action="store_true", help="서버 등록 없이 스킬만 설치")
    parser.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--claude-config-dir", type=Path, action="append", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    home = (args.home or Path.home()).resolve()
    if not which("uv"):
        sys.stdout.write(
            "uv를 찾을 수 없습니다. https://docs.astral.sh/uv/ 에서 설치한 뒤 다시 실행하세요.\n"
        )
        return 1
    hosts = args.host or detect_hosts(home, which)
    if not hosts:
        sys.stdout.write(
            "Claude Code·Codex·Antigravity를 찾지 못했습니다. --host로 지정해 다시 실행하세요.\n"
        )
        return 1

    ctx = Context(
        repository=REPOSITORY,
        home=home,
        desktop_config_dirs=tuple(args.claude_config_dir or default_desktop_config_dirs(home)),
        dry_run=args.dry_run,
        server=not args.no_server,
        runner=runner,
        claude_bin=which("claude"),
        stamp=datetime.now().strftime("%Y%m%d%H%M%S"),
    )
    report = Report()
    for host in dict.fromkeys(hosts):
        INSTALLERS[host](ctx, report)

    title = "설치 미리보기(--dry-run, 바뀐 것 없음)" if ctx.dry_run else "설치 결과"
    lines = [f"mvp-mcp {title} — 저장소 {REPOSITORY.as_posix()}", *report.lines, ""]
    if not ctx.dry_run:
        lines.append("사용 중인 앱(Claude·Codex·Antigravity)을 재시작해야 반영됩니다.")
    lines.extend(f"- {host}: {USAGE[host]}" for host in dict.fromkeys(hosts))
    sys.stdout.write("\n".join(lines) + "\n")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
