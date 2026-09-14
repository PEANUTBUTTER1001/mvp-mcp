"""현재 워크플로 지시 테스트."""

from __future__ import annotations

from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS


def test_workflow_uses_two_stage_adaptive_wizard_as_the_default_intake() -> None:
    """첫 인터뷰는 채팅 문답이 아닌 1·2차 적응형 native 질문 흐름으로 시작한다."""
    assert "`documentation_start_adaptive_wizard`" in WORKFLOW_INSTRUCTIONS
    assert '`phase="intake"`' in WORKFLOW_INSTRUCTIONS
    assert '`phase="design"`' in WORKFLOW_INSTRUCTIONS
    assert "`design_questions`" in WORKFLOW_INSTRUCTIONS
    assert "design_questions_json" not in WORKFLOW_INSTRUCTIONS
    assert "`single_select`" in WORKFLOW_INSTRUCTIONS
    assert "primary_surface" in WORKFLOW_INSTRUCTIONS
    assert "'제출했음'" in WORKFLOW_INSTRUCTIONS
    assert "candidate_root" in WORKFLOW_INSTRUCTIONS
    assert "documentation_update_candidate_requirements" in WORKFLOW_INSTRUCTIONS
    assert "documentation_update_candidate_architecture" in WORKFLOW_INSTRUCTIONS
    assert "documentation_update_candidate_delivery" in WORKFLOW_INSTRUCTIONS
    assert "documentation_record_candidate_test_run" in WORKFLOW_INSTRUCTIONS
    assert "documentation_record_candidate_release" in WORKFLOW_INSTRUCTIONS
    assert "documentation_package_status" in WORKFLOW_INSTRUCTIONS
    assert "documentation_validate_package" in WORKFLOW_INSTRUCTIONS
    assert "documentation_preview_package" in WORKFLOW_INSTRUCTIONS
    assert "safe_auto_apply" in WORKFLOW_INSTRUCTIONS
    assert "documentation_apply_package" in WORKFLOW_INSTRUCTIONS
    assert "증거 없는 PASS/RELEASED" in WORKFLOW_INSTRUCTIONS


def test_server_instructions_expose_adaptive_wizard_as_the_immediate_default() -> None:
    """Prompt를 호출하지 않아도 서버 초기 지시문이 기본 시작 도구를 명시한다."""
    assert "documentation_start_adaptive_wizard" in SERVER_INSTRUCTIONS
    assert "design_questions" in SERVER_INSTRUCTIONS
    assert "candidate_root" in SERVER_INSTRUCTIONS
    assert "documentation_update_candidate_requirements" in SERVER_INSTRUCTIONS
    assert "documentation_update_candidate_architecture" in SERVER_INSTRUCTIONS
    assert "documentation_update_candidate_delivery" in SERVER_INSTRUCTIONS
    assert "documentation_validate_package" in SERVER_INSTRUCTIONS
    assert "documentation_preview_package" in SERVER_INSTRUCTIONS
    assert "제출 확인이나 생성 승인을 요구" in SERVER_INSTRUCTIONS
    assert "턴을 종료하지 말고" in SERVER_INSTRUCTIONS
