"""구현 중 실제로 실행한 TEST 결과를 기록하는 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.implementation_usecase import RecordImplementationEvidenceUseCase
from mvp_mcp.domain.spec.model import VerificationEvidence
from mvp_mcp.presentation._safe import safe_tool


def register_implementation_record_evidence_tool(
    mcp: FastMCP, use_case: RecordImplementationEvidenceUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
        )
    )
    @safe_tool
    def implementation_record_evidence(
        run_id: str, evidence: VerificationEvidence, idempotency_key: str
    ) -> str:
        """실제로 실행한 TEST 결과 하나를 append-only로 기록한다.

        PASS에는 실행 근거(evidence: 명령·출력 요약), executor, executed_at, evidence_path
        (테스트 파일 또는 로그 경로)가 필요하다. 실행하지 않은
        TEST는 기록하지 않는다. 같은 idempotency_key 재시도는 같은 결과를 돌려준다.
        """

        return use_case(run_id, evidence, idempotency_key).model_dump_json(indent=2)
