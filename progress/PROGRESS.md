# PROGRESS

## 2026-09-13 13:34:57 +09:00 — Run-scoped candidate lifecycle breaking cutover

- 시작 시각: 2026-09-13 13:34:57 +09:00
- 목표: Run-scoped candidate lifecycle 공개 API 12개만 남기고, 구형 spec_id·직접 문서 Tool 10개를 안전하게 제거한다.
- 확정 범위: 신규 Candidate API MCP E2E, 구형 Tool 등록·어댑터·전용 UseCase 제거, 공개 계약 문서·가드레일 정합화, 전체 회귀 검증.
- 범위 제외: Adaptive Wizard 재개 인프라·기존 `.mvpmcp/` 파일 변경, worker·timeout 자동 재개, 플러그인 재설치, 대규모 파일 이동·루트 정리.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 신규 Candidate API MCP E2E 기준선 | 🟢 완료 | Composition Root에서 lifecycle 5개 기록→candidate sync→validate/preview와 generate_only 무반영을 검증 (16 passed) |
| 2. 구형 Tool 조립·어댑터·전용 UseCase 제거 | 🟢 완료 | `main.py` 등록·어댑터 10개·전용 UseCase를 제거하고 Adaptive Wizard 공유 ScopeMvp/SpecDraft 인프라는 보존 |
| 3. 공개 계약 문서·프롬프트·가드레일 갱신 | 🟢 완료 | canonical 12개·구형 10개 제거 완료·Run lifecycle 순서를 README/HANDOFF/통합 지침/감사/가드레일에 반영 |
| 4. 전체 회귀·품질 게이트 | 🟢 완료 | Ruff·Black·mypy 통과(67 source files), 전체 pytest 65 passed, Tool 부재·공백 검사 확인 |

- 구현 완료 시각: 2026-09-13 13:52:34 +09:00
- 구현 결과: `main.py::build()`는 Run-scoped canonical Tool 12개만 조립한다. 구형 Tool 10개 adapter와
  전용 spec_id UseCase·문서 Tool UseCase를 제거하고, 신규 Composition Root MCP E2E가 lifecycle 5개 기록,
  candidate sync, validate/preview 및 `generate_only` 무반영을 고정했다. Adaptive 재개가 공유하는
  `ScopeMvpUseCase`·`SpecDraft`·Repository와 미등록 `start_spec.py` 의존성은 물리 정리 범위에서 제외했다.
- 검증: targeted 57 passed, 최종 Ruff·Black·mypy 통과, `pytest -q --basetemp
  .pytest-tmp\\legacy-tool-removal-final-20260913 tests` 전체 65 passed, `git diff --check` 공백 오류 없음
  (line-ending 경고만 출력).
- 사용자 재확인: 2026-09-13에 `.venv-exec`으로 Ruff·Black·mypy·전체 pytest를 다시 실행했다.
  Ruff 통과, Black `80 files would be left unchanged`, mypy `67 source files` 문제 없음, pytest `65 passed`
  결과를 사용자가 직접 제공했다 (`확인됨`).

---

## 2026-09-13 12:41:55 +09:00 — Run-scoped candidate 수명주기 API

- 시작 시각: 2026-09-13 12:41:55 +09:00
- 목표: 메모리 `spec_id`에 묶인 요구사항·설계·배포·검증·릴리스 기록을 SQLite `run_id` 소유의 후보 수명주기로 추가하고, 기존 candidate validate/preview/apply 흐름과 안전하게 연결한다.
- 확정 범위: Run 영속 lifecycle 모델·revision/동시성 규칙, 후보 Tool 5개, candidate 재검증 전이, 문서·가드레일·회귀 검증.
- 범위 제외: 기존 `spec_id` Tool 5개 삭제·동작 변경, `.mvpmcp/` 형식·기존 사용자 파일 변경, 서버 모델 API worker, timeout 자동 재개, Web Wizard 복구, 대규모 파일 이동, 플러그인 재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. Run·candidate 수명주기 모델과 영속 계약 | 🟢 완료 | SQLite JSON Run의 하위 호환 기본값, lifecycle revision·candidate sync·이전 apply 이력 구현 |
| 2. 요구사항·설계·배포 후보 Tool과 invalidation | 🟢 완료 | `run_id`·optimistic version 기반 구조화 계약 갱신과 하위 계약 invalidation 구현 |
| 3. 테스트·릴리스 후보 기록 Tool과 게이트 | 🟢 완료 | append-only·idempotency key·PASS 릴리스 게이트를 Run 소유 상태로 이관 |
| 4. 조립·공개 안내·가드레일 | 🟢 완료 | `main.py::build()` 조립, canonical 12개 inventory, README·HANDOFF·세 클라이언트 가이드 반영 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | lifecycle·재시작·stale·candidate sync와 표준 전체 검사 통과 |

- 구현 완료 시각: 2026-09-13 13:03:44 +09:00
- 구현 결과: Run에 구조화 `candidate_lifecycle`과 revision·candidate sync 기준 hash·이전 apply cycle 이력을
  저장한다. 다섯 새 Tool은 최신 `expected_run_version`으로 요구사항→설계→전달→TEST/RELEASE를 갱신한다.
  구조화 변경은 `.mvpmcp/`에 쓰지 않고 candidate validate/preview binding만 무효화하며, 모델이 후보 Markdown을
  갱신한 뒤 새 revision으로 검증하도록 강제한다. 기존 spec_id Tool 5개는 직접 대체가 생겨 호환·deprecated로
  전환했고, 이전 직접 중복 Tool 5개와 함께 다음 breaking release까지 유지한다.
