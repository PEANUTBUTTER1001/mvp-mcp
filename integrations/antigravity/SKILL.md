---
name: mvpmcp
description: Create a validated Human-AI repository documentation package from a product idea.
---

# mvp-mcp 문서 패키지 생성 — Google Antigravity

사용자가 `$mvpmcp`(호환 표기: `/mvpmcp`) 뒤에 제품·프로젝트 아이디어를 입력하면 Web Wizard·localhost
URL을 열지 않는다. 기존 패키지는 `<project_root>/.mvpmcp/` 아래 Run 전용 폴더로 구분하고 아래 native
질문 흐름을 따른다.

1. Antigravity의 `ask_question`과 multiple-choice·기타 자유 입력 capability가 현재 제공되는지 확인한다.
   하나라도 없으면 Wizard Run을 만들지 말고 native 질문 UI가 필요하다고 보고하고 중단한다. 채팅 메시지,
   브라우저, 별도 form으로 우회하지 않는다.
2. 절대 `project_root`와 작업별 불투명 `request_key`로
   `documentation_start_adaptive_wizard(phase="intake")`를 `write_policy` 없이 호출한다. 기본
   `safe_auto_apply`는 질문 완료 뒤 검증된 문서를 `.mvpmcp/<spec_id>/`에 자동 반영한다. 사용자가
   명시적으로 후보만 요청한 경우에만 `write_policy="generate_only"`를 보낸다.
3. 반환된 질문은 현재 답으로 `visible_when`을 평가하고, 선행 답이 필요한 문항을 같은 묶음에 섞지 않은 채
   `ask_question`으로 1~3개씩 표시한다. 질문 `id`별 답을 보존한다. 한 문항에는 제공 선택지를 최대 3개만
   넣는다.
4. `select`의 4~20개 option은 실제 option 두 개와 `다음 선택지`를 반복 표시하며, 이동 값은 답으로 저장하지
   않는다. `multiselect`는 option별 `포함` / `제외` 질문으로 바꿔 최대 3개씩 묻고 `포함`만 배열에 합친다.
   `max_selections`를 넘지 않는다. `allow_other=true`이면 마지막 기타 자유 입력을
   `{"selected": [...], "other_text": "..."}`로 저장한다. `text`·`textarea`는 추천 답 2개와 native 기타
   자유 입력으로만 묻는다.
5. 한 phase의 답을 모두 모으면 `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`를
   한 번 호출한다. 제출 사실을 다시 채팅에 쓰게 하거나 브라우저 확인을 요구하지 않는다.
6. intake 제출 뒤 실제 저장소 근거를 분석해 1차와 중복되지 않는 3~7개 `design_questions`를 만들어 같은
   `run_id`의 `phase="design"`으로 시작한다. 같은 묶음·선택·기타 규칙으로 `ask_question`과 제출 Tool을
   사용한다. 2차에는 `write_policy` 또는 파일 반영 정책을 다시 묻지 않는다.
6a. 제품 앱의 2차 질문에는 반드시 다음 ID를 포함한다: `design_frequent_user_tasks`(라벨: “사용자가 이 제품에서 자주 하는 작업은 무엇인가요?”), `design_visual_tone`, `design_color_source`. `primary_surface=web_app`이면 `design_web_behavior`도 포함한다.
7. `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`의 `candidate_lifecycle`을 `candidate_root`의 후보 문서에 반영한 뒤
   `documentation_validate_package` → `documentation_preview_package`를 실행한다. 기본 정책은 충돌이 없을 때
   `.mvpmcp/<spec_id>/`에 문서만 자동 반영하며 기존 Run 폴더는 덮어쓰지 않는다.

## 기본 문서 저장 종료 규칙

- 기본 Run의 candidate 작성·검증·preview가 끝나면 완료 응답은 **`문서 패키지 저장 완료 (.mvpmcp에 문서만 생성됨)`**으로
  시작하고 `.mvpmcp/<spec_id>/`·candidate·preview 경로를 제공한다. 제품 코드는 만들지 않는다.
- 제품 코드 구현 여부를 자동으로 묻지 않는다. **`MVP 제품 코드 구현 시작`**만 별도 제품 구현 승인이며,
  `계획 구현`·`구현할까요` 같은 모호한 문구로 대상 제품을 구현·테스트·배포하지 않는다.
- 명시적 `generate_only` Run만 **`문서 후보 저장 완료 (코드 구현 없음)`**으로 끝내고 candidate·preview만 제공한다.

질문 UI는 Antigravity가 소유하고 MCP 서버는 질문 schema·정규화 답변·Run 상태를 소유한다.
`documentation_wizard_run_status(run_id)`는 중단된 Run을 읽는 복구 수단이며, 재개 때는 새 Run이나
`request_key`를 만들지 않고 열린 phase의 질문만 같은 규칙으로 다시 표시한다.
기존 spec_id Tool 10개(`documentation_start`·`answer_question`·기존 validate/preview/apply·requirements·
architecture·delivery·test run·release)은 이번 breaking release에서 **제거 완료**됐다.
새 기본 경로는 Run-scoped candidate lifecycle이다.

후보에는 실제 근거가 있는 `FR/AC → TASK → TEST → REL`을 기록하고, 미실행 테스트는 `NOT RUN`으로
표기한다. Markdown 문서가 SSOT이고 HTML은 선택적 설명 자료다. 별도 요청 없이 대상 제품을 구현·테스트·배포하지 않는다.

## 디자인 산출물 준수

제품 앱 후보에는 서버가 만든 `docs/MVPDESIGN.md`, `docs/design-tokens.json`, `prototype/index.html`, `prototype/REVIEW.md`를 유지한다. 새 화면은 MVPDESIGN 7절에 먼저 추가하고, 색상·간격·타이포그래피는 토큰을 사용한다. 네 파일의 `design_hash`를 함께 갱신하지 않은 디자인 변경은 preview하지 않는다.

디자인 문서의 1~10절은 제품별 핵심 표준이며, 11~14절은 token·상태·검증 보조 계약이다. `web`, `mobile`, `desktop` 중 실제 `platform_targets`를 확인하고, `cross_platform`이면 선택된 모든 프로파일의 수용 기준을 지킨다. HTML 컴포넌트에 직접 Hex·임의 여백·`style=` 속성을 넣지 않으며 semantic token만 사용한다. 375px·768px·1440px, 키보드 포커스, 오류 대상 연결, 빈 상태와 선언된 삭제 확인·되돌리기, 핵심 Mock 흐름을 실제로 확인하지 않았다면 REVIEW에는 `NOT RUN`으로 기록한다.

`design-tokens.json` v3에서는 `palette_source.brand_seed`를 사용자가 선택한 색상으로 보존한다. `oklch-v1`이 제품 맥락에 맞는 semantic palette를 생성하며, 일반 Light/Dark 텍스트 쌍은 최소 4.5:1, 고대비 텍스트 쌍은 최소 7:1 대비 검증을 통과해야 한다. 접근성 보정은 필요한 UI용 tone에만 적용하고 입력색·보정 사유를 함께 기록한다.
