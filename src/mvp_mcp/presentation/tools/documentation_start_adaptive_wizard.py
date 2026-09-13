"""비대기형 2단계 Adaptive Wizard MCP adapter."""

from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from mvp_mcp.core.exceptions import PipelineError
from mvp_mcp.domain.spec.adaptive_wizard_model import (
    AdaptiveRunStatus,
    AdaptiveWizardQuestion,
    AdaptiveWizardRun,
    WritePolicy,
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    OpenAdaptiveDesignWizardUseCase,
    StartAdaptiveWizardUseCase,
)
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._adaptive_wizard_snapshot import adaptive_wizard_snapshot


def register_documentation_start_adaptive_wizard_tool(
    mcp: FastMCP,
    start: StartAdaptiveWizardUseCase,
    design: OpenAdaptiveDesignWizardUseCase,
) -> None:
    """1·2차 질문 schema를 만들고 클라이언트 native UI에 넘긴다."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_start_adaptive_wizard(
        phase: Literal["intake", "design"],
        user_request: str = "",
        project_root: str = "",
        request_key: str = "",
        write_policy: WritePolicy | None = None,
        run_id: str = "",
        design_questions: list[AdaptiveWizardQuestion] | None = None,
        design_questions_json: str = "",
    ) -> str:
        """질문 schema를 반환한다. 브라우저를 열거나 답변을 기다리지 않는다.

        Codex는 `request_user_input`, Claude Code는 `AskUserQuestion`, Gemini CLI는
        `ask_user`로 반환된 질문을 표시한 뒤 `documentation_submit_adaptive_wizard_answers`에
        구조화 답변을 제출한다. `phase="intake"`에는 최초 요청·절대 project_root·request_key가,
        `phase="design"`에는 같은 run_id와 3~7개 맞춤 질문이 필요하다.
        """

        if phase == "intake":
            if run_id or design_questions is not None or design_questions_json:
                raise PipelineError(
                    "adaptive_wizard",
                    "1차 시작에는 run_id나 2차 질문을 넣을 수 없습니다.",
                    "phase=intake에는 user_request, project_root, request_key와 "
                    "선택적 write_policy만 사용하세요.",
                )
            return _serialize_open_questions(
                start(user_request, project_root, request_key, write_policy), "intake"
            )
        if user_request or project_root or request_key or write_policy is not None:
            raise PipelineError(
                "adaptive_wizard",
                "2차 설문에는 최초 요청·경로·request_key·write_policy를 다시 넣을 수 없습니다.",
                "phase=design에는 run_id와 design_questions를 사용하세요.",
            )
        return _serialize_open_questions(
            design(run_id, _resolve_design_questions(design_questions, design_questions_json)),
            "design",
        )


def _resolve_design_questions(
    questions: list[AdaptiveWizardQuestion] | None, legacy_payload: str
) -> list[AdaptiveWizardQuestion]:
    if questions is not None and legacy_payload:
        raise PipelineError(
            "adaptive_wizard",
            "구조화된 design_questions와 design_questions_json을 함께 사용할 수 없습니다.",
            "새 호출에는 design_questions만 사용하세요.",
        )
    if questions is not None:
        return questions
    if not legacy_payload.strip():
        raise PipelineError(
            "adaptive_wizard",
            "2차 맞춤 질문 JSON이 비어 있습니다.",
            "1차 답변과 저장소 분석을 바탕으로 3~7개 질문 정의를 전달하세요.",
        )
    try:
        decoded = json.loads(legacy_payload)
    except json.JSONDecodeError as exc:
        raise PipelineError(
            "adaptive_wizard",
            "2차 맞춤 질문 JSON 형식이 올바르지 않습니다.",
            "새 호출에는 구조화된 design_questions 배열을 사용하세요.",
        ) from exc
    if not isinstance(decoded, list):
        raise PipelineError(
            "adaptive_wizard",
            "2차 맞춤 질문은 JSON 배열이어야 합니다.",
            "3~7개 문항 정의가 든 JSON 배열을 전달하세요.",
        )
    try:
        return [AdaptiveWizardQuestion.model_validate(item) for item in decoded]
    except ValidationError as exc:
        raise PipelineError(
            "adaptive_wizard",
            f"2차 맞춤 질문 정의가 올바르지 않습니다: {exc.errors()[0]['msg']}",
            "각 문항에 안전한 id, label, kind와 선택형 options를 넣으세요.",
        ) from exc


def _serialize_open_questions(run: AdaptiveWizardRun, phase: str) -> str:
    expected_status = (
        AdaptiveRunStatus.INTAKE_OPEN if phase == "intake" else AdaptiveRunStatus.DESIGN_OPEN
    )
    if run.status is not expected_status:
        result = adaptive_wizard_snapshot(run)
        result.update(
            {
                "phase": phase,
                "next_action": "read_existing_run_status",
                "next_instruction": (
                    "질문을 다시 표시하지 말고 저장된 Run 상태와 답변을 사용하세요."
                ),
            }
        )
        return json.dumps(result, ensure_ascii=False)
    questions = run.intake_questions if phase == "intake" else run.design_questions
    result = adaptive_wizard_snapshot(run)
    result.update(
        {
            "phase": phase,
            "questions": [question.model_dump(mode="json") for question in questions],
            "next_action": "ask_client_native_questions",
            "next_instruction": (
                "반환된 질문만 클라이언트 native 질문 UI에 표시한 뒤, 사용자가 확정한 answers를 "
                "documentation_submit_adaptive_wizard_answers에 같은 run_id·phase로 "
                "한 번 제출하세요. "
                "브라우저·URL·추가 제출 확인 메시지를 사용하지 마세요."
            ),
        }
    )
    return json.dumps(result, ensure_ascii=False)