- 검증: targeted lifecycle/candidate/adaptive/guardrail `34 passed`, 최종 Ruff·Black·mypy 통과,
  `pytest -q --basetemp .pytest-tmp\\candidate-lifecycle-full-20260913 tests` 전체 `73 passed`.

---

## 2026-09-13 11:38:29 +09:00 — spec_id 직접 중복 Tool 유예 릴리스 전환

- 시작 시각: 2026-09-13 11:38:29 +09:00
- 목표: 직접 대체가 있는 `documentation_start`·`answer_question`·기존 validate/preview/apply을 한 릴리스 동안 유지하되, deprecated 전환 경로와 다음 breaking release 제거 조건을 공개 계약·문서·가드레일에 통일한다.
- 확정 범위: Tool 설명, 공개 inventory 가드레일, README·HANDOFF·통합 Skill·전환 감사, 회귀 검증.
- 범위 제외: 이번 릴리스의 Tool 등록 해제·adapter/UseCase 삭제, 등록·기록 Tool 5개 변경, `.mvpmcp/` 변경, 대규모 파일 이동, 플러그인 재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 직접 대체·유지 대상 계약 확정 | 🟢 완료 | 직접 중복 5개와 직접 대체 없는 spec_id Tool 5개를 분리 |
| 2. Tool 전환 안내·문서 갱신 | 🟢 완료 | Tool 설명·README·HANDOFF·Codex/Claude/Gemini Skill·전환 감사를 유예 정책으로 통일 |
| 3. 가드레일·회귀 검증 | 🟢 완료 | Tool inventory·전환 문서 계약·전체 품질 게이트 통과 |

- 구현 완료 시각: 2026-09-13 11:44:53 +09:00
- 구현 결과: 직접 대체가 있는 `documentation_start`·`answer_question`·기존 validate/preview/apply 5개는
  현재 공개·호출을 유지하되, Tool 설명과 모든 public 안내에 `deprecated`·대체 경로·다음 breaking release
  제거 조건을 명시했다. 요구사항·설계·전달·실행/릴리스 기록 Tool 5개는 직접 대체가 없어 유지 대상으로
  분리했다.
- 검증: targeted guardrail/workflow 11 passed, 최종 `ruff check src tests`, `black --check src tests`,
  `mypy --no-incremental src`, `pytest -q --basetemp .pytest-tmp\\compat-deprecation-final2-20260913 tests`
  모두 통과(68 passed). 전환 문구 정적 탐색은 README·HANDOFF·전환 감사·세 통합 Skill에서 모두 확인했고,
  `git diff --check`는 공백 오류 없이 line-ending 경고만 출력했다.

---

## 2026-09-13 00:45:12 +09:00 — Client-native 질문 UI 전환 및 Web Wizard 폐기

- 시작 시각: 2026-09-13 00:45:12 +09:00
- 목표: 설문을 위해 localhost 브라우저 창을 여는 모든 Web Wizard를 제거하고, Codex·Claude Code·Gemini CLI의 native 구조화 질문 UI가 정규화 답변을 MCP Run 흐름에 전달하도록 전환한다.
- 확정 범위: `LocalAdaptiveWizardForm`·`LocalWebSurveyForm`·`LocalWebQuestionForm`과 loopback HTTP/URL/CSRF/동기 대기 경로 폐기, 비대기형 adaptive Run 질문·제출 계약, 클라이언트별 통합 지침, 회귀 테스트·문서 갱신.
- 범위 제외: 서버 모델 API worker, 기존 사용자 `.mvpmcp` 변경, 후보 본문 자동 작성, 플러그인 재설치, 대규모 파일 이동.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. native 질문 계약·영향 경로 확정 | 🟢 완료 | Web Form 3종·URL elicitation/continuation probe·호환 Tool·조립 참조를 확인하고, 질문 schema 반환 → native UI → 답변 제출 계약으로 확정 |
| 2. 비대기형 adaptive Run 시작·제출 흐름 | 🟢 완료 | 질문 schema 즉시 반환, 답변 원자 저장, 같은 답변의 멱등 제출과 design 제출 뒤 DRAFT_READY를 구현 |
| 3. Web Wizard·호환 설문 경로 제거 및 조립 정리 | 🟢 완료 | localhost HTTP·브라우저 열기·CSRF·대기 Port·URL elicitation/continuation probe·구형 설문 Tool을 제거 |
| 4. Codex·Claude Code·Gemini CLI 통합 지침·문서 | 🟢 완료 | `request_user_input`·`AskUserQuestion`·`ask_user`가 같은 schema/answers 계약을 쓰도록 README·Skill·인수인계를 갱신 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | legacy 경로 정적 탐색 0건, MCP/Run·계층 가드레일, Ruff·Black·mypy·전체 pytest 통과 |

- 구현 완료 시각: 2026-09-13 11:11:05 +09:00
- 구현 결과: `documentation_start_adaptive_wizard`는 질문 schema를 즉시 반환하고,
  `documentation_submit_adaptive_wizard_answers`가 답변을 원자 저장한다. design 제출은 `DRAFT_READY`와
  `candidate_root`를 즉시 반환한다. localhost Web Form·URL elicitation/continuation probe·대기 Port와
  구형 설문 Tool은 제거했고, `main.py::build()`는 새 제출 UseCase와 Tool만 조립한다.
- 클라이언트 계약: Codex `request_user_input`, Claude Code `AskUserQuestion`, Gemini CLI `ask_user`가
  질문 schema의 `id`·조건·선택지를 보존해 답을 수집하고, 사용자의 별도 채팅 제출 메시지 없이 같은
  Run의 `answers`로 제출한다.
