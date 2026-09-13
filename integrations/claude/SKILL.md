---
name: mvpmcp
description: Create a validated Human-AI repository documentation package from a product idea.
---

# mvp-mcp 문서 패키지 생성 — Claude Code

사용자가 `/mvpmcp` 뒤에 아이디어를 입력하면 Web Wizard·localhost URL을 열지 않는다. 기존 패키지가 있으면
먼저 `<project_root>/.mvpmcp/AGENTS.md`를 읽고, 새 문서 생성은 아래 adaptive 경로를 사용한다.

1. 절대 `project_root`와 작업별 불투명 `request_key`를 정해
   `documentation_start_adaptive_wizard(phase="intake")`를 호출한다. 자동 반영을 명시적으로 허용하지
   않은 경우 `write_policy="generate_only"`로 고정한다.
2. 반환된 `questions`를 Claude Code의 `AskUserQuestion`으로 1~3개씩 표시한다. 질문 `id`별 답을
   보존하고, 선택형은 제공된 `options`만 사용한다. 조건부 `visible_when`이 거짓인 문항은 묻지 않는다.
   채팅 메시지·브라우저·제출 확인을 대신 사용하지 않는다.
3. 모든 답을 `answers` 객체로 모아
   `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`에 제출한다. 제출 후 즉시
   다음 작업으로 이어가며 사용자의 별도 “제출” 메시지를 기다리지 않는다.
4. intake 답변과 실제 저장소 근거로 1차 항목을 반복하지 않는 3~7개 `design_questions`를 만들고 같은
   `run_id`로 `phase="design"`을 연다. 다시 `AskUserQuestion`과 제출 Tool을 사용한다. 2차에서는
   `write_policy`·파일 반영 정책을 묻지 않는다.
5. `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`가 반환한 `candidate_lifecycle`을 `candidate_root`의 UTF-8 후보 문서에
   반영한 뒤 `documentation_validate_package` → `documentation_preview_package`를 실행한다.
   `manual_apply`만 별도 반영 요청 뒤 적용한다.

MCP 서버는 질문 schema와 영속 Run만 소유한다. 질문 UI는 Claude Code가 소유하며,
`documentation_wizard_run_status(run_id)`는 중단된 Run의 읽기 전용 복구 수단이다.
기존 spec_id Tool 10개(`documentation_start`·`answer_question`·기존 validate/preview/apply·requirements·
architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 기본 경로는 Run-scoped candidate lifecycle이다.
실제 TEST/RELEASE 기록은 Run-scoped candidate Tool과 `idempotency_key`를 사용한다.

후보에는 실제 근거가 있는 `FR/AC → TASK → TEST → REL` 추적성을 기록하고, 실행하지 않은 테스트는
`NOT RUN`으로 남긴다. Markdown 문서가 SSOT이며 선택 HTML은 설명용이다. 별도 요청 없이 대상 제품을
구현·테스트·배포하지 않는다.
