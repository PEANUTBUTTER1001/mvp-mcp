"""MVP 명세 워크플로 Prompt 어댑터."""

# ruff: noqa: E501

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

SERVER_INSTRUCTIONS = (
    "이 서버는 HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE 기반 문서 패키지를 생성한다. "
    "새 제품·기능·리팩터링·결함·문서화 요청은 documentation_start_adaptive_wizard(phase='intake', user_request, project_root, request_key, write_policy)로 시작한다. "
    "이 Tool은 질문 schema만 반환하며 브라우저를 열거나 대기하지 않는다. Codex에서는 request_user_input, Claude Code에서는 AskUserQuestion, Gemini CLI에서는 ask_user로 반환 질문만 표시한 뒤 documentation_submit_adaptive_wizard_answers에 같은 run_id·phase·answers를 제출하라. "
    "최초 요청에 명시된 work_type·solution_family·primary_surface·app_domain_hint·initial_audience만 suggested_answers로 넘기고(선택지에 없는 말은 other_text), from_request=true 문항은 묻지 말고 prefilled_summary를 첫 질문 앞에 보여 줘라. "
    "1차 답변을 저장한 뒤 최초 요청·저장소 근거를 분석해 1차 문항을 반복하지 않는 구조화된 design_questions 3~10개를 phase='design'으로 열되, 1차 제출 결과의 design_question_guidance·required_design_question_ids(제품 앱 design_frequent_user_tasks, 새로 만들기·기능 추가 design_must_features, AI 추정 confirm_*; 색·분위기 같은 디자인 질문은 만들지 않는다)를 모두 포함하고 선택지에는 쉬운 option_labels를 달아 같은 native 질문 UI로 답변을 제출하라. 서버 선택형 문항의 선택지는 2~4개다(design_must_features만 예외). Claude Code AskUserQuestion에는 한 번에 최대 4문항, 선택지를 그대로 1:1로 넣고 design_must_features는 4개씩 나눠 묻는다. "
    "write_policy는 최초 호출에서 고정하므로 2차 질문에 write_policy나 document_output_mode를 만들지 마라. "
    "2차 제출 결과가 DRAFT_READY와 candidate_root를 반환하면 documentation_update_candidate_requirements → documentation_update_candidate_architecture → documentation_update_candidate_delivery로 Run-scoped candidate lifecycle을 기록한 뒤 candidate_root 안에 UTF-8 후보 문서를 작성하고 documentation_package_status → documentation_validate_package → documentation_preview_package 순서로 진행하라. "
    "mvp-mcp는 디자인과 시제품에 관여하지 않으므로 후보에 prototype/index.html을 만들지 마라. 문서 반영(또는 preview)을 마치면 시제품은 사용자가 별도 프로토타입 스킬(Claude Code는 /mvpmcp:mvpmcpprototype)로 문서를 방안 삼아 만든다고 안내만 하라. "
    "후보 파일은 documentation_write_candidate_file에 run_id·expected_run_version·relative_path·content·expected_file_sha256·idempotency_key를 전달해 한 파일씩 저장하라. 후보 폴더에 쓰기 위한 셸 권한 상승은 사용하지 마라. 신규 hash는 null, 수정 hash는 package status의 candidate_files에서 읽고 다음 호출에는 반환된 version을 사용하라. 응답 유실이나 pending_candidate_write는 원래 모든 입력·같은 key로 재시도하며 CONFLICT는 현재 내용을 검토하라. "
    "native 질문 UI의 답이 반환될 때까지 턴을 종료하지 말고, 제출 확인이나 생성 승인을 요구하지 마라. "
    "safe_auto_apply는 preview에서 충돌이 없을 때만 자동 반영되고, generate_only와 manual_apply는 .mvpmcp를 바꾸지 않는다. "
    "반영 뒤 구현 요청에는 implementation_next_task·implementation_task_context로 작업 단위 명세만 읽고, 실제 실행한 TEST만 implementation_record_evidence로 기록하라. 루트 AGENTS.md 연결은 implementation_link_root_agents 미리보기를 보여 주고 동의할 때만 반영하라. "
    "구현·테스트·배포를 실행했다고 추측하지 마라."
)

