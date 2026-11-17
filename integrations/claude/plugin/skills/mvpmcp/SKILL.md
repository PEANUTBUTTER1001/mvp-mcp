---
name: mvpmcp
description: Create a validated Human-AI repository documentation package from a product idea.
---

# mvp-mcp 문서 패키지 생성 — Claude Code

사용자가 `/mvpmcp` 뒤에 아이디어를 입력하면 Web Wizard·localhost URL을 열지 않는다. 기존 패키지가 있으면
먼저 `<project_root>/.mvpmcp/` 아래의 기존 Run 패키지를 확인하고, 새 문서 생성은 아래 adaptive 경로를 사용한다.

1. `AskUserQuestion`과 host-native 기타 자유 입력이 현재 제공되는지 확인한다. 없으면 Wizard Run을 만들지
   말고 native 질문 UI가 필요하다고 보고하고 중단한다. 채팅 메시지·브라우저·제출 확인으로 우회하지 않는다.
2. 절대 `project_root`와 작업별 불투명 `request_key`를 정해
   `documentation_start_adaptive_wizard(phase="intake")`를 `write_policy` 없이 호출한다. 기본
   `safe_auto_apply`는 질문 완료 뒤 검증된 문서를 `.mvpmcp/<spec_id>/`에 자동 반영한다. 사용자가
   명시적으로 후보만 요청한 경우에만 `write_policy="generate_only"`를 보낸다.
3. 반환된 질문은 현재 답으로 `visible_when`을 평가하고, 선행 답이 필요한 문항을 같은 묶음에 섞지 않은 채
   Claude Code의 `AskUserQuestion`으로 **한 번에 최대 4문항** 표시한다. 질문 `id`별 답을 보존한다.
   서버 선택형 문항의 선택지는 2~4개이므로 `option_labels` 표시명을 **그대로 1:1**로 넣는다(묶기·페이지 넘김 없음).
4. 표시 규칙:
   - `multiselect`는 `multiSelect: true`로 묻고 `max_selections`·`exclusive_options`를 넘는 조합은 제출하지 않는다.
   - `AskUserQuestion`의 자동 “기타” 입력은 `allow_other=true`이면 `{"selected": [...], "other_text": "..."}`로
     저장한다. `allow_other=false` 문항에 기타 입력이 오면 저장하지 말고 같은 문항을 한 번 더 묻는다.
   - `design_must_features`(개수 제한 없음)만 선택지가 4개를 넘을 수 있다. 4개씩 나눈 복수 선택 문항으로 묻고
     고른 값을 원래 id 배열에 합친다. 남은 후보가 1개면 `포함` / `이번엔 안 함` 두 선택지로 묻는다.
   - `text`·`textarea`는 요청·저장소 근거 기반 추천 답 2개와 자동 “기타” 입력으로 묻는다.
5. 모든 답을 `answers` 객체로 모아
   `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`에 제출한다. 제출 후 즉시
   다음 작업으로 이어가며 사용자의 별도 “제출” 메시지를 기다리지 않는다.
6. intake 답변과 실제 저장소 근거로 1차 항목을 반복하지 않는 3~10개 `design_questions`를 만들고 같은
   `run_id`로 `phase="design"`을 연다. 같은 묶음·선택·기타 규칙으로 `AskUserQuestion`과 제출 Tool을
   사용한다. 2차에서는 `write_policy`·파일 반영 정책을 묻지 않는다.
6a. 제품 앱의 2차 질문에는 `required_design_question_ids`의 ID를 모두 포함한다: `design_frequent_user_tasks`(라벨: “사용자가 이 제품에서 자주 하는 작업은 무엇인가요?”), 새로 만들기·기능 추가는 `design_must_features`, AI 추정 항목은 `confirm_*`.
7. `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`가 반환한 `candidate_lifecycle`을 `candidate_root`의 UTF-8 후보 문서에
   반영한 뒤 `documentation_validate_package` → `documentation_preview_package`를 실행한다. 기본 정책은
   충돌이 없을 때 `.mvpmcp/<spec_id>/`에 문서만 자동 반영하며 기존 Run 폴더는 덮어쓰지 않는다.

후보 파일은 `documentation_write_candidate_file`에 `run_id`, `expected_run_version`, `relative_path`,
`content`(전체 본문), `expected_file_sha256`, `idempotency_key`를 전달해 한 파일씩 저장한다.
신규 파일의 hash는 `null`, 수정은 `documentation_package_status`의 `candidate_files[].sha256` 사용.
다음 호출에는 직전 응답의 `run_version` 사용. 후보 폴더에 쓰기 위한 셸 권한 상승은 사용하지 않는다.
응답 유실·`pending_candidate_write` 복구는 **원래 모든 입력과 같은 key**로 재시도한다. `CONFLICT`는
현재 내용·해시를 확인하고 새 key로 해결한다. `REPLAYED`의 저장 해시와 현재 파일 해시는 다를 수 있다.
저장 성공은 전체 검증 완료가 아니며 `status → validate → preview`를 유지한다. 새 Tool이 없으면
서버 재연결·지침 갱신 필요성을 보고한다. 기존 직접 편집은 호환 경로이며 기본 생성 흐름에서는 사용하지 않는다.

## 기본 문서 저장 종료 규칙

- 기본 Run의 candidate 작성·검증·preview가 끝나면 완료 응답은 **`문서 패키지 저장 완료 (.mvpmcp에 문서만 생성됨)`**으로
  시작하고 `.mvpmcp/<spec_id>/`·candidate·preview 경로를 제공한다. 제품 코드는 만들지 않는다.
