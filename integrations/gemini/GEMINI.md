# mvp-mcp 문서 패키지 생성 지침 — Gemini CLI

사용자가 `/mvpmcp` 뒤에 제품 아이디어를 입력하면 Web Wizard·브라우저·URL을 사용하지 않는다. 기존
패키지가 있으면 먼저 `<project_root>/.mvpmcp/AGENTS.md`를 읽고 아래 native 질문 흐름을 따른다.

1. 절대 `project_root`와 작업별 불투명 `request_key`로
   `documentation_start_adaptive_wizard(phase="intake")`를 호출한다. 사용자가 자동 반영을 명시적으로
   허용하지 않은 경우 최초 `write_policy`는 `generate_only`다.
2. 반환된 `questions`를 Gemini CLI의 `ask_user`로 1~3개씩 표시한다. `id`별 답을 그대로 보관하고,
   `select`·`multiselect`는 제공된 `options`만, `text`·`textarea`는 자유 입력을 사용한다. 조건부
   `visible_when`이 거짓인 문항은 건너뛴다.
3. 답을 모두 모으면 `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`로 한 번에
   제출한다. 제출 사실을 다시 채팅에 쓰게 하거나 브라우저 확인을 요구하지 않는다.
4. intake 제출 뒤 실제 저장소 근거를 분석해 1차와 중복되지 않는 3~7개 `design_questions`를 만들어
   같은 `run_id`의 `phase="design"`으로 시작한다. 다시 `ask_user`와 제출 Tool을 사용한다. 2차에는
   `write_policy` 또는 파일 반영 정책을 다시 묻지 않는다.
5. 2차 제출이 반환한 `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`의 `candidate_lifecycle`을 `candidate_root`의 후보 문서에 반영한 뒤
   `documentation_validate_package` → `documentation_preview_package`를 실행한다. `manual_apply`만 별도
   반영 요청 뒤 적용한다.

질문 UI는 Gemini CLI가 소유하고 MCP 서버는 질문 schema·정규화 답변·Run 상태를 소유한다.
`documentation_wizard_run_status(run_id)`는 중단된 Run을 읽는 복구 수단이며,
기존 spec_id Tool 10개(`documentation_start`·`answer_question`·기존 validate/preview/apply·requirements·
architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 기본 경로는 Run-scoped candidate lifecycle이다.
실제 TEST/RELEASE 기록은 Run-scoped candidate Tool과 `idempotency_key`를 사용한다.

후보에는 실제 근거가 있는 `FR/AC → TASK → TEST → REL`을 기록하고, 미실행 테스트는 `NOT RUN`으로
표기한다. Markdown 문서가 SSOT이고 HTML은 선택적 설명 자료다. 별도 요청 없이 대상 제품을 구현·테스트·배포하지 않는다.
