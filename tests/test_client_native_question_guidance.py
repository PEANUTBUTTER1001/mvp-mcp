"""클라이언트별 native 질문 안내가 공통 Wizard 계약을 유지하는지 검증한다."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CLAUDE_SKILL = "integrations/claude/plugin/skills/mvpmcp/SKILL.md"


def test_native_question_guidance_keeps_choice_other_and_batch_contracts() -> None:
    integrations = {
        "integrations/codex/SKILL.md": "request_user_input",
        _CLAUDE_SKILL: "AskUserQuestion",
        "integrations/gemini/GEMINI.md": "ask_user",
        "integrations/antigravity/SKILL.md": "ask_question",
    }
    required_contracts = (
        "visible_when",
        "max_selections",
        "allow_other=true",
        "기타 자유 입력",
        '"other_text"',
        "documentation_submit_adaptive_wizard_answers",
        "선택지 2~4개",
        "maintenance_kind",
    )
    # Claude Code AskUserQuestion은 한 번에 4문항·선택지 4개라 서버 선택지를 그대로 넣는다.
    # 한도를 조사하지 않은 다른 호스트는 기존 3개 묶음·다음 선택지 규칙을 유지한다.
    host_specific = {
        _CLAUDE_SKILL: ("최대 4문항", "1:1", "4개씩 나눈"),
    }
    paged = ("1~3개씩", "다음 선택지")

    for relative, native_tool in integrations.items():
        content = (_ROOT / relative).read_text(encoding="utf-8")
        assert native_tool in content, f"native 질문 도구 안내 누락: {relative}"
        assert "ui://" not in content, f"제거된 MCP 앱 안내가 남음: {relative}"
        for required in required_contracts + host_specific.get(relative, paged):
            assert required in content, f"{required} 안내 누락: {relative}"


def test_codex_guidance_requires_plan_before_starting_a_run() -> None:
    content = (_ROOT / "integrations/codex/SKILL.md").read_text(encoding="utf-8")

    assert "/plan" in content
    assert "Wizard Run을 만들지 말고" in content
    assert "스킬은 모드를 전환할 수 없다" in content


def test_default_document_save_guidance_separates_product_code_implementation() -> None:
    integrations = {
        "integrations/codex/SKILL.md": "request_user_input",
        _CLAUDE_SKILL: "AskUserQuestion",
        "integrations/gemini/GEMINI.md": "ask_user",
        "integrations/antigravity/SKILL.md": "ask_question",
    }
    required_contracts = (
        "safe_auto_apply",
        ".mvpmcp/<spec_id>/",
        "문서 패키지 저장 완료 (.mvpmcp에 문서만 생성됨)",
        "제품 코드 구현 여부를 자동으로 묻지 않는다",
        "MVP 제품 코드 구현 시작",
        "문서 후보 저장 완료 (코드 구현 없음)",
    )

    for relative, native_tool in integrations.items():
        content = (_ROOT / relative).read_text(encoding="utf-8")
        assert native_tool in content, f"후속 의도 확인 도구 안내 누락: {relative}"
        for required in required_contracts:
            assert required in content, f"{required} 안내 누락: {relative}"

    codex = (_ROOT / "integrations/codex/SKILL.md").read_text(encoding="utf-8")
    assert "PLEASE IMPLEMENT THIS PLAN" in codex


def test_candidate_save_guidance_uses_server_tool_and_exact_retries() -> None:
    for relative in (
        "integrations/codex/SKILL.md",
        _CLAUDE_SKILL,
        "integrations/gemini/GEMINI.md",
        "integrations/antigravity/SKILL.md",
    ):
        content = (_ROOT / relative).read_text(encoding="utf-8")
        for contract in (
            "documentation_write_candidate_file",
            "expected_file_sha256",
            "candidate_files",
            "idempotency_key",
            "pending_candidate_write",
            "원래 모든 입력과 같은 key",
            "셸 권한 상승은 사용하지 않는다",
            "status → validate → preview",
        ):
            assert contract in content, f"후보 저장 계약 누락: {relative}: {contract}"


def test_client_guidance_leaves_prototype_to_separate_skill() -> None:
    from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS

    integrations = (
        "integrations/codex/SKILL.md",
        _CLAUDE_SKILL,
        "integrations/gemini/GEMINI.md",
        "integrations/antigravity/SKILL.md",
    )
    for relative in integrations:
        content = (_ROOT / relative).read_text(encoding="utf-8")
        for required in (
            "문서 반영 후 별도 스킬",
            "시제품에 관여하지 않는다",
            "`prototype/index.html`을 만들지 않고",
            "`docs/*.md`를 방안 삼아",
            "명시적으로 실행할 때만",
        ):
            assert required in content, f"{required} 안내 누락: {relative}"
        for removed in (
            "prototype_brief",
            "skill_guide",
            "시제품 없이 진행",
            "시제품이 먼저다",
            "prototype_visual_check",
            "design_color_choice",
            "design_visual_tone",
            "design_web_behavior",
            "mvpdesign_instruction",
            "1~10절은 제품별 핵심 표준",
        ):
            assert removed not in content, f"이전 디자인 안내가 남음: {relative}: {removed}"
    claude = (_ROOT / _CLAUDE_SKILL).read_text(encoding="utf-8")
    assert "`/mvpmcp:mvpmcpprototype`" in claude
    for text in (SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS):
        assert "prototype_brief" not in text
        assert "prototype_visual_check" not in text
        assert "/mvpmcp:mvpmcpprototype" in text
        assert "시제품" in text


def test_client_guidance_skips_questions_fixed_by_request() -> None:
    from mvp_mcp.presentation.prompts.workflow import SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS

    integrations = (
        "integrations/codex/SKILL.md",
        _CLAUDE_SKILL,
        "integrations/gemini/GEMINI.md",
        "integrations/antigravity/SKILL.md",
    )
    for relative in integrations:
        content = (_ROOT / relative).read_text(encoding="utf-8")
        for required in ("명시된 사실만", "from_request=true", "prefilled_summary", "other_text"):
            assert required in content, f"{required} 안내 누락: {relative}"
        assert "선택지 값만, 예" not in content, f"구 미리 채우기 안내가 남음: {relative}"
    for text in (SERVER_INSTRUCTIONS, WORKFLOW_INSTRUCTIONS):
        assert "from_request=true" in text
        assert "prefilled_summary" in text
