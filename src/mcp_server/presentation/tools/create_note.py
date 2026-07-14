"""노트 생성 Tool 어댑터 (얇은 어댑터).

입력 검증 → UseCase 호출 → 사람이 읽기 쉬운 결과 문자열 반환만 담당한다.
비즈니스 로직은 두지 않는다. 실패 처리는 ``@safe_tool`` 이 일괄 담당한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.domain.note.model import NoteRequest
from mcp_server.domain.note.usecase import CreateNoteUseCase
from mcp_server.presentation._safe import safe_tool


def register_create_note_tool(mcp: FastMCP, use_case: CreateNoteUseCase) -> None:
    """노트 생성 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    @safe_tool
    def create_note(title: str, body: str = "") -> str:
        """제목과 본문으로 노트를 생성해 저장한다."""
        note = use_case(NoteRequest(title=title, body=body))
        return f"노트 생성 완료 → id={note.id}, hash={note.content_hash}"
