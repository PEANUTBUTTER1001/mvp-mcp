"""Codex가 지원하는 MCP Elicitation 폼으로 질문을 표시하는 Tool."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field, create_model

from mvp_mcp.domain.spec.model import Question
from mvp_mcp.presentation._safe import safe_async_tool


def _form_schema(question: Question) -> type[BaseModel]:
    """선택지 enum과 기타 상세 입력을 가진 평면 Elicitation 스키마를 만든다."""
    choices = list(question.options)
    if question.allows_other and "기타" not in choices:
        choices.append("기타")
    schema_extra: dict[str, Any] | None = {"enum": choices} if choices else None
    answer_field = Field(
        description="선택한 답변 또는 자유 입력 답변",
        json_schema_extra=schema_extra,
    )
    return create_model(
        "QuestionForm",
        answer=(str, answer_field),
    )


def _answer_value(question: Question, data: Any, other_detail: str = "") -> str:
    """Elicitation 폼 응답을 기존 답변 값 계약으로 변환한다."""
    answer = str(data.answer).strip()
    if answer == "기타":
        detail = other_detail.strip()
        if not question.allows_other or not detail:
            raise ValueError("기타를 선택하면 상세 내용을 입력해야 합니다.")
        return f"기타: {detail}"
    if question.options and answer not in question.options:
        raise ValueError("제시된 선택지 중 하나를 골라주세요.")
    if not answer:
        raise ValueError("답변을 입력해주세요.")
    return answer


def register_ask_elicitation_question_tool(mcp: FastMCP) -> None:
    """MCP form Elicitation 기반 질문 Tool 을 등록한다."""

    @mcp.tool()
    @safe_async_tool
    async def ask_elicitation_question(
        field: str,
        text: str,
        ctx: Context[Any, Any, Any],
        options: list[str] | None = None,
        description: str = "",
        hint: str = "",
        allows_other: bool = False,
    ) -> str:
        """Codex 내부 선택창을 우선 요청한다.

        클라이언트가 MCP form Elicitation을 지원하지 않으면 실패 메시지를 반환한다. 그때만
        `ask_web_question` 또는 `ask_next_web_question`으로 웹 Wizard를 사용한다.
        """
        question = Question(
            field=field,
            text=text,
            options=options or [],
            description=description,
            hint=hint,
            allows_other=allows_other,
        )
        message = question.text
        if question.description:
            message = f"{message}\n\n{question.description}"
        if question.hint:
            message = f"{message}\n\n힌트: {question.hint}"
        result = await ctx.elicit(message=message, schema=_form_schema(question))
        if result.action != "accept":
            return (
                "사용자가 질문 입력을 취소했습니다. 웹 Wizard 또는 채팅 방식으로 다시 물어보세요."
            )
        other_detail = ""
        if str(result.data.model_dump()["answer"]).strip() == "기타":
            detail_result = await ctx.elicit(
                message="기타를 선택했습니다. 원하시는 형태와 핵심 요구사항을 입력해주세요.",
                schema=create_model(
                    "OtherDetailForm",
                    detail=(str, Field(description="기타 선택의 상세 내용")),
                ),
            )
            if detail_result.action != "accept":
                return "기타 상세 입력이 취소되었습니다. 다시 질문해 주세요."
            other_detail = str(detail_result.data.model_dump()["detail"])
        value = _answer_value(question, result.data, other_detail)
        return f"Codex 선택창에서 받은 답변: {field}={value}"
