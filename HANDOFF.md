# HANDOFF.md — 현재 인수인계

> **최종 갱신:** 2026-09-08  
> **목적:** 다음 세션이 현재 MVP 문서 생성 서버의 사실·제약·다음 작업만 읽고 안전하게 이어간다.

## 먼저 읽을 문서

1. [AGENTS.md](AGENTS.md) — 계층·조립·테스트 절대 규칙
2. [README.md](README.md) — 현재 사용자 흐름·도구·6개 산출물 계약
3. 이 문서 — 현 상태·검증 근거·다음 마일스톤
4. 필요 시 [integrations/codex/SKILL.md](integrations/codex/SKILL.md) — Codex `/mvpmcp` 연동 원본

`PLAN.md`, `PROPOSAL.md`, `TEMPLATE.md`, `ARCHITECTURE_REVIEW.md`는 초기 설계·템플릿 배경 기록이다.
현재 도구 수·문서 수·Wizard 흐름의 기준으로 사용하지 않는다.

## 현재 상태

| 항목 | 상태 | 근거 신뢰도 |
|---|---|---|
| 6개 실행 계약 문서 생성 | 완료 | 확인됨 |
| `<project_root>/mvpmcp/` 고정 경로 내보내기 | 완료 | 확인됨 |
| REQ-ID·TASK-ID·TEST-ID·검증 근거 추적성 검사 | 완료 | 확인됨 |
| 단일 페이지 웹 Wizard | 완료 | 확인됨 |
| 비차단 설문 세션·30분 만료·상태/재개 Tool | 완료 | 확인됨 |
| Codex·Claude·Gemini 연동 원본 문서 | 완료 | 확인됨 |
| Codex Plugin의 설문 제출 자동 재개 어댑터 | 연기 | 확인됨 |
| 현재 전체 품질 게이트의 정확한 최신 실행 결과 | 미확인 | 충돌 |

## 현재 제품 계약

### 기본 흐름

```text
/mvpmcp <아이디어>
→ ask_web_survey(user_request, project_root)
→ 단일 페이지 웹 Wizard 설문 제출
→ resume_web_survey(session_id)
→ scope_mvp
→ register_requirements / confirm_scope / register_design_contract
→ register_delivery_contract
→ validate_mvp_bundle
→ export_mvp_bundle
→ <project_root>/mvpmcp/의 6개 Markdown 파일 안내
```

생성 파일은 `requirements.md`, `proposal.md`, `plan.md`, `backlog.md`, `test-plan.md`,
`verification-report.md`다. 이 서버는 **문서 산출물만** 책임지며, 대상 프로젝트의 구현·테스트 실행·배포를 하지 않는다.

### 호환 기능과 생성 경로

- 기존 `finalize_spec`·`export_spec`은 2문서 호환 기능으로 유지한다.
- `Settings.output_dir`의 기본값은 저장소 루트 `output/`이다. 서버 부팅 시 호환 기능의 쓰기 가능 여부를 검사하면서 빈 `output/`을 만들 수 있다.
- 주 산출물은 `output/`이 아니라 대상 프로젝트 루트의 `mvpmcp/`이다.

## 알려진 한계와 주의점

1. MCP 서버만으로는 Codex 클라이언트가 웹 Wizard의 제출 완료 이벤트를 자동 수신해
   `resume_web_survey`를 호출하도록 만들 수 없다. 이벤트 어댑터가 없는 환경에서는 다음 사용자 메시지에서
   `get_web_survey_status`를 확인한 뒤 재개해야 한다.
2. `presentation/prompts/workflow.py`의 `WORKFLOW_INSTRUCTIONS` 일부는 비차단 세션 도입 전의
   “설문 Tool이 `spec_id`를 반환” 흐름을 아직 포함한다. 다음 코드 변경 때 `session_id` →
   `resume_web_survey` 흐름으로 정합성을 맞춰야 한다.
3. 저장소의 `integrations/codex/SKILL.md`는 배포 원본이다. 실제 Codex에서 자동 적용되는 전역 Skill 또는
   Plugin 패키지의 설치본은 별도 동기화가 필요하다.
4. 메모리 기반 초안·설문 세션은 서버 재시작 뒤 사라진다. 영속화는 현재 범위 밖이다.

## 검증 기록

| 명령 또는 근거 | 결과 | 신뢰도 |
|---|---|---|
| `git diff --check` | 통과 | 확인됨 |
| `quick_validate.py integrations/codex` (`PYTHONUTF8=1`) | `Skill is valid!` | 확인됨 |
| `uv run pytest -q --basetemp "%TEMP%\\mvp-mcp-pytest-local-3"` | 사용자 보고: 51 passed | 확인됨 |
| `progress/PROGRESS.md`의 ruff·black·mypy·pytest 기록 | 52 passed로 기록됨 | 충돌 |

테스트 수가 51/52로 충돌하므로, 다음 코드 변경 전 또는 PR 직전에 사용자 터미널에서 전체 품질 게이트를 다시 실행해 단일 결과로 확정한다.

```bat
uv run ruff check && uv run black --check src tests && uv run mypy src && uv run pytest -q --basetemp "%TEMP%\mvp-mcp-pytest-final"
```

## 다음 마일스톤

**범위:** Codex Plugin 또는 클라이언트 어댑터가 설문 제출 완료를 감지해 `resume_web_survey(session_id)`를 자동 호출하도록 연결하고, 비차단 세션 기준으로 서버 지시문과 테스트를 정합화한다.

**범위 확장 금지:** 문서 생성 서버에 대상 MVP의 구현·실제 테스트 실행·배포·세션 영속 DB를 추가하지 않는다. 해당 항목은 별도 승인 후 다룬다.

**시작 순서:**

1. 현재 Plugin 설치 위치·Skill 로드 경로·MCP Tool 가용 여부를 읽기 전용으로 확인한다.
2. Codex가 외부 웹 설문 완료 이벤트를 수신할 수 있는 공식 어댑터 지점이 있는지 확인한다.
3. 가능하면 최소 어댑터와 재개 회귀 테스트만 설계한다.
4. **코드 수정 전 사용자 승인을 받는다.**

## 다음 채팅 시작 요청문

```text
먼저 AGENTS.md, README.md, HANDOFF.md, integrations/codex/SKILL.md를 읽어줘.

다음 마일스톤은 Codex Plugin/클라이언트가 웹 Wizard 설문 제출 완료를 감지해
resume_web_survey(session_id)를 자동 호출하는 연결 가능성을 조사하고, 가능하다면 최소 구현안을
제시하는 것이다. 서버의 비차단 세션 흐름과 6개 문서 산출물 계약은 유지해라.

대상 MVP 구현·테스트 실행·배포·세션 DB 영속화로 범위를 넓히지 말고,
코드를 수정하기 전에는 반드시 나에게 승인받아라.
```
