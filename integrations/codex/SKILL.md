---
name: mvpmcp
description: Use mvp-mcp to turn a product idea into a validated Human-AI repository documentation package.
---

# mvp-mcp 문서 패키지 생성

사용자가 `/mvpmcp` 뒤에 제품 또는 프로젝트 아이디어를 입력하면 다음을 따른다.

기존 패키지가 있으면 작업 전에 `<project_root>/.mvpmcp/AGENTS.md`를 먼저 읽고 그 계약을 따른다.

1. 현재 프로젝트의 절대 경로를 `project_root`로 사용해
   `documentation_collect_intake(user_request, project_root)`를 호출하고 통합 Wizard 제출을
   기다린다. 이 호출이 `spec_id`를 반환했다면 설문은 이미 제출된 것이다. 사용자에게 `제출함` 같은
   확인 메시지를 요구하거나 턴을 종료하지 말고, 같은 턴에서 반환된 `next_action`을 즉시 계속한다.
   사람과 AI의 협업 여부는 묻지 않는다.
2. `spec_id`가 반환되면 BIZ/FR/NFR/DATA/SEC 요구사항과 수용 기준을
   `documentation_register_requirements`에 등록한다.
3. 화면·흐름·데이터·인터페이스·규칙·오류 설계를
   `documentation_register_architecture`에 등록한다.
4. `FR/AC → TASK → TEST` 추적성을 유지하도록
   `documentation_register_delivery`에 작업과 테스트를 등록한다.
5. 선택 입력이 비었거나 되돌릴 수 있는 저위험 결정이 미정이면 반환된 `recommended_decisions`와
   제품 유형의 보수적 기본값을 채택하고 가정·출처로 기록한다. 보안·법률·결제·개인정보·파괴적
   데이터 변경처럼 오판 비용이 큰 항목만 사용자에게 묻는다. 권장안을 채택한 설계 결정은
   `status=resolved`, `decision`, `source=recommended_default`로 등록한다.
6. `documentation_validate`를 호출한다. 실제 미해결 고위험 결정이나 추적성 누락만 해결한다.
7. `documentation_preview`로 `.mvpmcp/` 변경 목록과 충돌을 보여준다.
8. 파일 적용에 대한 사용자의 명시적 승인을 받은 뒤에만, 반환된 `preview_id`와 승인 문구를
   `documentation_apply`에 전달한다.
9. 생성된 핵심 6개 Markdown과 조건부 `SECURITY.md`, `MIGRATION_PLAN.md`, `openapi.yaml`,
   `prototype/index.html` 중 실제 생성된 파일만 클릭 가능한 경로로 안내한다.

## 검증·출시 기록

- 실제 테스트를 실행한 경우에만 `documentation_record_test_run`으로 PASS/FAIL과 증거를 기록한다.
- 실행하지 않은 검증은 `NOT RUN`으로 유지한다.
- 실제 출시 기록만 `documentation_record_release`에 append-only로 추가한다.
- 프로토타입은 비권위 설명 자료이며 Markdown 문서가 SSOT다.

## 경계

이 Skill은 문서 산출물 생성용이다. 별도 요청 없이 대상 프로젝트의 코드 구현·테스트 실행·배포를
수행하지 않는다. 저장소의 이 파일이 배포 원본이며 설치된 Codex Skill은 릴리스 시 동기화한다.

`documentation_start`는 Wizard 실패 복구 수단이 아니다. `documentation_collect_intake`로 시작한
세션이 있으면 새 세션을 만들지 말고 그 `spec_id`를 계속 사용한다. 확정 후 요구사항을 바꿀 때는
`documentation_register_requirements(mode="upsert")`를 사용하고 반환된 지시에 따라 설계·TASK·TEST를
다시 등록한다. MCP 흐름이 실패해도 임의의 `outputs/` 축약 문서나 별도 prototype Skill로 대체하지 않는다.
