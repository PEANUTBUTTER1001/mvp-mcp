"""answer_question Tool 어댑터 (얇은 어댑터)."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.usecase import AnswerQuestionUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_next_question


def register_answer_question_tool(mcp: FastMCP, use_case: AnswerQuestionUseCase) -> None:
    """질문 답변 반영 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def answer_question(spec_id: str, field: str, value: str) -> str:
        """사용자의 답 하나를 명세 초안에 반영하고 남은 질문을 돌려준다."""
        _draft, remaining = use_case(spec_id, field, value)
        return f"반영됨: {field}={value}\n\n{format_next_question(remaining)}"
