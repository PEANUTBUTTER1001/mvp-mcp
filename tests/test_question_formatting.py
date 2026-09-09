"""채팅형 질문·선택지 표시와 워크플로 지시 테스트."""

from __future__ import annotations

from mvp_mcp.domain.spec.model import Question
from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS
from mvp_mcp.presentation.tools._format import format_next_question


def test_choice_question_uses_bold_markdown_numbered_list() -> None:
    """선택지는 일반 채팅에서 바로 보일 Markdown 목록으로 렌더링한다."""
    question = Question(
        field="deliverable",
        text="어떤 형태의 결과물을 기대하나요?",
        options=["앱/웹 서비스", "개발 도구/MCP", "데이터/ML", "기타"],
    )

    result = format_next_question([question])

    assert "1. **앱/웹 서비스**" in result
    assert "4. **기타**" in result
    assert "번호 또는 선택지 이름으로 답해주세요." in result
    assert "보기:" not in result
    assert "1)" not in result


def test_free_text_question_has_input_guidance() -> None:
    """선택지가 없는 질문도 일반 채팅 입력창으로 답하도록 안내한다."""
    result = format_next_question([Question(field="goal", text="목표는 무엇인가요?")])

    assert "자유롭게 답변해주세요." in result


def test_workflow_uses_single_web_survey_as_the_default_intake() -> None:
    """첫 인터뷰는 UI 선택·개별 문답 대신 단일 웹 설문으로 시작한다."""
    assert "`ask_web_survey(user_request, project_root)`" in WORKFLOW_INSTRUCTIONS
    assert "UI 선택을 묻지 말고" in WORKFLOW_INSTRUCTIONS
    assert "추가 질문도 하지 마라" in WORKFLOW_INSTRUCTIONS
    assert "register_delivery_contract" in WORKFLOW_INSTRUCTIONS
    assert "같은 호출에서 `spec_id`를 반환" in WORKFLOW_INSTRUCTIONS
    assert "`resume_web_survey`나 `get_web_survey_status`를 호출하지 말고" in WORKFLOW_INSTRUCTIONS
    assert "일반 채팅에서 별도 승인 답변을 기다리지 마라" in WORKFLOW_INSTRUCTIONS
    assert "웹 설문의 마지막 제출은 이 MVP 범위와 6문서 생성을 승인" in WORKFLOW_INSTRUCTIONS
    assert "export_mvp_bundle" in WORKFLOW_INSTRUCTIONS


def test_server_instructions_expose_web_survey_as_the_immediate_default() -> None:
    """Prompt를 호출하지 않아도 서버 초기 지시문이 기본 시작 도구를 명시한다."""
    assert "ask_web_survey(user_request, project_root)를 즉시 호출" in SERVER_INSTRUCTIONS
    assert "start_spec, clarify_intent, answer_question" in SERVER_INSTRUCTIONS
