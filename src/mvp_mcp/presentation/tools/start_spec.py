"""start_spec Tool 어댑터 (얇은 어댑터).

입력 검증 → UseCase 호출 → 사람이 읽을 문자열 반환만. 실패 처리는 ``@safe_tool``.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.model import ProjectType, SpecRequest
from mvp_mcp.domain.spec.usecase import StartSpecUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._format import format_start


def register_start_spec_tool(mcp: FastMCP, use_case: StartSpecUseCase) -> None:
    """MVP 명세 세션 시작 Tool 을 등록한다."""

    @mcp.tool()
    @safe_tool
    def start_spec(
        user_request: str,
        project_type: str = "etc",
        known_info: dict[str, str] | None = None,
    ) -> str:
        """MVP 명세 세션을 시작한다. 유형 템플릿을 적용하고 부족한 정보의 질문을 돌려준다.

        **먼저 clarify_intent 로 의도(문제·목표·기대 산출물·제약)를 파악하라.** 의도가
        불명확한데 이 도구를 성급히 호출하지 마라. 파악된 값은 known_info 로 담아 넘긴다.

        요청 내용을 보고 project_type 을 아래에서 반드시 하나 고른다(유형마다 질문·출력
        형식이 다르므로 정확히 고르는 것이 중요):
        - "messenger" : 채팅/메신저 앱
        - "shopping_mall" : 쇼핑몰/이커머스
        - "blog" : 블로그/게시판
        - "mcp_server" : MCP 서버·도구, 개발자용 도구/플러그인/확장 (예: "~용 MCP 만들어줘")
        - "ml_project" : 머신러닝/AI 모델 학습·예측 프로젝트
        - "data_pipeline" : 데이터 수집·변환·적재(ETL) 파이프라인
        - "etc" : 위 어디에도 맞지 않을 때만 (되도록 위 구체 유형을 우선한다)

        요청에 "MCP" 나 "MCP 서버" 가 있으면 "etc" 가 아니라 "mcp_server" 를 쓴다.
        지원하지 않는 값이나 생략 시 자동으로 "etc" 로 처리된다.
        """
        request = SpecRequest(
            project_type=ProjectType.coerce(project_type),
            user_request=user_request,
            known_info=known_info or {},
        )
        draft, questions = use_case(request)
        return format_start(draft, questions)