WORKFLOW_INSTRUCTIONS = (
    "너는 가이드 기반 문서화 도구를 사용한다. 별도 요청이 없으면 한국어로 작성한다.\n\n"
    '1. 새 요청에는 `documentation_start_adaptive_wizard`를 `phase="intake"`, 절대 `project_root`, 작업별 `request_key`와 함께 호출한다. '
    "파일 반영 허용이 없으면 `write_policy=generate_only`를 사용한다. 최초 요청에 명시된 사실만 `suggested_answers`로 넘기고, `from_request=true` 문항은 묻지 않으며 `prefilled_summary`를 첫 질문 앞에 보여 준다. 반환된 `questions`만 현재 클라이언트의 native 질문 UI로 표시한다: Codex `request_user_input`, Claude Code `AskUserQuestion`, Gemini CLI `ask_user`. 브라우저·URL·'제출했음' 확인 채팅을 사용하지 않는다. `select`·`multiselect`의 option과 `visible_when`을 지키며 제품 앱은 `primary_surface`를 포함해 분석한다.\n"
    '2. 확정 `answers`를 `documentation_submit_adaptive_wizard_answers(run_id, phase=intake, answers)`에 제출한다. 최초 요청·1차 답변·저장소 근거와 `design_question_guidance`로 3~10개 `design_questions`를 만들고 `phase="design"`으로 연다. 2차 답변도 native UI로 모아 같은 제출 Tool에 `phase=design`으로 저장한다. 문자열 JSON과 `single_select`는 새 호출에 쓰지 않는다.\n'
    "3. `DRAFT_READY`와 `candidate_root`를 받으면 최신 `expected_run_version`으로 `documentation_update_candidate_requirements` → `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다. 실제 TEST·RELEASE 기록은 `documentation_record_candidate_test_run`·`documentation_record_candidate_release`와 같은 `idempotency_key`를 사용한다.\n"
    "4. `documentation_package_status`의 `candidate_lifecycle`, current_candidate_revision·run_version을 읽고 lifecycle을 candidate_root 안의 UTF-8 Markdown 후보에 반영한다. 시제품(`prototype/index.html`)은 후보에 만들지 않는다. `candidate_sync_required`가 해소되도록 갱신한 뒤 `documentation_validate_package`, `documentation_preview_package`를 차례로 호출한다. `safe_auto_apply`는 충돌 없는 경우에만 반영하고, `manual_apply`만 별도 반영 요청 뒤 `documentation_apply_package`를 호출한다. 반영(또는 preview)을 마치면 시제품은 사용자가 별도 프로토타입 스킬(Claude Code는 `/mvpmcp:mvpmcpprototype`)로 문서를 방안 삼아 만든다고 안내한다.\n"
    "   후보 저장은 `documentation_write_candidate_file`로 파일별 전체 본문을 전달한다. 신규 `expected_file_sha256=null`, 수정은 `candidate_files`의 해시 사용. `expected_run_version`은 직전 응답 값을 따른다. 원래 입력·같은 `idempotency_key`로만 재시도하고 `pending_candidate_write`가 있으면 복구를 먼저 완료한다. 후보 저장용 셸 권한 상승은 사용하지 않는다.\n"
    "5. 실제 방향을 바꾸는 보안·법률·결제·개인정보·파괴적 데이터 변경만 추가 native 질문 후보로 남긴다. 증거 없는 PASS/RELEASED를 기록하지 않고 실제 테스트·출시 증거가 없으면 NOT RUN을 유지한다.\n"
)


def register_prompts(mcp: FastMCP) -> None:
    """MVP 설계 워크플로 Prompt를 등록한다."""

    @mcp.prompt()
    def mvp_spec_workflow() -> str:
        """사용자 요청을 client-native 질문 기반 MVP 명세로 변환하는 절차."""

        return WORKFLOW_INSTRUCTIONS
