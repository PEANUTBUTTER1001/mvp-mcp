# HANDOFF.md — 현재 인수인계

> 최종 갱신: 2026-09-10
> 현재 상태: 가이드 기반 고도화 구현·자동 검증·Codex 실사용 산출물 수용 확인 완료

## 먼저 읽을 문서

1. `AGENTS.md` — 계층·조립·검증 절대 규칙
2. `README.md` — 현재 공개 워크플로와 `.mvpmcp/` 산출 계약
3. 이 문서 — 구현 상태·제약·남은 운영 조치
4. `progress/PROGRESS.md` — 작업별 시간순 기록

제품 문서 계약의 유일한 기준은 사용자가 제공한
`HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.md`다. 고정 원본 SHA-256은
`2c4d944af733a37e4d6b4925695fb261cb30a0715087e26505ab35544702f96d`이며
`references/HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.sha256`과 coverage fixture가 이를 확인한다.
다른 계획 문서는 제품 계약의 근거로 사용하지 않는다.

## 현재 제품 계약

```text
documentation_collect_intake
→ documentation_register_requirements
→ documentation_register_architecture
→ documentation_register_delivery
→ documentation_validate
→ documentation_preview
→ 사용자 명시 승인
→ documentation_apply
```

실제 테스트·출시가 있으면 각각 `documentation_record_test_run`,
`documentation_record_release`로 append-only 기록한다. 실행하지 않은 결과는 `NOT RUN`이다.

| 입력 조건 | Markdown 프로파일 | 보조 산출물 |
|---|---|---|
| 일반 Wizard | 핵심 6문서 | 조건에 따라 OpenAPI·HTML |
| 명시적 PROTOTYPE_4 + 저위험 확인 4개 | 핵심 4문서 | HTML 선택과 독립 |
| 인증·개인정보·결제·위험 | 핵심 6 + SECURITY_PRIVACY | API/HTML 선택 가능 |
| 기존 데이터 변경 | 핵심 6 + MIGRATION_PLAN | API/HTML 선택 가능 |
| 보안 + 데이터 변경 | 핵심 6 + 조건부 2 | API/HTML 선택 가능 |

출력은 `<project_root>/.mvpmcp/` 안에서만 생성한다. `README.md`와 `AGENTS.md`는 패키지
루트, 핵심·조건부 문서는 `docs/`, OpenAPI는 `api/`, 선택 HTML은 `prototype/index.html`에 둔다.
`.manifest.json`은 관리 파일 해시·프로토타입 원본 계약 해시·승인 정보를 보유한다.

## 구현된 안전·품질 계약

- 가이드의 기본 6문서, 조건부 2문서, 4문서용 DELIVERY_CHECKLIST 전체 목차를 코드 계약으로 관리한다.
- BIZ/FR/NFR/DATA/SEC, AC, TASK, TEST, REL 식별자와 참조를 검증한다.
- 저위험 빈값·`계획 미정`은 보수적 권장값으로 해소하고 결정 출처·근거·신뢰도를 기록한다.
- 설계 결정은 `open`/`resolved`를 구분하며 실제 open 항목만 preview를 차단한다.
- Wizard가 `spec_id`를 반환하면 제출 완료이므로 별도 채팅 확인 없이 같은 턴에서 후속 Tool을 진행한다.
- 확정 후 요구사항은 stable ID upsert로 개정하고 revision을 올리며 설계·TASK·TEST를 안전하게 무효화한다.
- TEST PASS와 RELEASED는 실행자·시각·증거 등 필수 근거 없이는 생성할 수 없다.
- preview는 CREATE/UPDATE_MANAGED/KEEP_VALID/CONFLICT_UNMANAGED와 STALE을 보고한다.
- unmanaged 파일을 덮어쓰지 않고, preview 뒤 파일·manifest 변경을 SHA-256으로 재검사한다.
- 적용은 임시 staging·backup·교체·실패 복구 순서로 수행하며 stale 파일을 자동 삭제하지 않는다.
- HTML은 단일 파일, CSP `connect-src 'none'`, mock-only, NON-SSOT이며 실제 Chromium에서 검증한다.
- 구형 2문서·소문자 6문서 Tool, exporter, 모델, 렌더링 경로는 삭제했다.

## 검증 기록

