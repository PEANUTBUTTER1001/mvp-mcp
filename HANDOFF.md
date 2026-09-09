# HANDOFF.md — 현재 인수인계

> **최종 갱신:** 2026-09-09
> **목적:** 다음 세션이 현재 MVP 문서 생성 서버의 사실·제약·다음 작업만 읽고 안전하게 이어간다.

## 먼저 읽을 문서

1. [AGENTS.md](AGENTS.md) — 계층·조립·테스트 절대 규칙
2. [README.md](README.md) — 현재 사용자 흐름·도구·6개 산출물 계약
3. 이 문서 — 현 상태·검증 근거·다음 마일스톤
4. [progress/PROGRESS.md](progress/PROGRESS.md) — 완료 작업의 시간순 기록

`PLAN.md`, `PROPOSAL.md`, `TEMPLATE.md`, `ARCHITECTURE_REVIEW.md`는 초기 설계·템플릿 배경 기록이다.
현재 도구 수·문서 수·Wizard 흐름의 기준으로 사용하지 않는다.

## 현재 상태

| 항목 | 상태 | 근거 신뢰도 |
|---|---|---|
| 6개 실행 계약 문서 생성 | 완료 | 확인됨 |
| `<project_root>/mvpmcp/` 고정 경로 내보내기 | 완료 | 확인됨 |
| REQ-ID·TASK-ID·TEST-ID·검증 근거 추적성 검사 | 완료 | 확인됨 |
| 단일 페이지 웹 Wizard | 완료 | 확인됨 |
| Wizard 제출 대기 및 동일 호출 내 `spec_id` 생성 | 완료 | 확인됨 |
| 직접 지정 기술 스택 입력 및 `plan.md` 기술 스택 계약 | 완료 | 확인됨 |
| 본문 물결표 `\~` 이스케이프 작성 지침 | 완료 | 확인됨 |
| Codex·Claude·Gemini 연동 원본 문서 | 완료 | 미확인 |
| 새 6문서 구조로의 파일명·계약 전환 | 연기 | 확인됨 |

## 현재 제품 계약

### 기본 흐름

```text
/mvpmcp <아이디어>
→ ask_web_survey(user_request, project_root)
→ 단일 페이지 웹 Wizard 설문 제출 대기
→ 같은 호출에서 spec_id 반환
→ scope_mvp
→ register_requirements / confirm_scope / register_design_contract
→ register_delivery_contract
→ validate_mvp_bundle
→ export_mvp_bundle
→ <project_root>/mvpmcp/의 6개 Markdown 파일 안내
```

생성 파일은 `requirements.md`, `proposal.md`, `plan.md`, `backlog.md`, `test-plan.md`,
`verification-report.md`다. `plan.md`에는 모든 프로젝트 유형에서 `## 기술 스택` 제목이 필요하다.
이 서버는 **문서 산출물만** 책임지며, 대상 프로젝트의 구현·테스트 실행·배포를 하지 않는다.

### 문서 작성·검증 규칙

- 문서는 REQ-ID → TASK-ID → TEST-ID 연결을 유지한다.
- P0 요구사항은 수용 기준 2개 이상, 정상과 경계 또는 실패 TEST를 모두 가져야 한다.
- 직접 지정 기술 스택은 Wizard 입력란에서 필수로 받고, 기본 스택은 유형 템플릿에서 결정한다.
- 일반 본문의 리터럴 물결표는 `\~` 이스케이프를 사용한다. 코드 블록·명령어·정규식은 원문을 유지한다.
- `verification-report.md`는 실제 검증 근거를 `record_verification`으로 등록하기 전까지 `NOT_RUN`이다.

### 호환 기능과 주의점

- 기존 `finalize_spec`·`export_spec`은 2문서 호환 기능으로 유지한다.
- 기존 비차단 설문 세션 도메인 코드는 남아 있지만, `get_web_survey_status`와 `resume_web_survey`는 현재 서버에 등록하지 않는다. 기본 흐름은 제출 대기형 `ask_web_survey`다.
- 메모리 기반 초안은 서버 재시작 뒤 사라진다. 영속화는 현재 범위 밖이다.
- 실행 중인 MCP 서버는 재시작해야 최신 Wizard 동작을 사용한다.

## 검증 기록

| 명령 또는 근거 | 결과 | 신뢰도 |
|---|---|---|
| `.venv\\Scripts\\ruff.exe check` | 통과 | 확인됨 |
| `.venv\\Scripts\\black.exe --check src tests` | 통과 | 확인됨 |
| `.venv\\Scripts\\mypy.exe src` | 통과 | 확인됨 |
| `.venv\\Scripts\\pytest.exe -q --basetemp .pytest-tmp-full` | 55 passed | 확인됨 |

## 다음 마일스톤

**범위:** 현재 산출물 파일을 다음 6개 실행·인수인계 중심 문서로 전환하는 설계를 확정한다.

```text
FEATURE_SPEC.md
TECH_DESIGN.md
AGENTS.md
IMPLEMENTATION_PLAN.md
TEST_PLAN.md
RELEASE_RUNBOOK.md
```

**설계 기준:** S 티어는 항상 필수, A 티어는 프로젝트 유형별 필수, B 티어는 위험 신호가 있을 때 필수이며,
해당하지 않으면 `해당 없음` 또는 `MVP 이후`와 근거를 기록한다. REQ-ID → TASK-ID → TEST-ID → 출시 점검 항목의
추적표를 유지한다.

**범위 확장 금지:** 대상 MVP 구현·실제 테스트 실행·배포·세션 DB 영속화를 추가하지 않는다. 기존 6문서 파일을
교체하거나 Export API를 변경하는 구현은 사용자 승인 후에만 수행한다.

**시작 순서:**

1. 현재 6문서와 새 6문서의 항목·ID·검증 규칙 매핑을 확정한다.
2. 기존 `verification-report.md`의 `NOT_RUN`·근거 계약을 `TEST_PLAN.md` 및 `RELEASE_RUNBOOK.md`에 보존하는 방식을 설계한다.
3. Export API·파일명 변경의 하위 호환 정책을 결정한다.
4. **코드 수정 전 사용자 승인을 받는다.**

## 다음 채팅 시작 요청문

```text
먼저 AGENTS.md, README.md, HANDOFF.md, progress/PROGRESS.md를 읽어줘.

다음 마일스톤은 현재 mvpmcp의 6개 산출물을 FEATURE_SPEC.md, TECH_DESIGN.md,
AGENTS.md, IMPLEMENTATION_PLAN.md, TEST_PLAN.md, RELEASE_RUNBOOK.md로 고도화하기 위한
문서별 항목·ID 추적성·품질 게이트·하위 호환 설계를 확정하는 것이다.

S/A/B 티어 적용 규칙과 verification-report.md 계약의 승계 방안을 반드시 포함해라.
대상 MVP 구현·실제 테스트 실행·배포·세션 DB 영속화로 범위를 넓히지 말고,
Export API나 파일명을 바꾸는 코드 수정 전에는 반드시 나에게 승인받아라.
```