- 검증: targeted adaptive/guardrail/scaffolding 19 passed, Skill/Prompt 6 passed, 최종
  `ruff check src tests`, `black --check src tests`, `mypy --no-incremental src`,
  `pytest -q --basetemp .pytest-tmp\\native-question-final2-20260913 tests` 모두 통과(67 passed).
  legacy Web/elicitation 식별자 정적 탐색은 production·통합·현재 문서에서 0건이며, `git diff --check`는
  공백 오류 없이 line-ending 경고만 출력했다.

---

## 2026-09-12 23:13:47 +09:00 — 단계 11 문서 서술·프로토타입 품질 감사

- 시작 시각: 2026-09-12 23:13:47 +09:00
- 목표: 대표 품질 fixture와 실제 생성 프로토타입을 근거로 문서 서술·프로토타입의 수용 기준을 구체화하고, 필요한 최소 품질 보완만 구현·검증한다.
- 확정 범위: 현재 fixture·Skill·renderer·대표 출력의 읽기 전용 대조, 실제 브라우저 화면 캡처, 접근성·상태·콘텐츠 품질 수용 기준, 감사 결과에 근거한 최소 변경과 회귀 검증.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 등록 변경·삭제, 대규모 파일 이동, runtime output·cache 삭제, 기존 사용자 `.mvpmcp` 변경, 플러그인 동기화·재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. fixture·Skill·renderer 품질 기준선 | 🟢 완료 | 7개 루브릭·5개 대표 사례와 현재 self-review·renderer 계약을 읽기 전용으로 확인 |
| 2. 실제 prototype 화면 감사 | 🟠 별도 요청 대기 | 초기 화면 감사만 완료했다. 사용자가 시각적 완성도 조정은 별도 요청으로 분리함 |
| 3. 화면 목적별 Mock 상태·다중 화면 회귀 | 🟢 완료 | 범용 텍스트 `Mock 입력`을 각 `ScreenSpec.states` 선택으로 교체하고, 두 화면의 선택·상태 결과를 회귀로 고정 |
| 4. 구현·품질 게이트·검토용 HTML 재생성 | 🟢 완료 | Ruff·Black·mypy·import-linter·전체 pytest를 통과하고 별도 workspace preview를 생성; 기존 `.mvpmcp/`는 변경하지 않음 |

- 구현 완료 시각: 2026-09-12 23:23:47 +09:00
- 구현 결과: prototype이 화면 외에 DesignContract의 정상 흐름·예외 복구를 표시하고, 탭 키보드 전환 및 Mock 성공/오류 `aria` 상태를 구분한다. prototype 품질 fixture와 Codex Skill의 자체 점검도 같은 계약으로 고정했다.
- 검증: targeted pytest 3 passed, Ruff·Black·mypy·import-linter 통과, 전체 pytest 96 passed·2 xfailed. Black·pytest cache 권한 경고는 결과에 영향을 주지 않았다.
- 남은 수동 확인: 브라우저 보안 정책이 허용하는 방식으로 현재 생성 HTML의 실제 화면 캡처·가독성 검토가 필요하다. 이 작업에서는 정책 우회, 별도 브라우저·서버 사용, 기존 `.mvpmcp/` 재생성을 하지 않았다.
- 재확인 시각: 2026-09-12 23:40:25 +09:00 — 저장소의 `output/`·`outputs/`·`tests/`에 재사용 가능한 화면 이미지가 없고, 기존 in-app browser의 workspace `file:` 차단은 사용자 입력만으로 해제되지 않는다. 따라서 화면 감사는 계속 보류한다.
- preview 생성: 2026-09-12 23:44:05 +09:00 — 현재 `HtmlPrototypeRenderer`로 `output/stage11-prototype-review-20260912-234302/index.html`을 새로 생성했다. SHA-256은 `020904a691c2599f9211eef5fed80f76fd71632cb63ea4dafb0e4c3d9ba615be`이며, 사용자 흐름·오류 복구·탭 역할·offline CSP를 정적으로 확인했다. 기존 `.mvpmcp/`는 만들거나 변경하지 않았다.
- 화면 감사: 2026-09-12 23:47:26 +09:00 — 사용자 제공 초기 화면을 `output/stage11-prototype-review-20260912-234302/audit/01-start.jpeg`에 보존하고 직접 검토했다. 결과·한계·추가 캡처는 같은 폴더의 `01-start-notes.md`에 기록했다. 화면은 정상 로드됐지만 시작 화면만으로 오류·성공·모바일·키보드 상호작용은 판정할 수 없다.
- 콘텐츠·레이아웃 구현 완료: 2026-09-12 23:59:05 +09:00 — 각 화면의 `ScreenSpec.states`만 고르는 Mock 상태 시뮬레이터와 화면별 결과 문구를 구현했다. `prototype_acceptance` fixture·Codex Skill·README·Playwright 회귀를 같은 계약으로 갱신했으며, targeted pytest 3 passed 및 전체 pytest 96 passed·2 xfailed를 확인했다. 새 검토용 출력은 `output/stage11-prototype-state-review-20260912-235833/index.html`(SHA-256 `bdb280f1f49f5448e5b21535874cf5622e9b06cd967bd5fc7f0947229b56ba2e`)이다. 시각적 완성도 조정은 사용자 요청에 따라 별도 작업으로 보류한다.
- 최종 확인: 2026-09-13 00:00:26 +09:00 — Ruff·Black·Git diff 검사를 다시 통과했다. Black cache 읽기 권한 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 22:57:13 +09:00 — Clean Architecture·SOLID 최소 정리와 루트 산출물 inventory