- 제품 코드 구현 여부를 자동으로 묻지 않는다. **`MVP 제품 코드 구현 시작`**만 별도 제품 구현 승인이며,
  `계획 구현`·`구현할까요` 같은 모호한 문구로 대상 제품을 구현·테스트·배포하지 않는다.
- 명시적 `generate_only` Run만 **`문서 후보 저장 완료 (코드 구현 없음)`**으로 끝내고 candidate·preview만 제공한다.

MCP 서버는 질문 schema와 영속 Run만 소유한다. 질문 UI는 Claude Code가 소유하며,
`documentation_wizard_run_status(run_id)`는 중단된 Run의 읽기 전용 복구 수단이다. 재개 때는 새 Run이나
`request_key`를 만들지 않고 열린 phase의 질문만 같은 규칙으로 다시 표시한다.
기존 spec_id Tool 10개(`documentation_start`·`answer_question`·기존 validate/preview/apply·requirements·
architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 기본 경로는 Run-scoped candidate lifecycle이다.
실제 TEST/RELEASE 기록은 Run-scoped candidate Tool과 `idempotency_key`를 사용한다.

후보에는 실제 근거가 있는 `FR/AC → TASK → TEST → REL` 추적성을 기록하고, 실행하지 않은 테스트는
`NOT RUN`으로 남긴다. Markdown 문서가 SSOT이며 선택 HTML은 설명용이다. 별도 요청 없이 대상 제품을
구현·테스트·배포하지 않는다.

## 시제품 (문서 반영 후 별도 스킬)

mvp-mcp는 디자인(색·분위기·레이아웃·화면 구성·토큰·MVPDESIGN)과 시제품에 관여하지 않는다. 후보에 `prototype/index.html`을 만들지 않고 문서만 작성·검증·반영한다. 반영(또는 preview)을 마치면 "시제품은 같은 플러그인의 `/mvpmcp:mvpmcpprototype`로 방금 만든 `docs/*.md`를 방안 삼아 만들 수 있다"고 안내만 하고 직접 만들지 않는다. 사용자가 그 스킬을 명시적으로 실행할 때만 시제품을 만든다. 이전 Run에 남은 시제품·MVPDESIGN·토큰은 그대로 둔다.

`design-tokens.json` v3에서는 `palette_source.brand_seed`를 사용자가 선택한 색상으로 보존한다. `oklch-v1`이 제품 맥락에 맞는 semantic palette를 생성하며, 일반 Light/Dark 텍스트 쌍은 최소 4.5:1, 고대비 텍스트 쌍은 최소 7:1 대비 검증을 통과해야 한다. 접근성 보정은 필요한 UI용 tone에만 적용하고 입력색·보정 사유를 함께 기록한다.

## 쉬운 설문·구현 단계 (서비스 흐름 v2)

- 선택지는 `option_labels`의 표시명으로 보여 주고 값(option)으로 제출한다. `new_project` 같은 코드값을 사람에게 보이지 않는다.
- `exclusive_options`(예: `ai_suggest` “모르겠어요”)는 다른 보기와 함께 고르지 않는다. `default`는 미리 골라 둔 값이며 그대로 제출되면 AI 추정으로 기록된다.
- `required_unless`가 있는 문항은 나열된 문항 중 하나에 답이 있으면 비워도 된다(예: `pain_points` 또는 `pain_detail`).
- 시작할 때 최초 요청에 **명시된 사실만** `suggested_answers`로 넘긴다(`work_type`·`solution_family`·`primary_surface`·`app_domain_hint`·`initial_audience`). 선택지에 없는 말은 직접 입력으로 넣는다. 예: “안드로이드 날씨앱 만들거야” → `{"work_type": "new_project", "solution_family": ["product_application"], "primary_surface": ["android_app"], "app_domain_hint": {"selected": [], "other_text": "날씨"}}`. 요청에 없는 내용(불편한 점·대상 사용자 등)은 추정해 넣지 않는다.
- `from_request=true` 문항은 요청에서 확정됐으므로 질문 화면에 띄우지 않는다(답을 빼고 제출하면 서버가 채우고 AI 추정으로 기록). 첫 질문 묶음 앞에 시작 응답의 `prefilled_summary`를 한 줄로 보여 주고, 사용자가 고치면 그 문항 값을 직접 제출한다. 만들 것·종류처럼 질문 구성이 바뀌는 값을 고치면 새 `request_key`로 다시 시작한다.
- 1차 제출 결과의 `design_question_guidance`·`required_design_question_ids`를 기준으로 2차 질문을 만든다. `design_must_features`는 분석한 기능 후보로(개수 제한 없음), `confirm_*`는 AI 제안 문장으로 바꾼다. `scope_advice`가 있으면 문서에서 ‘첫 버전 / 다음 버전’ 분리안을 추론으로 표시한다.
- 서버 선택형 문항은 선택지 2~4개(`design_must_features`만 예외)다. “기타”에 적은 PC 프로그램·메신저·분야(예: 헬스) 같은 말은 서버가 분류로 해석하므로 코드값으로 바꿔 제출하지 않는다. `work_type=maintenance`(구조·문서 정리)는 후속 `maintenance_kind`를 함께 묻는다.
- 반영(APPLIED) 뒤 사용자가 구현을 요청하면 `implementation_next_task` → `implementation_task_context`로 작업 단위 명세만 읽고, 실제 실행한 TEST만 `implementation_record_evidence`로 기록한다. 루트 AGENTS.md 연결은 `implementation_link_root_agents(mode="preview")` 결과를 보여 주고 사용자가 동의할 때만 `mode="apply"`로 반영한다.
