"""6문서 실행 계약의 상세도·추적성 품질 게이트."""

from __future__ import annotations

import re

from .model import MvpBundleRequest, Priority, ProjectType, SpecDraft

_COMMON_HEADINGS: dict[str, tuple[str, ...]] = {
    "requirements_markdown": (
        "## 기능 요구사항",
        "## 비기능 요구사항",
        "## 수용 기준",
        "## 가정 및 미확정 결정",
    ),
    "proposal_markdown": (
        "## 배경 및 문제 정의",
        "## 목표 및 기대 효과",
        "## 대상 사용자 및 사용 시나리오",
        "## 핵심 가치 제안",
        "## MVP 범위",
        "## 성공 지표",
        "## 리스크 및 가정",
    ),
    "backlog_markdown": ("## 구현 순서", "## 작업 상세", "## 완료 조건"),
    "test_plan_markdown": (
        "## 테스트 데이터 및 사전 조건",
        "## 정상 시나리오",
        "## 경계 및 실패 시나리오",
        "## 증거 수집 방법",
    ),
}

_PLAN_HEADINGS: dict[ProjectType, tuple[str, ...]] = {
    ProjectType.MCP_SERVER: (
        "## 확정 정책",
        "## 기술 스택",
        "## Tool·Resource·Prompt 설계",
        "## 입출력 및 오류 계약",
        "## 내부 아키텍처",
        "## 상태 및 데이터 관리",
        "## 배포 및 통합",
    ),
    ProjectType.ML_PROJECT: (
        "## 문제 정의 및 목표 지표",
        "## 기술 스택",
        "## 데이터 명세",
        "## 데이터 파이프라인",
        "## 모델 및 방법론",
        "## 평가 설계",
        "## 실험 관리",
    ),
    ProjectType.DATA_PIPELINE: (
        "## 데이터 소스 명세",
        "## 기술 스택",
        "## 파이프라인 아키텍처",
        "## 스키마 및 데이터 모델",
        "## 스케줄링 및 재시도",
        "## 데이터 품질 및 운영",
    ),
}

_APP_PLAN_HEADINGS = (
    "## 확정 정책",
    "## 기술 스택",
    "## 화면 목록 및 상태",
    "## 사용자 플로우",
    "## 데이터 모델",
    "## API 및 인터페이스 계약",
    "## 업무 규칙",
    "## 오류 및 복구",
    "## 책임 분리 및 폴더 구조",
)


def required_sections(project_type: ProjectType) -> dict[str, tuple[str, ...]]:
    """문서별 최소 섹션 계약을 반환한다."""
    plan = _PLAN_HEADINGS.get(project_type, _APP_PLAN_HEADINGS)
    return {**_COMMON_HEADINGS, "plan_markdown": plan}


def validate_bundle(draft: SpecDraft, request: MvpBundleRequest) -> list[str]:
    """파일 저장 전 차단해야 할 문서·설계·추적성 누락을 수집한다."""
    issues: list[str] = []
    contract = draft.design_contract
    if contract is None:
        issues.append("상세 설계 계약이 없습니다 — register_design_contract를 먼저 호출하세요.")
    else:
        if draft.project_type in {
            ProjectType.ETC,
            ProjectType.MESSENGER,
            ProjectType.SHOPPING_MALL,
            ProjectType.BLOG,
        }:
            required_lists = {
                "화면": contract.screens,
                "사용자 플로우": contract.user_flows,
                "데이터 모델": contract.data_entities,
                "인터페이스": contract.interfaces,
                "업무 규칙": contract.business_rules,
                "오류 및 복구": contract.error_states,
            }
            issues.extend(
                f"상세 설계 계약의 {name}이 비어 있습니다."
                for name, value in required_lists.items()
                if not value
            )
        elif draft.project_type is ProjectType.MCP_SERVER:
            if not contract.interfaces or not contract.business_rules or not contract.error_states:
                issues.append("MCP 설계에는 인터페이스·업무 규칙·오류 및 복구 계약이 필요합니다.")
        else:
            if not contract.data_entities or not contract.business_rules:
                issues.append("데이터/ML 설계에는 데이터 모델과 업무 규칙 계약이 필요합니다.")

    task_ids = {reference for task in draft.tasks for reference in task.requirement_ids}
    test_ids = {reference for test in draft.test_cases for reference in test.requirement_ids}
    task_identifiers = [item.id for item in draft.tasks]
    test_identifiers = [item.id for item in draft.test_cases]
    if len(task_identifiers) != len(set(task_identifiers)):
        issues.append("등록된 TASK-ID가 중복되었습니다.")
    if len(test_identifiers) != len(set(test_identifiers)):
        issues.append("등록된 TEST-ID가 중복되었습니다.")
    for requirement in draft.requirements:
        if requirement.id not in task_ids:
            issues.append(f"{requirement.id}에 연결된 TASK가 없습니다.")
        if requirement.id not in test_ids:
            issues.append(f"{requirement.id}에 연결된 TEST가 없습니다.")
        if requirement.priority is Priority.P0:
            if len(requirement.acceptance_criteria) < 2:
                issues.append(f"{requirement.id} P0 요구사항에는 수용 기준이 2개 이상 필요합니다.")
            case_types = {
                test.case_type
                for test in draft.test_cases
                if requirement.id in test.requirement_ids
            }
            if "normal" not in case_types or not ({"boundary", "failure"} & case_types):
                issues.append(
                    f"{requirement.id} P0 요구사항에는 정상 및 경계/실패 TEST가 필요합니다."
                )

    for field, headings in required_sections(draft.project_type).items():
        body = str(getattr(request, field))
        missing = [heading for heading in headings if heading not in body]
        if missing:
            issues.append(f"{field} 필수 섹션 누락: {', '.join(missing)}")
    _validate_document_ids(request, task_identifiers, test_identifiers, issues)
    open_decisions = draft.intake.get("open_decisions", "")
    if open_decisions:
        for field in ("requirements_markdown", "plan_markdown"):
            if open_decisions not in str(getattr(request, field)):
                issues.append(f"{field}에 설문의 미확정 결정이 반영되지 않았습니다.")
    return issues


def _validate_document_ids(
    request: MvpBundleRequest,
    task_identifiers: list[str],
    test_identifiers: list[str],
    issues: list[str],
) -> None:
    """백로그와 테스트 계획이 계약의 고유 식별자를 정확히 한 번씩 기록하는지 확인한다."""
    for field, prefix, expected in (
        ("backlog_markdown", "TASK", task_identifiers),
        ("test_plan_markdown", "TEST", test_identifiers),
    ):
        identifiers = re.findall(rf"{prefix}-\d{{3}}", str(getattr(request, field)))
        unknown = sorted(set(identifiers) - set(expected))
        if unknown:
            issues.append(f"{field}에 등록되지 않은 {prefix}-ID가 있습니다: {', '.join(unknown)}")
        duplicated = sorted(
            identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1
        )
        if duplicated:
            issues.append(f"{field}에 중복된 {prefix}-ID가 있습니다: {', '.join(duplicated)}")
        missing = sorted(set(expected) - set(identifiers))
        if missing:
            issues.append(f"{field}에 누락된 {prefix}-ID가 있습니다: {', '.join(missing)}")