- 시작 시각: 2026-09-12 22:57:13 +09:00
- 목표: 공개 MCP 계약과 사용자 `.mvpmcp/`를 바꾸지 않고, 계층 가드레일을 강화하고 adaptive Wizard adapter 결합을 줄이며 루트 산출물의 보존·운영 역할을 기록한다.
- 확정 범위: AST 기반 domain import 가드레일, adaptive Wizard snapshot helper 분리, candidate root의 opaque Port 값 비교, 루트 산출물 inventory·현재 상태 문서화, 회귀 검증.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 등록 변경·삭제, 대규모 파일 이동, runtime output·cache 삭제, 기존 사용자 `.mvpmcp` 변경, 플러그인 동기화·재설치.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 계층·조립·루트 산출물 읽기 전용 기준선 | 🟢 완료 | import-linter 계약, `main.py::build()` 조립, Git 추적·참조·runtime output 보존 범위를 확인 |
| 2. Domain 가드레일·opaque candidate root 정리 | 🟢 완료 | AST 기반 import 검사와 opaque root 계약을 추가하고, 남은 `project_root` 절대경로 검증은 `core/security.py`로 이관 (`targeted pytest` 39 passed) |
| 3. Adaptive Wizard presentation helper 분리 | 🟢 완료 | peer Tool의 private helper import를 공용 private formatter로 교체 |
| 4. 루트 산출물 inventory·현재 상태 문서화 | 🟢 완료 | `progress/ROOT_ARTIFACT_AUDIT.md`에 역할·Git 추적·runtime 보존 정책을 기록하고 HANDOFF에 연결 |
| 5. 회귀·전체 품질 게이트 | 🟢 완료 | Ruff·Black·mypy·import-linter 통과, targeted pytest 39 passed, 전체 pytest 96 passed·2 xfailed |

- 완료 시각: 2026-09-12 23:04:38 +09:00
- 검증 참고: `uv`가 PATH에 없어 기존 `.venv-exec`의 동등한 실행 파일을 사용했다. Black·pytest cache 읽기/쓰기 권한 경고는 검사 결과에 영향을 주지 않았다.

---

## 2026-09-12 19:16:24 +09:00 — generate_only write policy 불변성 보장

- 시작 시각: 2026-09-12 19:16:24 +09:00
- 목표: 최초 요청에서 확정한 `generate_only` write policy가 Wizard의 `document_output_mode` 선택으로 `safe_auto_apply`로 승격되지 않도록 막고, 정책 충돌 회귀를 고정한다.
- 확정 범위: Adaptive Wizard 정책 결정·검증, 충돌/정상 경로 회귀 테스트, 진행 기록, 전체 품질 게이트.
- 범위 제외: 서버 모델 API worker, timeout 뒤 자동 재개, Tool 삭제·등록 변경, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. write policy 결정 경로·영향 분석 | 🟢 완료 | 자연어만으로는 정책이 결속되지 않고, 2차 `document_output_mode`가 허용됨을 실제 기록·UseCase에서 확인 |
| 2. 정책 승격 차단 구현 | 🟢 완료 | canonical 시작 입력의 write_policy를 Run에 고정하고, 해당 1차 문항 제거·2차 document_output_mode 거부를 적용 |
| 3. 정책 충돌·정상 경로 회귀 | 🟢 완료 | 명시 generate_only 결속·동일 request_key 정책 변경 거부·2차 정책 질문 거부, 기존 1차 정책 경로 통과 (targeted pytest 13 passed) |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 94 passed·2 xfailed (`--basetemp .pytest-tmp-policy-full`) |

- 완료 시각: 2026-09-12 19:23:55 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로와 Black 사용자 cache의 권한 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 18:31:09 +09:00 — MCP 공개 Tool 전환 감사·호환 경로 명시

- 시작 시각: 2026-09-12 18:31:09 +09:00
- 목표: canonical 6개 Tool과 보존할 호환 Tool을 분류·문서화하고, 등록·설명 계약을 회귀 테스트로 고정한다.
- 확정 범위: Tool inventory 감사 문서, 호환 Tool 설명·README 안내, canonical/compatibility 등록 가드레일, 진행 기록.
- 범위 제외: Tool 등록 해제·파일/UseCase 삭제, 공개 입력·출력/상태/write policy 변경, 대규모 파일 이동, 기존 `.mvpmcp` 변경, worker·timeout 자동 재개.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 공개 Tool inventory·처분 상태 | 🟢 완료 | canonical 6개, 호환 10개, 보조 질문 2개를 대체 경로와 함께 고정 |
| 2. 호환 경로 설명·문서 | 🟢 완료 | 기존 Tool을 삭제하지 않고 호환 전용임을 설명과 README에 명시 |
| 3. 등록·설명 회귀 가드레일 | 🟢 완료 | canonical/compatibility 구분, 전체 등록 목록, 대체·보류 안내를 검증 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 92 passed·2 xfailed (`--basetemp .pytest-tmp-tool-transition-full`) |

- 완료 시각: 2026-09-12 18:35:32 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 18:11:25 +09:00 — 산출물 품질 루브릭·대표 평가 fixture

