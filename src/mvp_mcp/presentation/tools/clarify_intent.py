"""clarify_intent Tool 어댑터 (얇은 어댑터).

본격 명세 작성 이전의 **선행 단계**. 사용자가 아이디어를 제시하면 곧바로 결과물로
넘어가지 않고, 먼저 문제·목표·기대 산출물·제약을 문답으로 파악하도록 안내한다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.query import GetIntakeQuestionsUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_intake


def register_clarify_intent_tool(mcp: FastMCP, use_case: GetIntakeQuestionsUseCase) -> None:
    """의도 파악(discovery) Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def clarify_intent(user_request: str) -> str:
        """사용자가 아이디어/프로젝트를 처음 제시하면 **가장 먼저** 이 도구를 호출한다.

        결과물을 성급히 만들지 말고, 먼저 사용자의 진짜 문제·목표·기대 산출물·제약을
        문답으로 파악하기 위한 질문 세트를 돌려준다. 반환된 질문을 한 번에 하나씩 물어
        의도가 충분히 명확해진 뒤에야 start_spec 으로 본격 프로세스를 시작한다.
        """
        questions = use_case()
        return format_intake(user_request, questions)
