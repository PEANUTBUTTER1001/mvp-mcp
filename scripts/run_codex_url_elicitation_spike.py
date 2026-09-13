"""Codex URL elicitation completion/retry capability를 독립 MCP 서버로 측정한다.

이 스크립트는 현재 제품 MCP Tool 목록에 등록하지 않는다. 단계 1 판정에만 사용하고,
`continuation_received`가 실제 Codex client에서 관찰되기 전에는 제품 workflow를 전환하지 않는다.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mvp_mcp.data.spec.sqlite_continuation_probe_repository import (
    SqliteContinuationProbeRepository,
)
from mvp_mcp.data.system_clock import SystemClock
from mvp_mcp.domain.spec.continuation_probe_usecase import (
    CompleteContinuationProbeUseCase,
    ReceiveContinuationProbeUseCase,
    StartContinuationProbeUseCase,
)
from mvp_mcp.presentation.tools.continuation_probe import register_continuation_probe_tool
from mvp_mcp.presentation.web.continuation_probe_form import LocalContinuationProbeForm
from mvp_mcp.presentation.web.continuation_probe_notifier import ContinuationProbeNotifier


def build(state_path: Path) -> tuple[FastMCP, LocalContinuationProbeForm]:
    """spike 전용 의존성을 조립한다."""
    probes = SqliteContinuationProbeRepository(state_path)
    clock = SystemClock()
    start = StartContinuationProbeUseCase(probes, clock)
    complete = CompleteContinuationProbeUseCase(probes, clock)
    receive = ReceiveContinuationProbeUseCase(probes, clock)
    notifier = ContinuationProbeNotifier()

    def on_submit(probe_id: str) -> None:
        complete(probe_id)
        notifier.notify_completed(probe_id)

    form = LocalContinuationProbeForm(on_submit)
    mcp = FastMCP("mvp_capability_probe")
    register_continuation_probe_tool(mcp, start, receive, form, notifier)
    return mcp, form


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path(tempfile.gettempdir()) / "mvp-mcp-continuation-probe.sqlite3",
        help="재시작 뒤 상태를 유지할 SQLite 파일 경로",
    )
    args = parser.parse_args()
    mcp, form = build(args.state_path)
    try:
        mcp.run()
    finally:
        form.close()


if __name__ == "__main__":
    main()
