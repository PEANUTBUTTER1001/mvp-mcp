"""FastMCP 서버 엔트리포인트 및 Composition Root.

모든 의존성 와이어링(인터페이스 → 구현체)은 오직 이 모듈에서만 수행한다.
UseCase 와 Presentation 어댑터는 구현체를 알지 못한다. 새 도구를 추가할 때는
아래 세 단계(구현체 생성 → UseCase 주입 → register_* 등록)를 그대로 따른다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.core.config import Settings
from mcp_server.core.logging import configure_logging
from mcp_server.data.note.repository_impl import InMemoryNoteRepository
from mcp_server.data.system_clock import SystemClock
from mcp_server.domain.note.query import (
    GetNoteUseCase,
    ListNotesUseCase,
    SearchNoteUseCase,
)
from mcp_server.domain.note.usecase import CreateNoteUseCase
from mcp_server.presentation.prompts.template import register_prompts
from mcp_server.presentation.resources.notes import register_resources
from mcp_server.presentation.tools.create_note import register_create_note_tool
from mcp_server.presentation.tools.search_note import register_search_note_tool


def build() -> FastMCP:
    """설정을 읽어 구현체를 조립하고 등록을 마친 FastMCP 서버를 반환한다."""
    configure_logging()  # stderr 로깅 1회 구성(stdout 은 프로토콜 전용).
    _cfg = Settings()  # 부팅 시 설정 검증(fail-fast). 새 구현체에 전달해 쓴다.

    # 1. 구현체 생성 (data 계층)
    repository = InMemoryNoteRepository()
    clock = SystemClock()

    # 2. UseCase 에 구현체 주입 (domain 계층)
    create_use_case = CreateNoteUseCase(repository=repository, clock=clock)
    search_use_case = SearchNoteUseCase(repository)
    list_use_case = ListNotesUseCase(repository)
    get_use_case = GetNoteUseCase(repository)

    # 3. 어댑터 등록 (presentation 계층)
    mcp = FastMCP("MCPServer")
    register_prompts(mcp)
    register_create_note_tool(mcp, create_use_case)
    register_search_note_tool(mcp, search_use_case)
    register_resources(mcp, list_use_case, get_use_case)
    return mcp


def main() -> None:
    """콘솔 스크립트 진입점. 기본 stdio 전송으로 서버를 실행한다."""
    build().run()


if __name__ == "__main__":
    main()
