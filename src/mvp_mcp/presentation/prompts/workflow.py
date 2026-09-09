"""MVP 명세 워크플로 Prompt 어댑터.

MCP 클라이언트(예: Claude)에게 이 서버의 도구를 어떤 순서로 쓰는지 안내한다. 이 문구가
산출물 품질을 좌우한다 — 아웃풋이 아쉬우면 이 파일부터 다듬는다.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

SERVER_INSTRUCTIONS = (
    "이 서버는 MVP 설계 문서 생성용이다. 사용자가 새 제품·프로그램·MVP 아이디어를 제시하면 "
    "기본 시작 도구로 ask_web_survey(user_request, project_root)를 즉시 호출하라. 일반 채팅으로 "
    "인터뷰 질문을 먼저 출력하거나 start_spec, clarify_intent, answer_question, "
    "ask_next_web_question을 기본 흐름에서 호출하지 마라. 웹 Wizard 제출 뒤에는 "
    "scope_mvp → register_requirements → confirm_scope → register_design_contract → "
    "register_delivery_contract → get_mvp_bundle_context → validate_mvp_bundle → "
    "export_mvp_bundle 순서를 따른다. 서버가 제공하는 도구를 실제 호출할 수 없는 경우에만 "
    "연결 활성화를 안내한다."
)

WORKFLOW_INSTRUCTIONS = (
    "너는 MVP 설계 PM 도구를 사용한다. 별도 요청이 없으면 사용자와의 대화와 "
    "최종 명세를 모두 **한국어(한글)** 로 작성한다. 사용자가 프로젝트/아이디어를 처음 "
    "제시하면 **절대 곧바로 결과물이나 해결책을 만들지 마라.** 다음 순서를 따른다:\n\n"
    "0. (선행·필수) 사용자가 프로젝트/아이디어를 처음 제시하면 UI 선택을 묻지 말고 "
    "`ask_web_survey(user_request, project_root)`를 호출한다. `project_root`에는 현재 Codex/"
    "Cowork 작업 폴더의 절대 경로를 넣는다. 로컬 브라우저에 하나의 웹 Wizard 설문이 "
    "열리며, 사용자는 문제·목표·결과물 유형·유형별 필수 정보·MVP 기능·제약을 한 번에 "
    "작성해 제출한다. 설문이 완료될 때까지 일반 채팅으로 추가 질문을 하지 마라. 웹 Wizard를 "
    "열 수 없을 때만 설문 문항을 일반 채팅으로 제시한다.\n"
    "1. `ask_web_survey`는 설문 제출을 기다린 뒤 같은 호출에서 `spec_id`를 반환한다. "
    "따라서 `resume_web_survey`나 `get_web_survey_status`를 호출하지 말고, 별도로 "
    "`start_spec`, `answer_question`, `ask_next_web_question`을 호출하지도 마라. "
    "설문 뒤 추가 질문도 하지 마라.\n"
    "2. 설문에서 받은 요청 기능으로 `scope_mvp` 를 호출한다. 이어서 요구사항을 모호성·충돌·"
    "미확정 항목까지 정리해 `register_requirements`에 넣는다. **웹 설문의 마지막 제출은 이 MVP "
    "범위와 6문서 생성을 승인한 것으로 간주한다.** REQ-ID와 MVP 포함/제외는 문서에 기록하되, "
    "일반 채팅에서 별도 승인 답변을 기다리지 마라.\n"
    "3. 바로 `confirm_scope`를 호출한다. 상세 설계 계약(화면, 사용자 흐름, 데이터 모델, "
    "인터페이스, 업무 규칙, 오류/복구, Open Decision)을 `register_design_contract`에 등록한다. "
    "그 뒤 각 REQ-ID를 빠짐없이 연결한 구현 작업(TASK-ID, 의존성, 파일 범위, 완료 조건)과 "
    "테스트(TEST-ID, 자동/수동, 정상/경계/실패, 기대 결과)를 "
    "`register_delivery_contract`에 등록한다. "
    "P0 요구사항은 수용 기준 2개 이상과 정상 및 경계/실패 TEST를 반드시 가진다. 이 MCP는 구현 "
    "코드를 변경하거나 테스트를 실행하지 않는다.\n"
    "4. `get_mvp_bundle_context`를 호출해 반환된 필수 `##` 섹션을 정확히 포함한 다섯 Markdown "
    "문서를 작성한다. `requirements.md`에는 기능·비기능·수용 기준·Open Decision, "
    "`proposal.md`에는 문제·사용자·가치·범위·지표·리스크, `plan.md`에는 기술 스택과 유형별 "
    "화면/데이터/"
    "인터페이스/규칙/오류 설계, `backlog.md`에는 구현 순서·작업 상세·완료 조건, "
    "`test-plan.md`에는 사전 조건·정상·경계/실패·증거 수집을 포함한다. 한두 줄 요약이나 "
    "확인되지 않은 사실의 추측은 금지한다.\n"
    "5. 먼저 다섯 본문으로 `validate_mvp_bundle`을 호출한다. 실패하면 반환된 누락 항목만 보완해 "
    "다시 검증한다. 통과한 경우에만 `export_mvp_bundle`로 저장한다. 이 Tool은 현재 프로젝트 "
    "루트의 `mvpmcp/`에 다섯 문서와 `verification-report.md`를 생성한다. 검증 보고서는 실제 근거를 "
    "`record_verification`으로 등록하기 전까지 반드시 `NOT_RUN`이다. 저장 성공 뒤에는 문서 전문을 "
    "중복 출력하지 말고, Tool이 돌려준 클릭 가능한 링크와 문서에 실제로 들어간 '포함 내용' "
    "3~7개만 안내한다.\n"
    "6. 별도 구현 AI가 `backlog.md`를 따라 구현·테스트한 뒤에만, 그 AI 또는 사용자가 실제 로그·"
    "스크린샷·명령 결과를 근거로 `record_verification`을 호출하고 `export_mvp_bundle`을 다시 "
    "호출한다. 근거 없는 PASS를 쓰지 마라. 기존 `finalize_spec`과 `export_spec`은 이전 두 "
    "문서 흐름의 호환용이다.\n"
)


def register_prompts(mcp: FastMCP) -> None:
    """MVP 설계 워크플로 Prompt 를 등록한다."""

    @mcp.prompt()
    def mvp_spec_workflow() -> str:
        """사용자 요청을 MVP 명세로 변환하는 도구 사용 절차."""
        return WORKFLOW_INSTRUCTIONS