- 시작 시각: 2026-09-12 18:11:25 +09:00
- 목표: 후보 문서의 의미 품질을 위한 Skill 자체 점검 기준과 재현 가능한 대표 평가 fixture를 추가한다.
- 확정 범위: 7개 품질 범주, 5개 대표 사례, Skill 자체 점검, fixture 스키마·필수 조건 회귀 테스트, 로드맵·진행 기록 정합화.
- 범위 제외: 공개 MCP Tool·candidate 결정적 구조 검증·Run 상태·write policy 변경, 저장소 대규모 탐색, 기존 `.mvpmcp` 변경, 구형 Tool 삭제, worker·timeout 자동 재개.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 루브릭·대표 fixture 계약 | 🟢 완료 | 7개 품질 범주와 신규 웹·기존 API·리팩터링·결함 수정·ML 5개 입력·기대 근거 사례를 고정 |
| 2. Codex Skill 자체 점검 | 🟢 완료 | 후보 작성 뒤 구조 검증 전 루브릭 보완과 보수적 근거 상태 기록 절차를 추가 |
| 3. 회귀 테스트·로드맵 정합화 | 🟢 완료 | fixture 스키마·Skill 계약 회귀와 6·7·8단계 상태를 갱신 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 91 passed·2 xfailed (`--basetemp .pytest-tmp-artifact-quality-full`) |

- 완료 시각: 2026-09-12 18:15:46 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 17:52:01 +09:00 — Architecture 기술 스택·디렉터리 구조 계약 강화

- 시작 시각: 2026-09-12 17:52:01 +09:00
- 목표: 후보 package와 기존 renderer의 `ARCHITECTURE.md`에 근거 상태 기술 스택 표·라벨된 디렉터리 구조를 필수 계약으로 만들고 구조 위반을 검증에서 차단한다.
- 확정 범위: 후보와 renderer 모두 적용, 구조 엄격 차단, IMPLEMENTATION_PLAN의 Architecture SSOT 참조 존재만 차단, 새 저장소 탐색 없이 안전한 계획 경로만 renderer가 생성한다.
- 범위 제외: 실제 저장소 경로 대조, TASK별 경로 완전 일치, 서버 모델 API worker, timeout 자동 재개, 구형 Tool 삭제, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 문서 계약·candidate 구조 검증 | 🟢 완료 | Architecture 필수 섹션과 표·트리·SSOT 참조 검증을 추가하고 잘못된 헤더·상태·라벨·펜스·참조 누락을 차단 |
| 2. 기존 renderer 출력 계약 | 🟢 완료 | 근거 상태 표와 안전한 NEW/OPTIONAL 트리, 구현 계획 참조를 생성 |
| 3. Skill/Prompt·회귀 fixture | 🟢 완료 | candidate 저작 지침과 strict validation 사례, escaped pipe·권장 기본값·PROTOTYPE_4 renderer 회귀를 갱신 |
| 4. 전체 품질 게이트 | 🟢 완료 | ruff·black·mypy 통과, pytest 89 passed·2 xfailed (`--basetemp .pytest-tmp-architecture-contract-full`) |

- 완료 시각: 2026-09-12 +09:00
- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건과 Black cache 읽기 경고는 결과에 영향을 주지 않았다.

---

## 2026-09-12 17:31:48 +09:00 — Adaptive Wizard 질문 계약·유형 분류 재개편

- 시작 시각: 2026-09-12 17:31:48 +09:00
- 목표: 2차 Wizard의 문자열 JSON 입력을 구조화하고, Android 앱을 `blog`로 오분류하지 않도록 1·2차 문항과 유형 분류를 개선한다.
- 범위 제외: 서버 모델 API worker, Codex timeout 뒤 자동 재개, 구형 Tool 삭제, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 구조화된 2차 질문 Tool 계약·정규화 | 🟢 완료 | typed `design_questions`를 정식 입력으로 추가하고 title/type·single_select 계열을 canonical schema로 정규화; 문자열 입력은 호환 경로로 유지 |
| 2. 1차 분류 축·모바일 템플릿·유형별 문항 | 🟢 완료 | 작업 유형과 솔루션·표면·도메인 분류를 분리하고 Android/iOS/크로스플랫폼을 `MOBILE_APP`으로 우선 매핑 |
| 3. 2차 문항 지침·Skill/Prompt 갱신 | 🟢 완료 | 정식 구조화 스키마와 금지된 별칭을 서버 Prompt·Codex Skill에 반영 |
| 4. 회귀 테스트·전체 품질 게이트 | 🟢 완료 | 구조화·문자열 호환 Tool 호출, Android/mobile·웹 콘텐츠 분류 회귀와 전체 검사 통과: ruff·black·mypy, pytest 81 passed·2 xfailed |

- 검증 참고: 현재 셸에는 `uv` 명령이 없어 저장소의 `.venv-exec` 실행 파일로 동등한 품질 게이트를 실행했다. pytest cache 경로 권한 경고 1건은 결과에 영향을 주지 않았다.

---

## 2026-09-12 — Codex Desktop 실제 2단계 Wizard·자동 반영 수용 테스트

- 목표: 구현 전제였던 "설문 제출 뒤 같은 task 자동 진행"과 `safe_auto_apply`의 Codex Desktop 실제
  동작을 확인한다.

| 확인 항목 | 상태 | 실제 결과 |
|---|---|---|
| 1차 blocking Wizard 대기 | 🔴 실패 | `documentation_start_adaptive_wizard` Tool 호출이 약 300초 뒤 timeout. 서버 대기만으로는 연장되지 않음. |
| timeout 뒤 Run 복구 | 🟢 완료 | 동일 `request_key` 재호출로 영속 `INTAKE_SUBMITTED` 답변을 회수. |
| 제출 뒤 채팅 없는 자동 재개 | 🔴 실패 | timeout 뒤에는 사용자의 `제출함` 메시지가 다음 Tool 호출의 계기가 됨. |
| 2차 질문 제출과 후보 작성 | 🟢 완료 | 2차 질문 정의가 두 번 형식 오류를 냈으나 세 번째 호출에서 `DRAFT_READY`와 candidate root를 발급하고 후보를 작성·검증. |
| 명시적 사전 승인 기반 safe auto apply | 🟢 완료 | 최초 자연어 요청에 `.mvpmcp/` 자동 반영 허용을 명시하면 9개 관리 문서를 충돌 없이 갱신. |

