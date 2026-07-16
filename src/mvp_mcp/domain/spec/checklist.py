"""⑨ 품질 체크리스트를 코드로 강제.

``validate`` 는 **최종화를 차단하는** 미통과 항목을 반환한다. 비면 통과.
``FinalizeSpecUseCase`` 는 항목이 있으면 최종화를 거부한다(기획의 "추측해서 결정하지
않는다" 원칙을 강제).
"""

from __future__ import annotations

from .model import DomainTemplate, SpecDraft


def validate(draft: SpecDraft, template: DomainTemplate) -> list[str]:
    """최종화를 차단하는 품질 미통과 항목을 반환한다(빈 리스트면 통과)."""
    issues: list[str] = []

    # 요구사항 누락 없음: 필수 필드가 모두 답변됐는가.
    missing = [f for f in template.required_fields if f not in draft.answers]
    if missing:
        issues.append(f"미답변 필수 필드: {', '.join(missing)}")

    # MVP 범위 확정됨: scope_mvp 가 실행됐는가.
    if draft.status == "collecting":
        issues.append("MVP 범위 미확정 — scope_mvp 를 먼저 호출하세요.")

    # 범위 초과 없음: 확정 기능에 제외 기능이 섞이지 않았는가.
    overreach = [f for f in draft.features if f in template.excluded_features]
    if overreach:
        issues.append(f"MVP 범위 초과 기능 포함: {', '.join(overreach)}")

    return issues
