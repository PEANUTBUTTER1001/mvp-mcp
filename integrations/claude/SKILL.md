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
   Claude Code의 `AskUserQuestion`으로 1~3개씩 표시한다. 질문 `id`별 답을 보존한다. 한 문항에는 제공
   선택지를 최대 3개만 넣는다.
4. `select`의 4~20개 option은 실제 option 두 개와 `다음 선택지`를 반복 표시하며, 이동 값은 답으로 저장하지
   않는다. `multiselect`는 option별 `포함` / `제외` 질문으로 바꿔 최대 3개씩 묻고 `포함`만 배열에 합친다.
   `max_selections`를 넘지 않는다. `allow_other=true`이면 마지막 기타 자유 입력을
   `{"selected": [...], "other_text": "..."}`로 저장한다. `text`·`textarea`는 추천 답 2개와 native 기타
   자유 입력으로만 묻는다.
5. 모든 답을 `answers` 객체로 모아
   `documentation_submit_adaptive_wizard_answers(run_id, phase, answers)`에 제출한다. 제출 후 즉시
   다음 작업으로 이어가며 사용자의 별도 “제출” 메시지를 기다리지 않는다.
6. intake 답변과 실제 저장소 근거로 1차 항목을 반복하지 않는 3~7개 `design_questions`를 만들고 같은
   `run_id`로 `phase="design"`을 연다. 같은 묶음·선택·기타 규칙으로 `AskUserQuestion`과 제출 Tool을
   사용한다. 2차에서는 `write_policy`·파일 반영 정책을 묻지 않는다.
6a. 제품 앱의 2차 질문에는 반드시 다음 ID를 포함한다: `design_frequent_user_tasks`(라벨: “사용자가 이 제품에서 자주 하는 작업은 무엇인가요?”), `design_visual_tone`, `design_color_source`. `primary_surface=web_app`이면 `design_web_behavior`도 포함한다.
7. `DRAFT_READY` 뒤 최신 `expected_run_version`으로
   `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   `documentation_package_status`가 반환한 `candidate_lifecycle`을 `candidate_root`의 UTF-8 후보 문서에
   반영한 뒤 `documentation_validate_package` → `documentation_preview_package`를 실행한다. 기본 정책은
   충돌이 없을 때 `.mvpmcp/<spec_id>/`에 문서만 자동 반영하며 기존 Run 폴더는 덮어쓰지 않는다.

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

## 디자인 산출물 준수

제품 앱 후보에는 서버가 만든 `docs/MVPDESIGN.md`, `docs/design-tokens.json`, `prototype/index.html`, `prototype/REVIEW.md`를 유지한다. 새 화면은 MVPDESIGN 7절에 먼저 추가하고, 색상·간격·타이포그래피는 토큰을 사용한다. 네 파일의 `design_hash`를 함께 갱신하지 않은 디자인 변경은 preview하지 않는다.
