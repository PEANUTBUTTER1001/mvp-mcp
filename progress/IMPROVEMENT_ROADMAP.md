# mvp-mcp 범용 문서 생성기 개선 로드맵

> 상태: **단계 0~14 완료 — Run-scoped candidate lifecycle breaking cutover까지 전체 품질 게이트 통과**
>
> 최종 갱신: 2026-09-13
>
> 상세 계약: [FINAL_SKILL_HARNESS_MCP_REFACTORING_PLAN.md](FINAL_SKILL_HARNESS_MCP_REFACTORING_PLAN.md)

## 목표

`mvp-mcp`를 정적 설문·템플릿 생성기에서, 두 단계 적응형 client-native 질문 UI와 Skill·Harness·MCP Core가
협력하는 범용 Human–AI 저장소 문서 생성기로 전환한다.

## 승인된 핵심 UX

```text
요청 → 1차 공통·유형별 질문 schema → native 질문 UI → 저장소·답변 분석 → 2차 맞춤 질문 schema
     → native 질문 UI
     → Run-scoped 구조화 계약 → 후보 산출물 자동 생성 → 품질 검사·preview → write_policy 기반 안전 반영
```

- 1차: 공통 8개 내외 + 유형별 3~6개
- 2차: 분석으로 만든 맞춤 질문 3~7개
- 2차 제출 뒤 별도 채팅·생성 승인 없이 후보·preview 생성
- 차단 결정에만 최대 1회의 1~3개 native 질문 묶음
- `ARCHITECTURE.md`에 근거 상태가 있는 기술 스택 표와 라벨된 디렉터리 구조를 생성
- canonical 시작 호출은 명시 `write_policy`를 Run에 고정한다. 자동 반영 권한이 명시되지 않으면
  `generate_only`를 사용하며, 2차 질문은 파일 반영 정책을 다시 묻지 않는다.

## 진행 순서

| 단계 | 작업 | 상태 |
|---:|---|---|
| 0 | 현재 실패 사례·E2E 기준선·평가 fixture 고정 | 완료 |
| 1 | Codex URL elicitation 자동 재개 capability spike | 완료 — 실제 Desktop 자동 retry 실패 확인 |
| 2 | 영속 Run 상태·SQLite·멱등 제출 | 완료 |
| 3 | 1차/2차 적응형 Wizard·Coordinator | 완료 — 영속 Run·질문 schema·제출 계약 |
| 4 | Skill·Harness·후보 Markdown 계약 | 기본 완료 |
| 5 | 후보 validate/preview/write policy | 기본 완료 — canonical 명시 정책 결속·2차 정책 재질문 거부 포함 |
| 6 | 2차 질문 계약 구조화·Wizard 문항/유형 재개편 | 완료 |
| 7 | 기술 스택·디렉터리 구조 문서 계약 | 완료 |
| 8 | 산출물 품질 루브릭·대표 fixture | 완료 |
| 9 | MCP 공개 Tool 전환·구형 흐름 정리 | 완료 — canonical 7개, Web 설문/elicitation Tool 제거·가드레일 반영 |
| 10 | Clean Architecture·SOLID·루트 산출물 정리 | 완료 — AST 계층 가드레일, opaque workspace 경계, presentation helper 분리, root inventory. 물리 이동·삭제는 별도 승인 |
| 11 | 문서 서술·프로토타입 품질 고도화 | 콘텐츠·레이아웃 계약 완료 — 화면별 상태 Mock, 흐름·오류·접근성 fixture와 회귀를 구현·검증. 시각적 완성도 조정은 별도 요청으로 보류 |
| 12 | client-native 질문 UI 전환·Web Wizard 폐기 | 완료 — 전체 정적 검사·pytest 67 passed |
| 13 | Run-scoped candidate lifecycle | 완료 — SQLite lifecycle·optimistic version·idempotent TEST/RELEASE 기록·candidate 재검증 연결·pytest 73 passed |
| 14 | Run-scoped candidate lifecycle breaking cutover | 완료 — 구형 spec_id/직접 문서 Tool 10개 제거, canonical 12개 E2E·부재 가드레일·현재 안내 정합화, pytest 65 passed |

