"""문서화 번들의 구조·추적성·단계 게이트."""

from __future__ import annotations

from .documentation_model import DocumentationValidationResult
from .model import SpecDraft, VerificationStatus
from .tier_policy import select_profile


def validate_documentation(draft: SpecDraft) -> DocumentationValidationResult:
    issues: list[str] = []
    blockers: list[str] = []
    if not draft.project_root:
        issues.append("대상 project_root가 없습니다.")
    if not draft.scope_confirmed:
        issues.append("MVP 범위가 확정되지 않았습니다.")
    if not draft.requirements:
        issues.append("BIZ/FR/NFR/DATA/SEC 요구사항이 없습니다.")
    if draft.design_contract is None:
        issues.append("구조화 설계 계약이 없습니다.")
    if not draft.tasks:
        issues.append("TASK가 없습니다.")
    if not draft.test_cases:
        issues.append("TEST가 없습니다.")

    requirement_ids = {item.id for item in draft.requirements}
    task_refs = {ref for task in draft.tasks for ref in task.requirement_ids}
    test_refs = {ref for test in draft.test_cases for ref in test.requirement_ids}
    for missing in sorted(requirement_ids - task_refs):
        issues.append(f"{missing}에 연결된 TASK가 없습니다.")
    for missing in sorted(requirement_ids - test_refs):
        issues.append(f"{missing}에 연결된 TEST가 없습니다.")

    if draft.documentation.has_pending_decision:
        blockers.append("설문의 '계획 미정' 항목을 담당자·기한과 함께 확정해야 합니다.")
    unresolved_decisions = (
        [item for item in draft.design_contract.open_decisions if item.status == "open"]
        if draft.design_contract
        else []
    )
    if unresolved_decisions:
        topics = ", ".join(item.topic for item in unresolved_decisions)
        blockers.append(f"해결되지 않은 설계 OPEN 결정이 있습니다: {topics}")

    verification_by_test = {item.test_id: item for item in draft.verification}
    verification_done = bool(draft.test_cases) and all(
        verification_by_test.get(test.id) is not None
        and verification_by_test[test.id].status is VerificationStatus.PASS
        for test in draft.test_cases
    )
    if not verification_done:
        blockers.extend(
            f"{test.id} NOT_RUN"
            for test in draft.test_cases
            if verification_by_test.get(test.id) is None
        )

    bundle_valid = not issues
    implementation_ready = (
        bundle_valid and not draft.documentation.has_pending_decision and not unresolved_decisions
    )
    next_action = (
        "documentation_preview_package로 생성 파일과 충돌을 확인하세요."
        if implementation_ready
        else "blocking_items와 누락된 구조화 계약을 해결하세요."
    )
    return DocumentationValidationResult(
        profile=select_profile(draft.documentation),
        bundle_valid=bundle_valid,
        implementation_ready=implementation_ready,
        verification_done=verification_done,
        issues=issues,
        blocking_items=blockers,
        next_action=next_action,
    )
