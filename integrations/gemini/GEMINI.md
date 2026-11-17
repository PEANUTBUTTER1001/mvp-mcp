# mvp-mcp 문서 패키지 생성 지침 — Gemini CLI

사용자가 `/mvpmcp` 뒤에 제품 아이디어를 입력하면 Web Wizard·브라우저·URL을 사용하지 않는다. 기존
패키지가 있으면 먼저 `<project_root>/.mvpmcp/` 아래의 기존 Run 패키지를 확인하고 아래 native 질문 흐름을 따른다.

1. `ask_user`와 host-native 기타 자유 입력이 현재 제공되는지 확인한다. 없으면 Wizard Run을 만들지 말고
   native 질문 UI가 필요하다고 보고하고 중단한다. 채팅 메시지·브라우저·제출 확인으로 우회하지 않는다.
2. 절대 `project_root`와 작업별 불투명 `request_key`로
   `documentation_start_adaptive_wizard(phase="intake")`를 `write_policy` 없이 호출한다. 기본
   `safe_auto_apply`는 질문 완료 뒤 검증된 문서를 `.mvpmcp/<spec_id>/`에 자동 반영한다. 사용자가
   명시적으로 후보만 요청한 경우에만 `write_policy="generate_only"`를 보낸다.
3. 반환된 질문은 현재 답으로 `visible_when`을 평가하고, 선행 답이 필요한 문항을 같은 묶음에 섞지 않은 채
   Gemini CLI의 `ask_user`로 1~3개씩 표시한다. 질문 `id`별 답을 보존한다. 한 문항에는 제공 선택지를
   최대 3개만 넣는다.
4. `select`의 4~20개 option은 실제 option 두 개와 `다음 선택지`를 반복 표시하며, 이동 값은 답으로 저장하지
   않는다. `multiselect`는 option별 `포함` / `제외` 질문으로 바꿔 최대 3개씩 묻고 `포함`만 배열에 합친다.
   `max_selections`를 넘지 않는다. `allow_other=true`이면 마지막 기타 자유 입력을
   `{"selected": [...], "other_text": "..."}`로 저장한다. `text`·`textarea`는 추천 답 2개와 native 기타
   자유 입력으로만 묻는다.
5. 답을 모두 모으면 `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`로 한 번에
   제출한다. 제출 사실을 다시 채팅에 쓰게 하거나 브라우저 확인을 요구하지 않는다.
6. intake 제출 뒤 실제 저장소 근거를 분석해 1차와 중복되지 않는 3~10개 `design_questions`를 만들어
   같은 `run_id`의 `phase="design"`으로 시작한다. 같은 묶음·선택·기타 규칙으로 `ask_user`와 제출 Tool을
   사용한다. 2차에는 `write_policy` 또는 파일 반영 정책을 다시 묻지 않는다.
7. 2차 제출이 반환한 `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`의 `candidate_lifecycle`을 `candidate_root`의 후보 문서에 반영한 뒤
   `documentation_validate_package` → `documentation_preview_package`를 실행한다. 기본 정책은 충돌이 없을 때
   `.mvpmcp/<spec_id>/`에 문서만 자동 반영하며 기존 Run 폴더는 덮어쓰지 않는다.

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

