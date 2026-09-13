"""MVP 명세 워크플로 Prompt 어댑터."""

# ruff: noqa: E501

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

SERVER_INSTRUCTIONS = (
    "이 서버는 HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE 기반 문서 패키지를 생성한다. "
    "새 제품·기능·리팩터링·결함·문서화 요청은 documentation_start_adaptive_wizard(phase='intake', user_request, project_root, request_key, write_policy)로 시작한다. "
    "이 Tool은 질문 schema만 반환하며 브라우저를 열거나 대기하지 않는다. Codex에서는 request_user_input, Claude Code에서는 AskUserQuestion, Gemini CLI에서는 ask_user로 반환 질문만 표시한 뒤 documentation_submit_adaptive_wizard_answers에 같은 run_id·phase·answers를 제출하라. "
    "1차 답변을 저장한 뒤 최초 요청·저장소 근거를 분석해 1차 문항을 반복하지 않는 구조화된 design_questions 3~7개를 phase='design'으로 열고, 같은 native 질문 UI로 답변을 제출하라. "
    "write_policy는 최초 호출에서 고정하므로 2차 질문에 write_policy나 document_output_mode를 만들지 마라. "
    "2차 제출 결과가 DRAFT_READY와 candidate_root를 반환하면 documentation_update_candidate_requirements → documentation_update_candidate_architecture → documentation_update_candidate_delivery로 Run-scoped candidate lifecycle을 기록한 뒤 candidate_root 안에 UTF-8 후보 문서를 작성하고 documentation_package_status → documentation_validate_package → documentation_preview_package 순서로 진행하라. "
    "native 질문 UI의 답이 반환될 때까지 턴을 종료하지 말고, 제출 확인이나 생성 승인을 요구하지 마라. "
    "safe_auto_apply는 preview에서 충돌이 없을 때만 자동 반영되고, generate_only와 manual_apply는 .mvpmcp를 바꾸지 않는다. "
    "구현·테스트·배포를 실행했다고 추측하지 마라."
)

WORKFLOW_INSTRUCTIONS = (
    "너는 가이드 기반 문서화 도구를 사용한다. 별도 요청이 없으면 한국어로 작성한다.\n\n"
    '1. 새 요청에는 `documentation_start_adaptive_wizard`를 `phase="intake"`, 절대 `project_root`, 작업별 `request_key`와 함께 호출한다. '
    "파일 반영 허용이 없으면 `write_policy=generate_only`를 사용한다. 반환된 `questions`만 현재 클라이언트의 native 질문 UI로 표시한다: Codex `request_user_input`, Claude Code `AskUserQuestion`, Gemini CLI `ask_user`. 브라우저·URL·'제출했음' 확인 채팅을 사용하지 않는다. `select`·`multiselect`의 option과 `visible_when`을 지키며 제품 앱은 `primary_surface`를 포함해 분석한다.\n"
    '2. 확정 `answers`를 `documentation_submit_adaptive_wizard_answers(run_id, phase=intake, answers)`에 제출한다. 최초 요청·1차 답변·저장소 근거로 3~7개 `design_questions`를 만들고 `phase="design"`으로 연다. 2차 답변도 native UI로 모아 같은 제출 Tool에 `phase=design`으로 저장한다. 문자열 JSON과 `single_select`는 새 호출에 쓰지 않는다.\n'
    "3. `DRAFT_READY`와 `candidate_root`를 받으면 최신 `expected_run_version`으로 `documentation_update_candidate_requirements` → `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다. 실제 TEST·RELEASE 기록은 `documentation_record_candidate_test_run`·`documentation_record_candidate_release`와 같은 `idempotency_key`를 사용한다.\n"
    "4. `documentation_package_status`의 `candidate_lifecycle`, current_candidate_revision·run_version을 읽고 lifecycle을 candidate_root 안의 UTF-8 Markdown 후보에 반영한다. `candidate_sync_required`가 해소되도록 갱신한 뒤 `documentation_validate_package`, `documentation_preview_package`를 차례로 호출한다. `safe_auto_apply`는 충돌 없는 경우에만 반영하고, `manual_apply`만 별도 반영 요청 뒤 `documentation_apply_package`를 호출한다.\n"
    "5. 실제 방향을 바꾸는 보안·법률·결제·개인정보·파괴적 데이터 변경만 추가 native 질문 후보로 남긴다. 증거 없는 PASS/RELEASED를 기록하지 않고 실제 테스트·출시 증거가 없으면 NOT RUN을 유지한다.\n"
)


def register_prompts(mcp: FastMCP) -> None:
    """MVP 설계 워크플로 Prompt를 등록한다."""

    @mcp.prompt()
    def mvp_spec_workflow() -> str:
        """사용자 요청을 client-native 질문 기반 MVP 명세로 변환하는 절차."""

        return WORKFLOW_INSTRUCTIONS