## 추적 원칙

- 실제 구현·테스트·배포 완료 전에는 완료로 표시하지 않는다.
- client-native 질문 UI의 세션 유지·재개는 각 MCP 클라이언트의 책임이며, 서버 모델 worker는 별도 사용자 승인 없이는 도입하지 않는다.
- 기존 사용자 수정 파일은 후보 생성·자동 반영 과정에서도 덮어쓰지 않는다.
- 루트 파일 이동·삭제는 Git 추적·참조·보존 가치를 확인한 뒤에만 수행한다.
- Web Wizard Tool 대기와 timeout 결합은 제거했다. Run 데이터는 SQLite에 남고 native 질문 UI 중단 뒤에는
  `documentation_wizard_run_status`로 상태를 읽는다.

## 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-09-11 | 초기 범용 문서 생성기 개선 로드맵 작성 |
| 2026-09-11 | 2단계 적응형 Wizard와 영속 Run을 승인된 핵심 UX로 승격 |
| 2026-09-12 | 실사용 timeout·질문 형식 오류를 반영해 Wizard 질문 계약/문항 재개편을 다음 단계로, timeout 자동 재개를 최후순위로 조정 |
| 2026-09-12 | 6·7단계 구현을 완료하고, 7개 품질 루브릭과 5개 대표 평가 fixture를 추가하는 8단계를 시작 |
| 2026-09-12 | 8단계를 완료: Skill 자체 점검, fixture 스키마·필수 조건 회귀, 전체 품질 게이트를 통과 |
| 2026-09-12 | 9단계의 Tool inventory 감사를 완료: canonical 6개와 호환·보조 Tool을 고정하고 삭제는 별도 승인으로 보류 |
| 2026-09-12 | 실제 Android `generate_only` 수용 기록을 바탕으로 최초 명시 write policy 결속·정책 재질문 거부를 구현하고 전체 pytest 94 passed, 2 xfailed를 확인 |
| 2026-09-12 | 10단계 최소 정리를 완료: AST 기반 domain import 가드레일, core 경로 정책, adaptive Wizard snapshot helper 분리, root artifact inventory와 전체 품질 게이트를 반영. Tool 삭제·파일 이동·runtime 정리는 하지 않음 |
| 2026-09-12 | 11단계의 계약 기반 보완을 완료: prototype이 `user_flows`·`error_states`를 표시하고 키보드 탭·Mock 성공/오류 상태를 구분하도록 했으며, fixture·Skill·Playwright 회귀를 추가했다. in-app browser의 workspace `file:` 접근 정책 때문에 실제 화면 캡처 감사는 보류했다. |
| 2026-09-12 | 11단계의 콘텐츠·레이아웃 보완을 완료: 범용 텍스트 Mock 입력을 화면별 `ScreenSpec.states` 선택으로 교체하고, 다중 화면 상태 결과를 회귀로 고정했다. 시각적 완성도 조정은 사용자 요청에 따라 별도 작업으로 분리했다. |
| 2026-09-13 | 사용자의 선택에 따라 localhost Web Wizard·URL elicitation/continuation probe·호환 설문 Tool을 폐기하고, 질문 schema → Codex `request_user_input`·Claude Code `AskUserQuestion`·Gemini CLI `ask_user` → 구조화 답변 제출의 비대기형 Run 계약으로 전환했다. |
| 2026-09-13 | `spec_id`에 묶인 요구사항·설계·전달·TEST/RELEASE 기록의 Run-scoped candidate lifecycle 대체 경로를 추가했다. 구조화 변경은 candidate validate/preview를 무효화하고, 기존 spec_id Tool 5개는 호환·deprecated로 한 릴리스 유지한다. |
| 2026-09-13 | Run-scoped candidate lifecycle breaking cutover를 시작했다. 신규 Composition Root MCP E2E를 먼저 고정한 뒤 구형 Tool 10개 등록·어댑터·전용 UseCase를 제거하고 canonical 12개만 공개한다. |
| 2026-09-13 | breaking cutover를 완료했다. canonical 12개만 등록되고 구형 Tool 10개는 미등록이며, Ruff·Black·mypy와 전체 pytest 65 passed를 통과했다. |