질문 UI는 Gemini CLI가 소유하고 MCP 서버는 질문 schema·정규화 답변·Run 상태를 소유한다.
`documentation_wizard_run_status(run_id)`는 중단된 Run을 읽는 복구 수단이며, 재개 때는 새 Run이나
`request_key`를 만들지 않고 열린 phase의 질문만 같은 규칙으로 다시 표시한다.
기존 spec_id Tool 10개(`documentation_start`·`answer_question`·기존 validate/preview/apply·requirements·
architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 기본 경로는 Run-scoped candidate lifecycle이다.
실제 TEST/RELEASE 기록은 Run-scoped candidate Tool과 `idempotency_key`를 사용한다.

후보에는 실제 근거가 있는 `FR/AC → TASK → TEST → REL`을 기록하고, 미실행 테스트는 `NOT RUN`으로
표기한다. Markdown 문서가 SSOT이고 HTML은 선택적 설명 자료다. 별도 요청 없이 대상 제품을 구현·테스트·배포하지 않는다.

## 시제품 (문서 반영 후 별도 스킬)

mvp-mcp는 디자인(색·분위기·레이아웃·화면 구성·토큰·MVPDESIGN)과 시제품에 관여하지 않는다. 후보에 `prototype/index.html`을 만들지 않고 문서만 작성·검증·반영한다. 반영(또는 preview)을 마치면 "시제품은 클라이언트의 프로토타입 스킬로 방금 만든 `docs/*.md`를 방안 삼아 만들 수 있다"고 안내만 하고 직접 만들지 않는다. 사용자가 그 스킬을 명시적으로 실행할 때만 시제품을 만든다. 이전 Run에 남은 시제품·MVPDESIGN·토큰은 그대로 둔다.

## 쉬운 설문·구현 단계 (서비스 흐름 v2)

- 선택지는 `option_labels`의 표시명으로 보여 주고 값(option)으로 제출한다. `new_project` 같은 코드값을 사람에게 보이지 않는다.
- `exclusive_options`(예: `ai_suggest` “모르겠어요”)는 다른 보기와 함께 고르지 않는다. `default`는 미리 골라 둔 값이며 그대로 제출되면 AI 추정으로 기록된다.
- `required_unless`가 있는 문항은 나열된 문항 중 하나에 답이 있으면 비워도 된다(예: `pain_points` 또는 `pain_detail`).
- 시작할 때 최초 요청에 **명시된 사실만** `suggested_answers`로 넘긴다(`work_type`·`solution_family`·`primary_surface`·`app_domain_hint`·`initial_audience`). 선택지에 없는 말은 직접 입력으로 넣는다. 예: “안드로이드 날씨앱 만들거야” → `{"work_type": "new_project", "solution_family": ["product_application"], "primary_surface": ["android_app"], "app_domain_hint": {"selected": [], "other_text": "날씨"}}`. 요청에 없는 내용(불편한 점·대상 사용자 등)은 추정해 넣지 않는다.
- `from_request=true` 문항은 요청에서 확정됐으므로 질문 화면에 띄우지 않는다(답을 빼고 제출하면 서버가 채우고 AI 추정으로 기록). 첫 질문 묶음 앞에 시작 응답의 `prefilled_summary`를 한 줄로 보여 주고, 사용자가 고치면 그 문항 값을 직접 제출한다. 만들 것·종류처럼 질문 구성이 바뀌는 값을 고치면 새 `request_key`로 다시 시작한다.
- 1차 제출 결과의 `design_question_guidance`·`required_design_question_ids`를 기준으로 2차 질문을 만든다. `design_must_features`는 분석한 기능 후보로(개수 제한 없음), `confirm_*`는 AI 제안 문장으로 바꾼다. `scope_advice`가 있으면 문서에서 ‘첫 버전 / 다음 버전’ 분리안을 추론으로 표시한다.
- 서버 선택형 문항은 선택지 2~4개(`design_must_features`만 예외)다. 호스트 질문 UI가 한 문항에 3개까지만 보여 주면 위 `다음 선택지`·포함/제외 규칙을 그대로 쓴다. “기타”에 적은 말은 서버가 분류로 해석하므로 코드값으로 바꿔 제출하지 않는다. `work_type=maintenance`(구조·문서 정리)는 후속 `maintenance_kind`를 함께 묻는다.
- 반영(APPLIED) 뒤 사용자가 구현을 요청하면 `implementation_next_task` → `implementation_task_context`로 작업 단위 명세만 읽고, 실제 실행한 TEST만 `implementation_record_evidence`로 기록한다. 루트 AGENTS.md 연결은 `implementation_link_root_agents(mode="preview")` 결과를 보여 주고 사용자가 동의할 때만 `mode="apply"`로 반영한다.
