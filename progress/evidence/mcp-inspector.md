# MCP Inspector 기동 확인

- 확인일: 2026-09-10
- 명령: `.venv-exec/Scripts/uv.exe run mcp dev scripts/inspector_server.py`
- 결과: Inspector Web과 MCP Apps sandbox가 로컬 포트에서 기동됨을 확인한 뒤 종료함.
- Tool 등록·스키마: `tests/test_guardrails.py`와 10개 workflow smoke evaluation으로 자동 검증.
- 정상·오류 동작: `tests/test_documentation.py`, `tests/test_delivery.py`,
  `tests/test_prototype_rendering.py`에서 preview/apply, 충돌, 미정 결정, 증거 게이트를 검증.
- 보안: 실행 중 발급된 일회성 Inspector token은 기록하지 않음.
