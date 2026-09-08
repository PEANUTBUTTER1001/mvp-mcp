"""실행 계약(요구사항·범위·검증·6문서) Tool 어댑터."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mvp_mcp.domain.spec.model import (
    DeliveryTestCase,
    DesignContract,
    ImplementationTask,
    MvpBundleRequest,
    RequirementInput,
    VerificationEvidence,
)
from mvp_mcp.domain.spec.usecase import (
    ConfirmScopeUseCase,
    ExportMvpBundleUseCase,
    GetMvpBundleContextUseCase,
    RecordVerificationUseCase,
    RegisterDeliveryContractUseCase,
    RegisterDesignContractUseCase,
    RegisterRequirementsUseCase,
    ValidateMvpBundleUseCase,
)
from mvp_mcp.presentation._safe import safe_tool


def register_delivery_tools(
    mcp: FastMCP,
    requirements_uc: RegisterRequirementsUseCase,
    confirm: ConfirmScopeUseCase,
    contract: RegisterDeliveryContractUseCase,
    design: RegisterDesignContractUseCase,
    verification: RecordVerificationUseCase,
    exporter: ExportMvpBundleUseCase,
    validator: ValidateMvpBundleUseCase,
    bundle_context: GetMvpBundleContextUseCase,
) -> None:
    """실행 계약 Tool 묶음을 등록한다."""

    @mcp.tool()
    @safe_tool
    def register_requirements(spec_id: str, items: list[RequirementInput]) -> str:
        draft = requirements_uc(spec_id, items)
        return "요구사항 등록됨: " + ", ".join(item.id for item in draft.requirements)

    @mcp.tool()
    @safe_tool
    def confirm_scope(spec_id: str) -> str:
        draft = confirm(spec_id)
        return f"MVP 범위 확인 완료: spec_id={draft.id}"

    @mcp.tool()
    @safe_tool
    def register_design_contract(spec_id: str, contract: DesignContract) -> str:
        design(spec_id, contract)
        return (
            "상세 설계 계약 등록됨: "
            f"화면 {len(contract.screens)}개, 흐름 {len(contract.user_flows)}개, "
            f"데이터 {len(contract.data_entities)}개, 인터페이스 {len(contract.interfaces)}개"
        )

    @mcp.tool()
    @safe_tool
    def get_mvp_bundle_context(spec_id: str) -> str:
        return bundle_context(spec_id)

    @mcp.tool()
    @safe_tool
    def register_delivery_contract(
        spec_id: str, tasks: list[ImplementationTask], tests: list[DeliveryTestCase]
    ) -> str:
        draft = contract(spec_id, tasks, tests)
        return f"작업 {len(draft.tasks)}개·테스트 {len(draft.test_cases)}개 계약 등록됨"

    @mcp.tool()
    @safe_tool
    def record_verification(spec_id: str, evidence: list[VerificationEvidence]) -> str:
        draft = verification(spec_id, evidence)
        return f"검증 근거 {len(draft.verification)}건 기록됨"

    @mcp.tool()
    @safe_tool
    def export_mvp_bundle(
        spec_id: str,
        requirements_markdown: str,
        proposal_markdown: str,
        plan_markdown: str,
        backlog_markdown: str,
        test_plan_markdown: str,
    ) -> str:
        result = exporter(
            MvpBundleRequest(
                spec_id=spec_id,
                requirements_markdown=requirements_markdown,
                proposal_markdown=proposal_markdown,
                plan_markdown=plan_markdown,
                backlog_markdown=backlog_markdown,
                test_plan_markdown=test_plan_markdown,
            )
        )
        links = "\n".join(
            f"- [{name}]({path.replace(chr(92), '/')})" for name, path in result.paths.items()
        )
        return (
            f"MVP 실행 문서를 만들었습니다.\n\n{links}\n\n"
            "포함 내용:\n"
            "- REQ-ID별 기능·비기능 요구사항과 수용 기준\n"
            "- 사용자·범위·성공 지표·리스크가 있는 기획서\n"
            "- 화면·흐름·데이터·인터페이스·오류 복구 설계\n"
            "- TASK-ID 구현 백로그와 TEST-ID 정상·경계/실패 시나리오\n"
            "- 실제 검증 전 `NOT_RUN`으로 시작하는 인수 보고서"
        )

    @mcp.tool()
    @safe_tool
    def validate_mvp_bundle(
        spec_id: str,
        requirements_markdown: str,
        proposal_markdown: str,
        plan_markdown: str,
        backlog_markdown: str,
        test_plan_markdown: str,
    ) -> str:
        result = validator(
            MvpBundleRequest(
                spec_id=spec_id,
                requirements_markdown=requirements_markdown,
                proposal_markdown=proposal_markdown,
                plan_markdown=plan_markdown,
                backlog_markdown=backlog_markdown,
                test_plan_markdown=test_plan_markdown,
            )
        )
        if result.passed:
            return "6문서 품질 게이트 통과: export_mvp_bundle로 저장할 수 있습니다."
        return "6문서 품질 게이트 미통과:\n- " + "\n- ".join(result.issues)
