---
name: mvpmcp
description: Create a validated Human-AI repository documentation package from a product idea.
---

# mvp-mcp 문서 패키지 생성

사용자가 `/mvpmcp` 뒤에 아이디어를 입력하면 다음 순서를 지킨다.

기존 패키지가 있으면 작업 전에 `<project_root>/.mvpmcp/AGENTS.md`를 먼저 읽고 그 계약을 따른다.

1. `documentation_collect_intake(user_request, project_root)`로 통합 Wizard를 열고 제출 결과의
   `spec_id`를 받는다. `spec_id` 반환은 제출 완료를 뜻하므로 별도 제출 확인을 요구하지 않고 같은
   응답에서 다음 Tool을 계속 호출한다.
2. `documentation_register_requirements`에 BIZ/FR/NFR/DATA/SEC 요구사항과 수용 기준을 등록한다.
3. `documentation_register_architecture`에 화면·흐름·데이터·인터페이스·규칙·오류를 등록한다.
4. `documentation_register_delivery`에 요구사항과 연결된 TASK와 TEST를 등록한다.
5. 저위험 미정값은 `recommended_decisions`로 해소하고, 실제 고위험 미해결 사항만 확인한다.
   권장 설계 결정은 `status=resolved`로 등록한 뒤 `documentation_validate`와
   `documentation_preview`를 호출한다.
6. `.mvpmcp/` 생성·수정·유지·충돌·오래된 파일을 사용자에게 보여주고 명시적 승인을 받는다.
7. 승인 후에만 `documentation_apply(preview_id, approval)`를 호출한다.
8. 실제 생성된 파일 경로와 조건부 문서·OpenAPI·HTML 프로토타입 여부를 간단히 안내한다.

실행하지 않은 테스트는 `NOT RUN`으로 유지한다. `documentation_record_test_run`과
`documentation_record_release`에는 실제 증거만 append-only로 기록한다. 프로토타입은 비권위
설명 자료이며 Markdown 문서가 SSOT다. 별도 요청 없이 대상 제품을 구현·테스트·배포하지 않는다.
