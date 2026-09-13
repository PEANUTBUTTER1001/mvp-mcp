---
name: mvpmcp
description: Use mvp-mcp to turn a product idea into a validated Human-AI repository documentation package.
---

# mvp-mcp 문서 패키지 생성 — Codex

사용자가 `/mvpmcp` 뒤에 제품·프로젝트 아이디어를 입력하면, 로컬 Web Wizard나 URL을 열지 말고 이
흐름을 따른다. 기존 패키지가 있으면 먼저 `<project_root>/.mvpmcp/AGENTS.md`를 읽는다.

1. 현재 프로젝트의 절대 경로와 작업 전용의 8자 이상 불투명 `request_key`를 만든다.
   `documentation_start_adaptive_wizard(phase="intake")`를 호출한다. 사용자가 `.mvpmcp/` 자동 반영을
   명시적으로 허용하지 않았다면 최초 `write_policy`는 `generate_only`다.
2. 반환된 `questions`만 Codex의 `request_user_input`으로 묻는다. 한 번에 1~3개씩 표시하고, 각 답의
   질문 `id`를 보존한다. `select`·`multiselect`는 제공된 `options`만 쓰며, `text`·`textarea`는 자유
   입력을 받는다. `visible_when`을 만족하지 않는 문항은 건너뛴다. 질문을 대화 메시지나 브라우저로
   바꾸어 묻지 않는다.
3. 한 단계의 답을 모두 모으면 `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`를
   한 번 호출한다. 사용자가 `제출했음` 같은 추가 메시지를 입력할 때까지 기다리지 않는다.
4. intake 제출 뒤 최초 요청·답변·실제 저장소 근거를 분석해 1차 문항을 반복하지 않는 3~7개
   `design_questions`를 만들고, 같은 `run_id`로 `phase="design"`을 시작한다. 다시
   `request_user_input` → 답변 제출을 진행한다. 2차에는 `write_policy`나 파일 반영 정책을 다시 묻지
   않는다.
5. 2차 제출의 `DRAFT_READY`, `run_version`, `candidate_root`를 받으면 별도 채팅 질문·생성 승인을
   요구하지 말고, 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` →
   `documentation_update_candidate_delivery`를 호출한다. 각 결과의 version을 다음 호출에 사용한다.
   `documentation_package_status`가 반환한 `candidate_lifecycle`을 바탕으로 **서버가 발급한
   candidate_root 안에만** UTF-8 후보 문서를 작성한다.
6. `candidate_sync_required`가 해소되도록 문서를 갱신한 뒤 `documentation_package_status` → `documentation_validate_package` →
   `documentation_preview_package` 순서로 검증한다. `manual_apply`만 별도 반영 요청 뒤
   `documentation_apply_package`를 호출한다. 어떤 정책에서도 unmanaged 사용자 파일을 덮어쓰지 않는다.

질문 UI는 Codex 클라이언트가 소유하고 MCP 서버는 질문 schema·Run 상태·정규화 답변만 다룬다.
`documentation_wizard_run_status(run_id)`는 native 질문이 중단된 뒤 상태를 읽는 복구 수단이다.
기존 spec_id Tool 10개(`documentation_start`, `answer_question`, 기존 validate/preview/apply,
requirements·architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 문서 생성에는 adaptive Wizard와 Run-scoped candidate lifecycle, candidate package Tool만 사용한다.

## 후보 품질 자체 점검

- **구체성**: 대상 사용자·현재 문제·성공 기준을 실제 요구사항·수용 기준에 연결한다.
- **MVP 범위**: 첫 출시의 P0 핵심 흐름과 명시적 비범위를 분리한다.
- **기존 영향**: 기능 추가·리팩터링·결함 수정이면 기존 계약·호환성·회귀 범위를 기록한다.
- **기술 스택 근거**: 저장소·사용자 근거가 없는 기술·버전을 확정 사실처럼 쓰지 않는다.
- **디렉터리 구조 사실성**: 조사 전 경로는 현재 구조로 단정하지 않고 계획 라벨로만 기록한다.
- **추적성**: FR/AC, TASK, TEST는 실제 영향 관계만 연결한다.
- **불확실성 표기**: 권장안·미정 결정은 근거와 다음 확인 방법을 분리한다.

- REQUIREMENTS에는 `FR-`·`AC-`, IMPLEMENTATION_PLAN에는 `TASK-`, TEST_PLAN에는 `TEST-`,
  RELEASE_RUNBOOK에는 `REL-`을 실제 근거와 함께 기록한다.
- `ARCHITECTURE.md`의 기술 스택과 디렉터리 구조를 경로 SSOT로 삼고, 확인하지 않은 내용은
  `RECOMMENDED` 또는 `UNRESOLVED`로 표시한다.
- 실제 실행하지 않은 테스트는 `NOT RUN`이다. 실제 테스트·출시만 각각
  `documentation_record_candidate_test_run`, `documentation_record_candidate_release`에 기록하고,
  같은 재시도에는 고유 `idempotency_key`를 유지한다.
- `prototype/index.html`은 선택적 설명 자료이며 Markdown 문서가 SSOT다. 외부 네트워크 호출이나
  실제 제품 동작을 넣지 않는다.

방향을 바꾸는 고위험 차단 결정만 추가 native 질문 후보로 남기고, 다른 불확실성은 근거와 함께
후보 문서에 기록한다.

## 프로토타입 품질 자체 점검

- `user_flows`가 있으면 정상 단계와 예외 흐름을 함께 보이고, `error_states`가 있으면 사용자 문구와
  복구 경로를 표시한다.
- `ScreenSpec.states`에 선언된 화면별 상태만 Mock으로 선택·확인한다. 실제 API·업로드·결제는 수행하지
  않는다.
- 외부 CDN·폰트·네트워크 요청을 넣지 않고, `NON-SSOT` 경계를 화면에서 명확히 알린다.

별도 요청 없이 대상 제품의 코드 구현·테스트 실행·배포를 수행하지 않는다.