- 결정: 300초 timeout 이후 자동 재개는 **최후순위**로 연기한다. 다음 구현은 2차 질문의 문자열 JSON
  계약과 Wizard 유형·문항 품질을 먼저 개선한다.
- 주의: 이번 `candidate_valid: true`는 구조·추적성 검증 통과를 뜻하며, 문서 서술의 실무 품질은 아직
  별도 루브릭·대표 fixture로 평가하지 않았다.

---

## 2026-09-11 20:16:26 +09:00 — 동기 대기형 2단계 적응형 Wizard 기반

- 시작 시각: 2026-09-11 20:16:26 +09:00
- 목표: Codex URL elicitation 대신 검증된 loopback blocking Wizard를 사용해, 같은 MCP 작업 안에서 1차·2차 설문을 채팅 재입력 없이 진행할 수 있는 영속 Run 기반을 구현한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 2-0. 계획·기존 경로 재정렬 | 🟢 | 실제 Codex URL 재개 실패와 `LocalWebSurveyForm.ask()`의 동기 대기 계약을 확인해, blocking loopback form을 기본 전송 방식으로 확정 |
| 2-1. 영속 Adaptive Run 도메인·SQLite 저장소 | 🟢 | request_key, optimistic version, 단계별 제출 snapshot, DRAFT_READY 및 재시작 조회 모델을 구현 |
| 2-2. 1·2차 blocking Web Wizard·MCP Tool | 🟢 | loopback HTTP form, CSRF 제출 토큰, 1차→2차 대기, `DRAFT_READY + spec_id` 호환 연결과 MCP memory E2E를 구현 |
| 2-3. Skill·서버 지시문·호환 경로 | 🟢 | 서버 Prompt·Codex Skill·README를 adaptive 기본 경로로 전환하고 기존 Tool을 호환 경로로 명시 |
| 2-4. 회귀·E2E·품질 게이트 | 🟢 | ruff·black·mypy 통과, 전체 pytest `68 passed, 2 xfailed`, 기존 MCP 평가 `10/10` 통과 |

- 완료 시각: 2026-09-12 +09:00
- 구현 경계: URL elicitation·서버 측 모델 worker는 기본 경로에서 제외했다. 이번 단계는 2차 제출 뒤
  `DRAFT_READY + spec_id`와 기존 validate/preview 체인 연결까지이며, run 전용 candidate package와
  `safe_auto_apply`는 다음 단계다.

### 다음 승인 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 3-0. 후보 package·기존 exporter 재사용 설계 | 🟢 | `<output>/runs/<run_id>/candidate`와 `<output>/previews/<run_id>/<preview_id>`를 기존 exporter의 hash·충돌·원자 반영 계약에 결합 |
| 3-1. candidate 저장소·validate/preview/apply UseCase | 🟢 | 후보 파일은 Skill이 작성하고 MCP Core는 경로·UTF-8·symlink 정책, revision/version 검증, preview, `write_policy` 상태 전이를 담당 |
| 3-2. 후보 package Tool·Skill handoff·자동 안전 반영 | 🟢 | `DRAFT_READY`가 candidate root를 발급하고, status → validate → preview chain 및 `safe_auto_apply` 내부 Apply를 같은 모델 턴의 지시문에 연결 |
| 3-3. candidate E2E·회귀·품질 게이트 | 🟢 | unmanaged 충돌 보존·SQLite 재시작·stale revision·정책 거부·manual/auto apply·MCP memory E2E와 전체 품질 게이트 통과 |

- 후보 package 품질 게이트: `ruff`, `black --check`, `mypy` 통과; 전체 pytest
  `76 passed, 2 xfailed`; 기존 MCP evaluation `10/10 passed`.
- 구현 경계: candidate 본문은 서버가 모델 API로 작성하지 않는다. Codex Skill이 server-issued root 안에
  작성하고, server 재시작 뒤 process-local preview apply payload가 없으면 같은 revision으로 새 preview를
  만들어 수동 반영 binding을 복구한다. 미니 Wizard·browser 완료 화면·구형 Tool 6개 전환은 후속 단계다.

---

## 2026-09-11 18:49:27 Asia/Seoul — 2단계 적응형 Wizard 리팩터링 단계 0·1

- 시작 시각: 2026-09-11 18:49:27 Asia/Seoul
- 목표: 승인된 최종 계획의 회귀 fixture 기준선과 Codex URL elicitation 자동 재개 capability spike를 최소 변경으로 구현·검증한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 0-1. 현행 Tool·Wizard·테스트 계약 조사 | 🟢 | 기본 Tool은 blocking `SubmitWebSurveyUseCase`만 조립하며, 비차단 Begin/Submit/Resume UseCase는 미등록임을 확인 |
| 0-2. 실패 fixture·회귀 기준선 고정 | 🟢 | 중복 설문·제출 뒤 단절·URL completion 사례를 strict xfail 2건과 평가 fixture로 고정 |
| 1-1. 자동 재개 capability spike 설계·구현 | 🟢 | SQLite Probe·loopback URL form·completion notification·수동 retry MCP E2E 구현 및 통과 |
| 1-2. Codex client 연계 검증·결정 기록 | 🟢 | 실제 Codex Desktop 수용 테스트 완료. URL elicitation은 Tool 오류·링크로 표시되고, 사용자가 form을 제출해도 원래 Tool 자동 retry가 일어나지 않았다. MCP URL 재개는 제품 경로에서 제외한다. 상세는 `progress/CODEX_URL_ELICITATION_CAPABILITY_SPIKE.md` |
| 1-3. 품질 게이트·인수인계 갱신 | 🟢 | ruff·black·mypy, 전체 pytest(62 passed, 2 xfailed), 기존 MCP 평가(10/10), diff check 통과. 결과·후속 분기를 HANDOFF와 spike 기록에 반영 |

