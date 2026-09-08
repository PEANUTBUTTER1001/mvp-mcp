"""초안 생성 전 discovery 단계에서 쓰는 범용 웹 질문 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.model import Question
from mvp_mcp.domain.spec.usecase import AskWebQuestionUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_ask_web_question_tool(mcp: FastMCP, use_case: AskWebQuestionUseCase) -> None:
    """한 질문을 로컬 웹 UI로 받고 답변을 반환하는 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def ask_web_question(
        field: str,
        text: str,
        options: list[str] | None = None,
        description: str = "",
        hint: str = "",
        allows_other: bool = False,
    ) -> str:
        """네이티브 질문 UI가 없을 때 discovery 질문 하나를 웹 화면에 표시한다."""
        question = Question(
            field=field,
            text=text,
            options=options or [],
            description=description,
            hint=hint,
            allows_other=allows_other,
        )
        answer = use_case(question)
        return f"웹 화면에서 받은 답변: {field}={answer.value}"
