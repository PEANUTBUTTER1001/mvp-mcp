"""네이티브 질문 UI를 지원하지 않는 클라이언트용 웹 질문 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import AskNextWebQuestionUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_next_question


def register_ask_next_web_question_tool(mcp: FastMCP, use_case: AskNextWebQuestionUseCase) -> None:
    """로컬 웹 질문 화면을 열고 확정된 답변을 초안에 반영하는 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def ask_next_web_question(spec_id: str) -> str:
        """다음 질문을 브라우저에 표시한다.

        클라이언트에 네이티브 선택 UI가 없을 때만 사용한다. 이 호출은 사용자가 웹 화면에서
        답을 확정할 때까지 대기하며, 완료되면 답을 반영한 다음 질문을 돌려준다.
        """
        _draft, next_questions, answer = use_case(spec_id)
        return f"웹 화면에서 반영됨: {answer.value}\n\n{format_next_question(next_questions)}"
