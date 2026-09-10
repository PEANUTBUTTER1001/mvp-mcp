# mvp-mcp 문서 패키지 생성 지침

사용자가 `/mvpmcp` 뒤에 제품 아이디어를 입력하면 다음 순서로 처리한다.

기존 패키지가 있으면 작업 전에 `<project_root>/.mvpmcp/AGENTS.md`를 먼저 읽고 그 계약을 따른다.

1. `documentation_collect_intake(user_request, project_root)`로 통합 Wizard를 완료한다.
   `spec_id`가 반환되면 제출은 완료된 것이므로 별도 제출 확인 없이 같은 응답에서 다음 단계를 계속한다.
2. 반환된 `spec_id`에 `documentation_register_requirements`로 요구사항·수용 기준을 등록한다.
3. `documentation_register_architecture`로 화면·흐름·데이터·인터페이스·규칙·오류를 등록한다.
4. `documentation_register_delivery`로 `FR/AC → TASK → TEST` 연결을 등록한다.
5. 저위험 미정값은 `recommended_decisions`로 해소하고 권장 설계 결정은 `status=resolved`로
   등록한다. 실제 고위험 미해결 사항만 확인한 뒤 `documentation_validate`와
   `documentation_preview`를 호출한다.
6. 파일별 CREATE/UPDATE/KEEP/CONFLICT/STALE 결과를 사용자에게 설명하고 명시적 승인을 받는다.
7. 승인 후에만 `documentation_apply(preview_id, approval)`를 호출한다.
8. `.mvpmcp/` 아래 실제 생성된 핵심·조건부·보조 산출물의 경로를 안내한다.

테스트 실행을 추측하지 않는다. 실행하지 않았으면 `NOT RUN`이며, 실제 테스트와 출시만 각각
`documentation_record_test_run`, `documentation_record_release`로 append-only 기록한다. HTML
프로토타입은 설명용이고 Markdown 문서가 SSOT다. 별도 요청 없이 대상 구현·테스트·배포를 하지 않는다.
