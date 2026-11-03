"""Run 전용 후보 텍스트 파일의 조건부 저장 Tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.candidate_file_model import CandidateFileWriteRequest
from mvp_mcp.domain.spec.candidate_file_usecase import WriteCandidateFileUseCase
from mvp_mcp.presentation._safe import safe_tool


def register_documentation_write_candidate_file_tool(
    mcp: FastMCP, use_case: WriteCandidateFileUseCase
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_write_candidate_file(
        run_id: str,
        expected_run_version: int,
        relative_path: str,
        content: str,
        expected_file_sha256: str | None,
        idempotency_key: str,
    ) -> str:
        """후보 파일 하나를 저장한다. 신규는 hash=null, 수정은 status의 파일 hash를 사용한다.

        셸 명령·절대 경로를 받지 않는다. 전체 본문을 전달하고 응답 유실 시 모든 입력과
        idempotency_key를 그대로 재전송한다. 저장 후 전체 validate/preview는 별도 수행한다.
        """
        request = CandidateFileWriteRequest(
            run_id=run_id,
            expected_run_version=expected_run_version,
            relative_path=relative_path,
            content=content,
            expected_file_sha256=expected_file_sha256,
            idempotency_key=idempotency_key,
        )
        return use_case(request).model_dump_json(indent=2)