- 품질 게이트 완료: 2026-09-11 19:15:08 +09:00
- 실제 수용 결과: Codex Desktop은 URL elicitation을 native Wizard가 아닌 Tool 오류·링크로 처리했고, 브라우저 form 제출 후에도 원래 Tool을 자동 재시도하지 않았다. 다음 구현은 영속 Run + 별도 Web Wizard + 서버 측 지속 worker 대안으로 설계한다.

---

## 2026-09-10 19:23:12 +09:00 — 실클라이언트 Wizard 연속 실행·권장 기본값·상태 계약 보강

- 시작 시각: 2026-09-10 19:23:12 +09:00
- 목표: 실클라이언트 수용 테스트에서 발견된 구버전 Skill 충돌, Wizard 제출 후 중단, 미정값 반복 질문, 확정 후 수정 및 상태 게이트 결함을 해결한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 설치 Skill·신규 Tool 계약 일치화 | 🟢 | 개인 플러그인 `0.2.0+codex.20260910103953` 재설치; 설치 Skill과 원본 SHA-256 일치, 절대 MCP 실행 경로 적용 |
| 2. 설문 권장 기본값·결정 출처 모델 | 🟢 | 미입력 상세와 계획 미정 선택을 프로젝트별 보수적 기본값으로 해소하고 출처·근거·신뢰도 기록 |
| 3. OPEN 결정·preview 품질 게이트 수정 | 🟢 | `status=resolved` 결정은 허용하고 실제 open topic만 정확한 문구로 차단 |
| 4. 요구사항 수정·수동 시작 상태 전이 수정 | 🟢 | stable ID upsert·revision·후속 계약 무효화, collecting 상태 선검증, 정확한 next_action 구현 |
| 5. 통합·회귀·전체 품질 검증 | 🟢 | ruff·black·mypy 통과, pytest 55 passed, 평가 10/10, plugin/Skill validation 통과 |
| 6. 새 Codex 작업 수동 수용 테스트 | 🟢 | 사용자가 새 Codex 작업에서 고도화 산출물이 정상 생성됐음을 확인 (`확인됨`) |

- 완료 시각: 2026-09-10 19:46:03 +09:00
- 실사용 수용 확인: 2026-09-10 20:54:56 +09:00 — 새 Codex 작업의 고도화 산출물 정상 생성
- 검증 참고: pytest cache와 Black 사용자 캐시는 샌드박스 권한 경고가 있었으나 테스트·포맷 검사 결과에는 영향이 없다.

---

## 2026-09-10 11:18:12 +09:00 — HUMAN-AI 가이드 기반 문서 시스템 고도화

- 시작 시각: 2026-09-10 11:18:12 +09:00
- 목표: HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE를 유일 기준으로 구조화 문서 계약·추적성·품질 게이트·안전한 `.mvpmcp/` 출력과 선택적 HTML 프로토타입을 구현한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 0. 개발 환경·기존 기준선 복구 | 🟢 | `.venv-exec` 격리 환경 구성; ruff·black·mypy 통과, pytest 55 passed. 실행 중 서버가 `.venv` 교체를 잠가 재시작 시 정리 필요 |
| 1. 가이드 기준 고정·구조화 도메인 모델 | 🟢 | 가이드 SHA-256·coverage manifest·8문서 전체 목차·프로파일·ID 모델 구현 |
| 2. 추적성·단계 게이트·변경 이력 | 🟢 | FR/AC→TASK→TEST와 NOT RUN·증거 필수·append-only TEST/REL 계약 구현 |
| 3. 통합 Wizard·프로파일 판정 | 🟢 | 13개 문서·위험 질문과 prototype 필요/불필요, 조건부·배타 선택 구현 |
| 4. Markdown·OpenAPI·HTML 렌더링 | 🟢 | 6+조건부 2문서 전체 목차, 단일 OpenAPI, NON-SSOT 독립 HTML 구현 |
| 5. `.mvpmcp/` preview·apply | 🟢 | manifest hash·unmanaged 충돌·STALE 보존·원자적 적용 구현 |
| 6. MCP Tool·연동·레거시 cutover | 🟢 | 신규 workflow·3개 연동 지침 전환; 구형 2/6문서 Tool·exporter·모델·렌더러 삭제 |
| 7. 전체 테스트·Inspector·평가 | 🟢 | ruff·black·mypy 통과, pytest 50 passed(Chromium 포함), 환경 READY, Inspector 기동, 평가 10/10 |

- 완료 시각: 2026-09-10 13:05:00 +09:00
- 추가 발견·수정: Windows 텍스트 개행 변환으로 관리 hash가 달라지는 결함을 UTF-8 byte write로 수정하고, preview 이후 manifest 변조 차단 회귀 테스트를 추가했다.
- 운영 참고: 실행 중인 기존 MCP 서버가 원래 `.venv`를 잠가 `.venv-exec`에서 검증했다. 서버 종료 후 표준 `.venv` 재동기화가 필요하다.

---

## 2026-09-09 10:44:14 +09:00 — Wizard 즉시 재개·기술 스택 문서화

