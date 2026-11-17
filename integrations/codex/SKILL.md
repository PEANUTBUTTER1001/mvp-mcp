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
6. intake 제출 뒤 최초 요청·답변·실제 저장소 근거를 분석해 1차 문항을 반복하지 않는 3~10개
   `design_questions`를 만들고, 같은 `run_id`로 `phase="design"`을 시작한다. 같은 묶음·선택·기타 규칙으로
   `request_user_input` → 답변 제출을 진행한다. 2차에는 `write_policy`나 파일 반영 정책을 다시 묻지 않는다.
6a. 제품 앱의 2차 질문에는 `required_design_question_ids`의 ID를 모두 포함한다: `design_frequent_user_tasks`(라벨: “사용자가 이 제품에서 자주 하는 작업은 무엇인가요?”), 새로 만들기·기능 추가는 `design_must_features`, AI 추정 항목은 `confirm_*`.
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

후보 파일은 `documentation_write_candidate_file`에 `run_id`, `expected_run_version`, `relative_path`,
`content`(전체 본문), `expected_file_sha256`, `idempotency_key`를 전달해 한 파일씩 저장한다.
신규 파일의 hash는 `null`, 수정은 `documentation_package_status`의 `candidate_files[].sha256` 사용.
다음 호출에는 직전 응답의 `run_version` 사용. 후보 폴더에 쓰기 위한 셸 권한 상승은 사용하지 않는다.
응답 유실·`pending_candidate_write` 복구는 **원래 모든 입력과 같은 key**로 재시도한다. `CONFLICT`는
현재 내용·해시를 확인하고 새 key로 해결한다. `REPLAYED`의 저장 해시와 현재 파일 해시는 다를 수 있다.
저장 성공은 전체 검증 완료가 아니며 `status → validate → preview`를 유지한다. 새 Tool이 없으면
서버 재연결·지침 갱신 필요성을 보고한다. 기존 직접 편집은 호환 경로이며 기본 생성 흐름에서는 사용하지 않는다.

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
- `ScreenSpec.states`에 선언된 화면별 상태만 “이 시제품에 대해” 패널의 상태 미리보기로 확인한다. 실제 API·업로드·결제는 수행하지
  않는다.
- 외부 CDN·폰트·네트워크 요청을 넣지 않고, `NON-SSOT` 경계를 화면에서 명확히 알린다.

별도 요청 없이 대상 제품의 코드 구현·테스트 실행·배포를 수행하지 않는다.

## 시제품 (문서 반영 후 별도 스킬)

mvp-mcp는 디자인(색·분위기·레이아웃·화면 구성·토큰·MVPDESIGN)과 시제품에 관여하지 않는다. 후보에 `prototype/index.html`을 만들지 않고 문서만 작성·검증·반영한다. 반영(또는 preview)을 마치면 "시제품은 같은 플러그인의 `mvpmcpprototype` 스킬로 방금 만든 `docs/*.md`를 방안 삼아 만들 수 있다"고 안내만 하고 직접 만들지 않는다. 사용자가 그 스킬을 명시적으로 실행할 때만 시제품을 만든다. 이전 Run에 남은 시제품·MVPDESIGN·토큰은 그대로 둔다.

`design-tokens.json` v3에서는 `palette_source.brand_seed`를 사용자가 선택한 색상으로 보존한다. `oklch-v1`이 제품 맥락에 맞는 semantic palette를 생성하며, 일반 Light/Dark 텍스트 쌍은 최소 4.5:1, 고대비 텍스트 쌍은 최소 7:1 대비 검증을 통과해야 한다. 접근성 보정은 필요한 UI용 tone에만 적용하고 입력색·보정 사유를 함께 기록한다.

## 쉬운 설문·구현 단계 (서비스 흐름 v2)

- 선택지는 `option_labels`의 표시명으로 보여 주고 값(option)으로 제출한다. `new_project` 같은 코드값을 사람에게 보이지 않는다.
- `exclusive_options`(예: `ai_suggest` “모르겠어요”)는 다른 보기와 함께 고르지 않는다. `default`는 미리 골라 둔 값이며 그대로 제출되면 AI 추정으로 기록된다.
- `required_unless`가 있는 문항은 나열된 문항 중 하나에 답이 있으면 비워도 된다(예: `pain_points` 또는 `pain_detail`).
- 시작할 때 최초 요청에 **명시된 사실만** `suggested_answers`로 넘긴다(`work_type`·`solution_family`·`primary_surface`·`app_domain_hint`·`initial_audience`). 선택지에 없는 말은 직접 입력으로 넣는다. 예: “안드로이드 날씨앱 만들거야” → `{"work_type": "new_project", "solution_family": ["product_application"], "primary_surface": ["android_app"], "app_domain_hint": {"selected": [], "other_text": "날씨"}}`. 요청에 없는 내용(불편한 점·대상 사용자 등)은 추정해 넣지 않는다.
- `from_request=true` 문항은 요청에서 확정됐으므로 질문 화면에 띄우지 않는다(답을 빼고 제출하면 서버가 채우고 AI 추정으로 기록). 첫 질문 묶음 앞에 시작 응답의 `prefilled_summary`를 한 줄로 보여 주고, 사용자가 고치면 그 문항 값을 직접 제출한다. 만들 것·종류처럼 질문 구성이 바뀌는 값을 고치면 새 `request_key`로 다시 시작한다.
- 1차 제출 결과의 `design_question_guidance`·`required_design_question_ids`를 기준으로 2차 질문을 만든다. `design_must_features`는 분석한 기능 후보로(개수 제한 없음), `confirm_*`는 AI 제안 문장으로 바꾼다. `scope_advice`가 있으면 문서에서 ‘첫 버전 / 다음 버전’ 분리안을 추론으로 표시한다.
- 서버 선택형 문항은 선택지 2~4개(`design_must_features`만 예외)다. 호스트 질문 UI가 한 문항에 3개까지만 보여 주면 위 `다음 선택지`·포함/제외 규칙을 그대로 쓴다. “기타”에 적은 말은 서버가 분류로 해석하므로 코드값으로 바꿔 제출하지 않는다. `work_type=maintenance`(구조·문서 정리)는 후속 `maintenance_kind`를 함께 묻는다.
- 반영(APPLIED) 뒤 사용자가 구현을 요청하면 `implementation_next_task` → `implementation_task_context`로 작업 단위 명세만 읽고, 실제 실행한 TEST만 `implementation_record_evidence`로 기록한다. 루트 AGENTS.md 연결은 `implementation_link_root_agents(mode="preview")` 결과를 보여 주고 사용자가 동의할 때만 `mode="apply"`로 반영한다.
