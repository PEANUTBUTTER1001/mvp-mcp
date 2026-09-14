---
name: mvpmcp
description: Use mvp-mcp to turn a product idea into a validated Human-AI repository documentation package.
---

# mvp-mcp 문서 패키지 생성 — Codex

사용자가 `$mvpmcp`(호환 표기: `/mvpmcp`) 뒤에 제품·프로젝트 아이디어를 입력하면, 로컬 Web Wizard나
URL을 열지 말고 이 흐름을 따른다. 기존 패키지는 `<project_root>/.mvpmcp/` 아래 Run 전용 폴더로 구분한다.

1. **Plan 사전 확인:** Codex에서는 먼저 사용자가 `/plan` 또는 `Shift+Tab`으로 Plan 모드를 켜야 한다.
   스킬은 모드를 전환할 수 없다. `request_user_input`이 현재 도구 목록에 없으면 Wizard Run을 만들지 말고
   Plan 모드가 필요하다고 보고하고 중단한다. 대화 텍스트·브라우저·별도 form으로 우회하지 않는다.
2. 현재 프로젝트의 절대 경로와 작업 전용의 8자 이상 불투명 `request_key`를 만든다.
   `documentation_start_adaptive_wizard(phase="intake")`를 호출한다. `write_policy`는 보내지 않는다.
   서버 기본값은 `safe_auto_apply`이며, 질문 완료 뒤 검증된 문서를 `.mvpmcp/<spec_id>/`에 자동 반영한다.
   사용자가 명시적으로 “후보만 저장”을 요청한 경우에만 `write_policy="generate_only"`를 보낸다.
3. 반환된 질문을 **현재 답으로 `visible_when`을 평가한 뒤**, 선행 답이 필요한 문항을 같은 묶음에 섞지 않고
   `request_user_input`으로 1~3개씩 묻는다. 질문 `id`와 답을 보존한다. 한 native 질문창 안에는 각 문항의
   제공 선택지를 최대 3개만 넣는다.
4. 선택형 변환 규칙은 다음과 같다.
   - `select`의 2~3개 option은 그대로 표시한다. 4~20개 option은 실제 option 두 개와 `다음 선택지`를
     반복 표시하고, `다음 선택지`는 답으로 저장하지 않는다.
   - `multiselect`는 각 option을 `포함` / `제외` 질문으로 바꾸고, 최대 3개 문항씩 묶는다. `포함`만 원래
     question id의 배열에 합친다. `max_selections`를 넘는 선택은 묻지 않거나 제출하지 않는다.
   - `allow_other=true`이면 호스트의 마지막 `기타 (직접 입력)` 선택지를 켜고, 사용자가 입력한 문구는
     `{"selected": [...], "other_text": "..."}`로 보존한다. `allow_other=false`이면 기타 입력을 답으로
     저장하지 않는다.
   - `text`·`textarea`는 요청·저장소 근거 기반의 짧은 추천 답 2개와 host-native 기타 자유 입력으로만 묻는다.
     UI가 자유 입력을 제공하지 않으면 텍스트 채팅으로 바꾸지 말고 지원 불가를 보고하고 중단한다.
5. 한 phase의 표시 대상 답을 모두 모으면 `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`를
   한 번 호출한다. 사용자가 `제출했음` 같은 추가 메시지를 입력할 때까지 기다리지 않는다.
6. intake 제출 뒤 최초 요청·답변·실제 저장소 근거를 분석해 1차 문항을 반복하지 않는 3~7개
   `design_questions`를 만들고, 같은 `run_id`로 `phase="design"`을 시작한다. 같은 묶음·선택·기타 규칙으로
   `request_user_input` → 답변 제출을 진행한다. 2차에는 `write_policy`나 파일 반영 정책을 다시 묻지 않는다.
7. 2차 제출의 `DRAFT_READY`, `run_version`, `candidate_root`를 받으면 별도 채팅 질문·생성 승인을
   요구하지 말고, 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` →
   `documentation_update_candidate_delivery`를 호출한다. 각 결과의 version을 다음 호출에 사용한다.
   `documentation_package_status`가 반환한 `candidate_lifecycle`을 바탕으로 **서버가 발급한
   candidate_root 안에만** UTF-8 후보 문서를 작성한다.
8. `candidate_sync_required`가 해소되도록 문서를 갱신한 뒤 `documentation_package_status` → `documentation_validate_package` →
   `documentation_preview_package` 순서로 검증한다. 기본 `safe_auto_apply`는 충돌이 없으면 이 단계에서
   `.mvpmcp/<spec_id>/`에 문서만 반영한다. 기존 `.mvpmcp` 루트와 다른 Run 폴더의 사용자 파일은 건드리지 않는다.

## 기본 문서 저장 종료 규칙

- 기본 Run에서 candidate 작성·검증·preview가 통과하면 문서 패키지 저장은 완료다. 완료 응답의 첫 문장은 반드시
  **`문서 패키지 저장 완료 (.mvpmcp에 문서만 생성됨)`**으로 시작하고, Run별 `.mvpmcp/<spec_id>/` 경로와
  candidate·preview 경로를 제공한다. 실제 제품 소스는 변경하지 않는다.
- 완료 직후 제품 코드 구현 여부를 자동으로 묻지 않는다. `PLEASE IMPLEMENT THIS PLAN`도 구현 승인으로 해석하지 않는다.
  **`MVP 제품 코드 구현 시작`**이라는 명시 요청만 별도 제품 구현 작업의 승인이다. `계획 구현`·`구현할까요` 같은
  모호한 문구로 제품 소스·테스트·빌드·배포를 시작하지 않는다.
- 사용자가 명시적으로 후보만 요청한 `generate_only` Run만 **`문서 후보 저장 완료 (코드 구현 없음)`**으로 끝내고,
  candidate·preview 경로만 제공한다.

질문 UI는 capability가 있는 Codex 호스트가 소유하고 MCP 서버는 질문 schema·Run 상태·정규화 답변만 다룬다.
native 질문이 중단된 기존 Run은 `documentation_wizard_run_status(run_id)`로 재개한다. 재개 때는 새 Run이나
`request_key`를 만들지 않고, 열린 phase의 질문만 위 규칙으로 다시 표시한다.
`INTAKE_OPEN`이면 반환된 `intake_questions`, `DESIGN_OPEN`이면 `design_questions`만 지원되는 native UI로
표시한 뒤 같은 `run_id`·phase로 답변을 제출한다. 이 복구에는 `request_key`를 다시 요구하거나 새 Run을
만들지 않는다. UI가 없으면 schema 반환까지만 확인하고 제출하지 않는다.
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
