"""클라이언트 native 질문 UI 답변 제출 MCP adapter."""

from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from mvp_mcp.domain.spec.adaptive_wizard_model import AdaptiveRunStatus
from mvp_mcp.domain.spec.adaptive_wizard_policy import (
    product_design_question_guidance,
    required_product_design_question_ids,
)
from mvp_mcp.domain.spec.adaptive_wizard_usecase import (
    CreateAdaptiveWizardDraftUseCase,
    SubmitAdaptiveWizardAnswersUseCase,
)
from mvp_mcp.presentation._safe import safe_tool
from mvp_mcp.presentation.tools._adaptive_wizard_snapshot import adaptive_wizard_snapshot


def register_documentation_submit_adaptive_wizard_answers_tool(
    mcp: FastMCP,
    submit: SubmitAdaptiveWizardAnswersUseCase,
    create_draft: CreateAdaptiveWizardDraftUseCase,
) -> None:
    """native 질문 UI의 확정 답변을 저장하고 다음 결정을 반환한다."""

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=False,
        )
    )
    @safe_tool
    def documentation_submit_adaptive_wizard_answers(
        run_id: str,
        phase: Literal["intake", "design"],
        answers: dict[str, object],
        revise: bool = False,
    ) -> str:
        """한 단계의 구조화 답변을 원자 저장한다.

        같은 답변을 재제출하면 기존 Run을 반환한다. 1차 제출 뒤에는 저장소 근거를 분석해 2차
        질문을 열고, 2차 제출 뒤에는 즉시 candidate workspace를 발급한다. `revise=True`는
        2차 질문이 열리기 전까지만 1차 답변을 고친다.

        `answers`는 질문 id별 값이다. select는 option 값 문자열, multiselect는 option 값 배열,
        선택지에 없는 직접 입력은 `{"selected": [option 값...], "other_text": "직접 입력"}`,
        text·textarea는 문자열. 기타를 허용하는 문항에 선택지 밖 값을 보내면
        `other_text`로 저장된다.
        """

        run = submit(run_id, phase, answers, revise)
        if phase == "design" and run.status is AdaptiveRunStatus.DESIGN_SUBMITTED:
            run = create_draft(run.id)
        result = adaptive_wizard_snapshot(run)
        if phase == "intake":
            submission = run.intake_submission
            intake_answers: dict[str, object] = dict(submission.answers) if submission else {}
            inferred = submission.ai_inferred if submission else {}
            result.update(
                {
                    "phase": "intake",
                    "user_message_required": False,
                    "required_design_question_ids": sorted(
                        required_product_design_question_ids(intake_answers, inferred)
                    ),
                    "design_question_guidance": [
                        question.model_dump(mode="json")
                        for question in product_design_question_guidance(intake_answers, inferred)
                    ],
                    "next_action": "analyze_intake_and_open_design",
                    "next_instruction": (
                        "같은 작업에서 최초 요청·intake_answers·project_root의 실제 저장소 "
                        "맥락을 분석하세요. design_question_guidance의 필수 문항을 모두 포함하고 "
                        "1차 질문을 반복하지 않는 3~10개 맞춤 질문을 만든 뒤, "
                        "documentation_start_adaptive_wizard(phase='design', run_id, "
                        "design_questions)를 호출하세요. "
                        "색·분위기 같은 디자인 질문은 만들지 마세요. "
                        "design_must_features 선택지는 분석한 기능 후보로, confirm_* 선택지는 "
                        "AI 제안 문장으로 바꾸세요. 모든 선택지에 쉬운 option_labels를 다세요. "
                        "추가 채팅 질문·브라우저·제출 확인을 요구하지 마세요."
                    ),
                }
            )
        else:
            result.update(
                {
                    "phase": "design",
                    "user_message_required": False,
                    "next_action": "write_candidate_package",
                    "next_instruction": (
                        "2차 답변까지 수집됐습니다. candidate_root 안에만 UTF-8 후보 문서를 "
                        "작성한 뒤 "
                        "documentation_package_status → documentation_validate_package → "
                        "documentation_preview_package 순서로 진행하세요."
                    ),
                }
            )
        return json.dumps(result, ensure_ascii=False)
