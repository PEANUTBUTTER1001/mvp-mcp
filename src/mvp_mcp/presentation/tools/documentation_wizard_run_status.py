"""영속 Adaptive Wizard Run 상태 조회 MCP adapter."""

# ruff: noqa: E501

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.adaptive_wizard_usecase import GetAdaptiveWizardRunUseCase
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._adaptive_wizard_snapshot import adaptive_wizard_snapshot


def register_documentation_wizard_run_status_tool(
    mcp: FastMCP,
    get_run: GetAdaptiveWizardRunUseCase,
) -> None:
    """새 질문 UI를 열지 않는 복구·진단용 Run 상태 Tool을 등록한다."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_wizard_run_status(run_id: str) -> str:
        """run_id의 단계, 제출 snapshot, 다음 복구 동작을 읽기 전용으로 반환한다."""

        run = get_run(run_id)
        result = adaptive_wizard_snapshot(run)
        result["resume_hint"] = _resume_hint(run.status.value)
        return json.dumps(result, ensure_ascii=False)


def _resume_hint(status: str) -> str:
    hints = {
        "INTAKE_OPEN": "반환된 1차 질문 schema를 클라이언트 native UI에 표시한 뒤 answers를 제출하세요.",
        "INTAKE_SUBMITTED": "1차 답변을 분석한 뒤 phase=design으로 3~7개 맞춤 질문 schema를 열어야 합니다.",
        "DESIGN_OPEN": "저장된 2차 질문 schema를 클라이언트 native UI에 표시한 뒤 answers를 제출하세요.",
        "DESIGN_SUBMITTED": "제출 완료 상태입니다. documentation_submit_adaptive_wizard_answers 재시도로 candidate workspace를 복구하세요.",
        "DRAFT_READY": "candidate_lifecycle를 갱신했다면 candidate Markdown에 반영한 뒤 package_status → validate_package → preview_package를 진행하세요.",
        "CANDIDATE_VALIDATED": "검증된 candidate입니다. 같은 revision과 run_version으로 documentation_preview_package를 호출하세요.",
        "PREVIEW_READY": "후보 preview가 준비됐습니다. generate_only는 결과를 제공하고 manual_apply는 별도 반영 요청 때만 적용하세요.",
        "CONFLICTED": "충돌 파일은 보존됐습니다. 대상 파일을 해소한 뒤 같은 candidate revision으로 새 preview를 만드세요.",
        "APPLIED": "마지막 candidate revision은 반영됐습니다. 새 후보를 작성하면 package status부터 다시 확인하세요.",
    }
    return hints.get(status, "종결 또는 알 수 없는 상태입니다.")
