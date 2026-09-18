"""클라이언트별 native 질문 안내가 공통 Wizard 계약을 유지하는지 검증한다."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_native_question_guidance_keeps_choice_other_and_batch_contracts() -> None:
    integrations = {
        "integrations/codex/SKILL.md": "request_user_input",
        "integrations/claude/SKILL.md": "AskUserQuestion",
        "integrations/gemini/GEMINI.md": "ask_user",
        "integrations/antigravity/SKILL.md": "ask_question",
    }
    required_contracts = (
        "1~3개씩",
        "visible_when",
        "max_selections",
        "allow_other=true",
        "기타 자유 입력",
        '"other_text"',
        "다음 선택지",
        "documentation_submit_adaptive_wizard_answers",
    )

    for relative, native_tool in integrations.items():
        content = (_ROOT / relative).read_text(encoding="utf-8")
        assert native_tool in content, f"native 질문 도구 안내 누락: {relative}"
        for required in required_contracts:
            assert required in content, f"{required} 안내 누락: {relative}"


def test_codex_guidance_requires_plan_before_starting_a_run() -> None:
    content = (_ROOT / "integrations/codex/SKILL.md").read_text(encoding="utf-8")

    assert "/plan" in content
    assert "Wizard Run을 만들지 말고" in content
    assert "스킬은 모드를 전환할 수 없다" in content


def test_default_document_save_guidance_separates_product_code_implementation() -> None:
    integrations = {
        "integrations/codex/SKILL.md": "request_user_input",
        "integrations/claude/SKILL.md": "AskUserQuestion",
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


def test_client_guidance_keeps_multi_platform_design_quality_contract() -> None:
    integrations = (
        "integrations/codex/SKILL.md",
        "integrations/claude/SKILL.md",
        "integrations/gemini/GEMINI.md",
        "integrations/antigravity/SKILL.md",
    )
    required_contracts = (
        "1~10절은 제품별 핵심 표준",
        "11~14절은 token·상태·검증 보조 계약",
        "platform_targets",
        "cross_platform",
        "직접 Hex·임의 여백·`style=` 속성",
        "375px·768px·1440px",
        "오류 대상 연결",
        "NOT RUN",
        "palette_source.brand_seed",
        "oklch-v1",
        "4.5:1",
        "7:1",
        "대비 검증",
    )

    for relative in integrations:
        content = (_ROOT / relative).read_text(encoding="utf-8")
        for required in required_contracts:
            assert required in content, f"{required} 안내 누락: {relative}"
