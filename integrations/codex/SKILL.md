---
name: mvpmcp
description: Use mvp-mcp to turn a product idea into a validated six-document MVP package. Invoke when the user starts with /mvpmcp followed by an idea.
---

# MVP MCP 시작

사용자가 `/mvpmcp` 뒤에 제품 또는 프로젝트 아이디어를 입력하면 다음을 따른다.

1. 아이디어를 바로 설계하거나 일반 채팅 질문으로 바꾸지 말고,
   `ask_web_survey(user_request, project_root)`를 즉시 호출한다. `project_root`는 현재 새 프로젝트의
   작업 루트 절대 경로다.
2. Tool은 단일 페이지 웹 Wizard URL과 `session_id`를 즉시 반환한다. 사용자는 웹 페이지에서
   모든 설문을 한 번에 작성해 제출한다. Tool 호출을 설문 제출까지 대기 상태로 두지 않는다.
3. Codex 클라이언트가 제출 완료 이벤트를 현재 대화로 전달할 수 있으면 즉시
   `resume_web_survey(session_id)`를 호출한다. 그렇지 않으면 사용자의 다음 메시지에서
   `get_web_survey_status(session_id)`로 상태를 확인한다. 상태가 `submitted`이면
   `resume_web_survey(session_id)`를 호출하고, `open`이면 설문 링크를 다시 안내한다.
4. 재개 결과의 `spec_id`를 사용해 `scope_mvp` → `register_requirements` → `confirm_scope` →
   `register_design_contract` → `register_delivery_contract` → `get_mvp_bundle_context` →
   `validate_mvp_bundle` → `export_mvp_bundle` 순서로 진행한다.
5. 성공 시 문서 본문을 채팅에 중복 출력하지 않는다. `<project_root>/mvpmcp/` 아래 생성된 6개
   Markdown 파일의 클릭 가능한 경로와 각 파일의 포함 내용을 간략히 안내한다.

## 경계

- 이 Skill은 문서 산출물 생성용이다. 대상 프로젝트의 코드 구현·테스트 실행·배포는 수행하지 않는다.
- 이 파일은 저장소의 배포 원본이다. Codex에서 실제로 자동 적용하려면 Codex Plugin에 포함하거나
  `C:\Users\user\.codex\skills\mvpmcp\SKILL.md`에 설치된 버전도 같은 내용으로 갱신해야 한다.