| 검증 | 결과 |
|---|---|
| `uv run ruff check src tests scripts` | 통과 |
| `uv run black --check src tests scripts` | 통과 |
| `uv run mypy src` | 통과 |
| `uv run pytest -q` | 50 passed; Chromium 브라우저 테스트 포함 |
| 개발 환경 점검 | Python·uv·Node·npx·MCP CLI·Playwright·Chromium launch READY |
| MCP Inspector | 로컬 Web·sandbox 기동 확인 후 종료 |
| `scripts/run_mcp_evaluations.py` | 10/10 passed |

### 2026-09-10 실클라이언트 결함 보강 검증

| 검증 | 결과 |
|---|---|
| `ruff check src tests scripts` | 통과 |
| `black --check src tests scripts` | 통과 |
| `mypy src` | 통과 |
| `pytest -q --basetemp .pytest-tmp-final` | 55 passed |
| `scripts/run_mcp_evaluations.py` | 10/10 passed |
| 개인 플러그인 구조 검증 | 통과 |
| 설치 Skill SHA-256 동기화 | 원본과 일치 |
| 새 Codex 작업의 고도화 산출물 생성 | 통과 — 2026-09-10 사용자 확인 (`확인됨`) |

Black과 pytest는 샌드박스 사용자가 사용자 프로필 캐시에 쓸 수 없어 경고가 날 수 있으나 검사와
테스트 결과에는 영향이 없다.

## 운영 시 주의점

- 현재 초안·preview는 프로세스 메모리 상태이므로 서버 재시작 후 사라진다.
- 실행 중이던 기존 MCP 프로세스가 원래 `.venv` 실행 파일을 잠가, 이번 작업은 `.venv-exec` 격리
  환경에서 검증했다. 기존 서버를 종료한 다음 표준 `.venv`를 다시 `uv sync --group dev`하면 된다.
- 개인 Codex 플러그인은 `0.2.0+codex.20260910103953`으로 재설치했으며 설치 Skill과
  `integrations/codex/SKILL.md` 해시가 일치한다. 새 작업에서만 갱신된 Skill·Tool schema를 확인할 수 있다.
- `scripts/sync_codex_plugin.py`로 배포 원본을 동기화하고 설치 캐시는 직접 수정하지 않는다.
- Codex 연동 Skill의 완료 안내에는 조건부 보안 문서가 `SECURITY.md`로 적혀 있지만 실제 생성
  계약은 `SECURITY_PRIVACY.md`다. 생성 기능에는 영향이 없으나 다음 플러그인 릴리스에서 원본과
  설치 캐시를 함께 갱신해야 한다 (`확인됨`).
- 이번 사용자 수용 확인은 새 Codex 작업의 최종 고도화 산출물이 정상 생성된 범위다. Claude·Gemini
  등 다른 MCP 클라이언트의 동일 흐름은 이번 마일스톤에서 실사용 검증하지 않았다 (`미확인`).
- 실제 대상 프로젝트 코드 구현·테스트 실행·배포는 이 서버의 책임이 아니다.

## 다음 마일스톤

실제로 생성된 `.mvpmcp/` 패키지 한 건을 가이드의 문서별 목적·전체 목차·ID 추적성·품질 게이트와
대조해 **내용 품질 수용 리뷰**를 수행한다. 먼저 누락·빈약한 내용·문서 간 모순을 증거와 함께
보고하고, 코드·Skill·플러그인 수정은 사용자가 개선안을 승인한 뒤 별도 구현 작업으로 진행한다.

함께 처리할 작은 유지보수 후보는 `integrations/codex/SKILL.md`의 `SECURITY.md` 안내를
`SECURITY_PRIVACY.md`로 바로잡고 공식 동기화·재설치 흐름으로 원본과 설치본을 일치시키는 것이다.

## 다음 채팅 시작 문구

```text
먼저 AGENTS.md, README.md, HANDOFF.md, progress/PROGRESS.md를 읽어줘.

다음 마일스톤은 실제로 생성된 .mvpmcp/ 패키지 한 건을
HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.md의 문서별 목적·전체 목차·ID 추적성·품질 게이트와
대조하여 내용 품질을 수용 리뷰하는 것이다. 허용 범위는 생성 산출물과 현재 계약의 읽기·분석,
누락·빈약한 내용·문서 간 모순의 증거 기반 보고, 그리고 승인 가능한 최소 개선안 작성까지다.
대상 제품 구현, 기능 추가, 외부 배포 등으로 범위를 확대하지 말아줘.
코드·Skill·플러그인·의존성 변경은 분석 결과와 최소 변경 계획을 먼저 보고하고 내 명시적 승인을
받은 뒤에만 진행해줘.
```