- 시작 시각: 2026-09-09 10:44:14 +09:00
- 목표: Wizard 제출을 기다려 같은 MCP 호출에서 명세 초안을 만들고, 6문서 계획에 기술 스택과 물결표 이스케이프 작성 규칙을 반영한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 제출 대기형 Wizard 흐름 구현 | 🟢 | `ask_web_survey`가 Wizard 제출을 기다리고 같은 호출에서 `spec_id`를 반환하도록 전환 |
| 기술 스택 수집·계획 문서 계약 | 🟢 | 직접 지정 시 필수 입력란을 표시하고 모든 유형의 `plan.md`에 `## 기술 스택`을 강제 |
| Markdown 물결표 작성 규칙 | 🟢 | 6문서 생성 컨텍스트에 리터럴 물결표의 `\\~` 이스케이프 규칙 반영 |
| 회귀 테스트·전체 검증 | 🟢 | ruff·black·mypy 통과, pytest 55 passed (`--basetemp .pytest-tmp-full`) |

---

## 2026-09-08 17:52:20 +09:00 — 6문서 결과물 품질 고도화

- 시작 시각: 2026-09-08 17:52:20 +09:00
- 목표: 설문·설계 계약의 상세도를 6문서 작성 컨텍스트로 전달하고, 문서 식별자와 Open Decision의 품질 게이트를 강화한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 현행 세션·문서 품질 계약 분석 | 🟢 | `resume_web_survey`의 상세 설문 누락과 기존 검증 한계를 확인 |
| 상세 설문·설계 계약 컨텍스트 전파 | 🟢 | 비차단 재개 경로를 포함해 7개 설문 상세값과 계약 세부값을 컨텍스트에 반영 |
| ID·Open Decision 품질 게이트 | 🟢 | TASK/TEST 중복·미등록·누락 ID와 미확정 결정 문서 누락을 차단 |
| 워크플로·회귀 테스트 정합화 | 🟢 | 세션 재개 지침과 상세 설문·중복 TEST 회귀 테스트 추가 |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과, pytest 54 passed (`--basetemp .pytest-tmp-full`) |

---

## 2026-09-08 16:21:44 +09:00 — 비차단 Wizard 세션·30분 만료 고도화

- 시작 시각: 2026-09-08 16:21:44 +09:00
- 목표: 브라우저 제출 대기로 MCP Tool 호출이 끝나는 문제를 제거하고, 제출 결과를 30분간 재개 가능한 세션으로 관리한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 설문 세션 모델·저장소·30분 만료 | 🟢 | 프로세스 메모리 세션과 1,800초 만료 정책 반영 |
| 비차단 시작·상태·재개 Tool | 🟢 | ask_web_survey·get_web_survey_status·resume_web_survey 등록 |
| 웹 제출 연결 및 기존 흐름 전환 | 🟢 | POST 제출값을 세션에 저장하고 blocking 대기 제거 |
| 회귀 테스트·문서 갱신 | 🟢 | Tool 등록 회귀 포함 pytest 52 passed |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과 |
| Codex 제출 완료 자동 재개 Plugin | 🟠 | 서버 범위를 넘어서는 클라이언트 어댑터 작업으로 별도 구현 필요 |

---

## 2026-09-08 12:51:13 +09:00 — 6문서 품질 계약 고도화

- 시작 시각: 2026-09-08 12:51:13 +09:00
- 목표: 기존 2문서의 상세 콘텐츠를 보존하고, 6문서 산출물의 설계·추적성·품질 게이트를 강제한다.

### 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 구조화 설계 계약·검증 모델 | 🟢 | 화면·흐름·데이터·인터페이스·규칙·오류와 PASS 증거 계약 반영 |
| 문서 품질 게이트·상세 작성 컨텍스트 | 🟢 | 필수 섹션·REQ/TASK/TEST 추적성·P0 정상/경계 검증 적용 |
| Tool·워크플로·상세 설문 연결 | 🟢 | 설문 상세 항목, 신규 Tool, 자동 검증-저장 흐름 반영 |
| 회귀·품질 테스트 및 문서 갱신 | 🟢 | 품질 계약 회귀 테스트와 README·Codex 시작 Skill 갱신 |
| 전체 품질 게이트 | 🟢 | ruff·black·mypy 통과, pytest 51 passed; pytest 임시 폴더는 실행 사용자 TEMP 경로 사용 |


## 작업 목표

활성 프로젝트 루트의 `mvp/`에 6개 실행 계약 문서를 만들고, 요구사항·작업·테스트·검증을 추적한다.

## 단계 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| 1. 현 구조·영향 확인 | 🟢 | 2문서 Exporter·인메모리 초안·단일 설문 흐름 확인 완료 |
| 2. 실행 계약 도메인 모델·상태 구현 | 🟢 | REQ-ID·TASK-ID·TEST-ID·검증 근거·확인 게이트 구현 완료 |
| 3. 6문서 Bundle·프로젝트 루트 Exporter 구현 | 🟢 | `<project_root>/mvp/` 고정 파일 6개 저장·재내보내기 범위 제한 완료 |
| 4. Tool·Wizard·워크플로 연결 | 🟢 | 기본 설문에 프로젝트 루트 전달, 8단계 프롬프트·전역 `/mvpmcp` Skill 갱신 완료 |
| 5. 테스트·문서 갱신 | 🟢 | 6문서 내용·재내보내기·NOT_RUN·오류 변환·README 갱신 완료 |
| 6. 품질 게이트 검증 | 🟢 | ruff·black·mypy·pytest 46개 통과 |
