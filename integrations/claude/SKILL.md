---
name: mvpmcp
description: Start an MVP specification interview through mvp-mcp.
---

# MVP MCP 시작

사용자가 `/mvpmcp` 뒤에 제품 또는 프로젝트 아이디어를 입력하면 다음을 따른다.

1. 아이디어를 바로 설계하거나 일반 채팅 질문으로 바꾸지 말고,
   `ask_web_survey(user_request, project_root)`를 즉시 호출한다.
2. Tool은 단일 페이지 웹 Wizard URL과 `session_id`를 즉시 반환한다. 사용자는 웹 페이지에서
   모든 설문을 한 번에 작성해 제출한다. 제출 대기 상태로 Tool 호출을 유지하지 않는다.
3. Claude가 설문 완료 이벤트를 받을 수 있으면 즉시 `resume_web_survey(session_id)`를 호출한다.
   이벤트를 받을 수 없는 환경에서는 사용자가 후속 메시지를 보낸 뒤
   `get_web_survey_status(session_id)`로 제출 여부를 확인하고, `submitted`이면
   `resume_web_survey(session_id)`를 호출한다.
4. 재개 결과의 `spec_id`를 사용해 `scope_mvp` → `register_requirements` → `confirm_scope` →
   `register_design_contract` → `register_delivery_contract` → `get_mvp_bundle_context` →
   `validate_mvp_bundle` → `export_mvp_bundle` 순서로 진행한다.
5. 성공 시 본문을 채팅에 중복 출력하지 말고 생성된 6개 Markdown 파일의 클릭 가능한 경로와
   포함 내용을 간단히 안내한다.
