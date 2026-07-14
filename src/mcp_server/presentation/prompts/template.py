"""Prompt 어댑터 (도구 사용 진입점 안내).

MCP 클라이언트(예: Claude)에게 이 서버의 도구를 어떻게 쓰면 되는지 안내하는 표준
프롬프트를 배포한다. 산출물 품질을 좌우하는 지시는 대부분 이 파일에 모인다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """안내 Prompt 를 MCP 서버에 등록한다."""

    @mcp.prompt()
    def note_quickstart(topic: str) -> str:
        """``topic`` 에 대한 노트를 만드는 표준 절차 프롬프트."""
        return (
            f"'{topic}' 주제로 노트를 작성한다.\n\n"
            "1. 제목은 한 줄로 핵심을 담아 정한다.\n"
            "2. 본문은 요점을 불릿으로 3개 이상 정리한다.\n"
            "3. 작성이 끝나면 create_note 도구를 호출해 저장한다.\n"
            "   - title: 위에서 정한 제목\n"
            "   - body: 정리한 본문\n"
        )
