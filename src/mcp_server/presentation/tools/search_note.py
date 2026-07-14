"""노트 검색 Tool 어댑터 (얇은 어댑터).

제목 부분일치로 노트를 검색한다. 비즈니스 로직 없이 UseCase 로 위임하고, 사람이 읽기
쉬운 결과 문자열만 반환한다. 실패 처리는 ``@safe_tool`` 이 일괄 담당한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.domain.note.query import SearchNoteUseCase
from mcp_server.presentation._safe import safe_tool


def register_search_note_tool(mcp: FastMCP, use_case: SearchNoteUseCase) -> None:
    """노트 검색 Tool 을 MCP 서버에 등록한다."""

    @mcp.tool()
    @safe_tool
    def search_note(query: str) -> str:
        """제목에 검색어가 포함된 노트를 최신순으로 찾는다."""
        results = use_case(query)
        if not results:
            return f"'{query}' 와(과) 일치하는 노트가 없습니다."
        lines = [f"'{query}' 검색 결과 {len(results)}건:"]
        lines += [f"- [{n.id}] {n.title}" for n in results]
        return "\n".join(lines)
