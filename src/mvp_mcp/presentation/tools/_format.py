"""Tool 어댑터 공용 문자열 포매팅 헬퍼.

도메인 객체를 사람이 읽을 문자열로 바꾸는 순수 표현 로직만 둔다(비즈니스 로직 금지).
"""

from __future__ import annotations

from mvp_mcp.domain.spec.model import Question, SpecDraft
from mvp_mcp.domain.spec.templates_data import TEMPLATES


def format_intake(user_request: str, questions: list[Question]) -> str:
    """clarify_intent 결과: 요청 되짚기 + discovery 질문 목록 + 진행 안내."""
    lines = [
        "🧭 의도 파악(선행 단계)",
        f"사용자 요청: {user_request}",
        "",
        "아래 질문을 **한 번에 하나씩** 사용자에게 묻고(설명·힌트 포함), 답을 모아라.",
        "성급히 결과물을 만들지 말고, 의도가 충분히 명확해진 뒤에만 start_spec 으로 넘어간다.",
        "",
    ]
    for i, q in enumerate(questions, start=1):
        lines.append(f"{i}. [{q.field}] {q.text}")
        if q.description:
            lines.append(f"   · 설명: {q.description}")
        if q.options:
            choices = "  ".join(f"{j}) {o}" for j, o in enumerate(q.options, start=1))
            lines.append(f"   · 보기: {choices}")
        if q.hint:
            lines.append(f"   · 힌트: {q.hint}")
    lines.append("")
    lines.append(
        "답이 모이면 'deliverable' 로 프로젝트 유형을 정하고, 파악한 값을 known_info 로 "
        "담아 start_spec 을 호출한다."
    )
    return "\n".join(lines)


def format_next_question(questions: list[Question]) -> str:
    """남은 질문 중 **다음 하나**만 설명·보기·힌트와 함께 렌더링한다(문답식 진행).

    모두 채워졌으면 다음 단계(scope_mvp)를 안내한다. 여러 질문을 한꺼번에 묻지 않고
    한 번에 하나씩 진행하도록, 항상 첫 번째 미충족 질문만 노출한다.
    """
    if not questions:
        return "✅ 모든 필수 정보가 채워졌습니다. 이제 scope_mvp 를 호출하세요."
    q = questions[0]
    lines = [f"❓ 다음 질문 (남은 {len(questions)}개)", f"[{q.field}] {q.text}"]
    if q.description:
        lines.append(f"  · 설명: {q.description}")
    if q.options:
        choices = "  ".join(f"{i}) {opt}" for i, opt in enumerate(q.options, start=1))
        lines.append(f"  · 보기: {choices}")
    if q.hint:
        lines.append(f"  · 힌트: {q.hint}")
    return "\n".join(lines)


def format_start(draft: SpecDraft, questions: list[Question]) -> str:
    """start_spec 결과: id + 적용 템플릿 + 다음 질문(하나)."""
    template = TEMPLATES.get(draft.project_type)
    display_name = template.display_name if template else draft.project_type.value
    return (
        f"명세 세션 시작됨 → spec_id={draft.id}\n"
        f"적용 템플릿: {display_name}\n\n"
        f"{format_next_question(questions)}"
    )


def format_scope(draft: SpecDraft) -> str:
    """scope_mvp 결과: 확정 포함 기능 / 컷된 기능+사유."""
    included = ", ".join(draft.features) if draft.features else "(없음)"
    deferred = "\n".join(f"- {d}" for d in draft.deferred) if draft.deferred else "- (없음)"
    return (
        f"MVP 범위 확정됨 (spec_id={draft.id})\n"
        f"포함 기능: {included}\n"
        f"컷된 기능:\n{deferred}\n\n"
        "다음: finalize_spec 을 호출하세요."
    )
