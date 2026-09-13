# mvp-mcp 구현 직전 최종 계획 — 2단계 적응형 Wizard · Skill · Harness · MCP Core

> 상태: **역사 계획 — 2026-09-13 client-native 질문 전환, Run-scoped candidate lifecycle, canonical 12개 breaking cutover까지 완료됨**
>
> 승인일: 2026-09-11
>
> 구현 상태: 이 문서의 이전 구현 기록은 URL elicitation 대안으로 영속 Run + 동기 대기형 loopback Wizard를 구현했고, 2026-09-12에
> Run 전용 candidate workspace, revision·version 결속 validate/preview, 충돌 보존과 `safe_auto_apply`까지
> 구현했다. 이후 공개 Tool 6개 전환, 문서 renderer의 기술 스택/트리 계약, 최소 Clean Architecture·루트
> 산출물 inventory를 완료했다. 이후 사용자가 Web Wizard 폐기를 승인하여, 2026-09-13에 해당 Form·Tool·
> continuation probe를 삭제하고 client-native 질문 schema·제출 계약으로 대체했다. 같은 날 Run-scoped candidate
> lifecycle을 추가하고 구형 spec_id·직접 문서 Tool 10개를 제거해 canonical 12개만 남겼다. 현재 계약은
> `README.md`, `HANDOFF.md`, `progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md`가 기준이다.
>
> 대상: `mvp-mcp` 범용 Human–AI 저장소 문서 패키지 생성기

## 0.2 2026-09-13 현재 구현 보정 — client-native 질문 UI

이 절이 문서의 이전 Web/loopback/URL elicitation 표현보다 우선한다. 서버는 질문 schema를 반환하고
답변을 기다리지 않는다. Codex는 `request_user_input`, Claude Code는 `AskUserQuestion`, Gemini CLI는
`ask_user`로 질문을 표시한 뒤 확정 답을 구조화해 제출한다.

```text
documentation_start_adaptive_wizard(phase=intake)
  → questions schema 즉시 반환
  → 클라이언트 native 질문 UI
  → documentation_submit_adaptive_wizard_answers(phase=intake, answers)
  → 저장소·답변 분석 및 design_questions 정의
  → documentation_start_adaptive_wizard(phase=design)
  → 클라이언트 native 질문 UI
  → documentation_submit_adaptive_wizard_answers(phase=design, answers)
  → DRAFT_READY + spec_id + candidate_root
  → update_candidate_requirements → architecture → delivery
  → candidate Markdown 갱신
  → package_status → validate_package → preview_package
```

- 브라우저·localhost HTTP·URL elicitation·CSRF·Tool 대기·continuation probe는 제품 코드와 공개 Tool에서
  제거했다. 클라이언트 질문 UI의 세션 만료/재개 보장은 서버가 소유하지 않는다.
- 제출 Tool은 같은 phase·같은 정규화 답변을 멱등 처리한다. design 제출은 `DRAFT_READY`와 candidate
  workspace를 즉시 반환하므로 별도 사용자 채팅 메시지를 기다리지 않는다.
- 서버 모델 API worker, timeout 뒤 자동 재개, 기존 사용자 `.mvpmcp/` 변경, 플러그인 재설치는 이 전환에
  포함하지 않는다.

## 0.3 2026-09-13 현재 구현 보정 — Run-scoped candidate lifecycle과 breaking cutover

이 절은 아래에 남은 Web/URL/loopback·공개 6개·호환 Tool 유지 표현보다 우선하는 현재 상태다.

- public MCP Tool은 adaptive Run 3개, candidate lifecycle 5개, candidate package 4개로 **정확히 12개**다.
- `documentation_start`, `answer_question`, 기존 validate/preview/apply, requirements/architecture/delivery/test/release의 spec_id Tool 10개는 등록·어댑터·전용 UseCase 경로에서 제거됐다.
- lifecycle 구조화 변경은 `candidate_sync_required`를 설정한다. 모델은 candidate Markdown을 갱신한 뒤 새 revision으로 validate/preview한다.
- `presentation/tools/start_spec.py`와 지원 `StartSpecUseCase`는 공개 등록이 없는 고립 레거시다. 물리 제거는 별도 승인 과제이며 현재 기능을 설명하지 않는다.
- Web Wizard와 timeout 자동 재개는 제품 경로가 아니며, client-native UI의 세션 재개는 각 MCP 클라이언트 책임이다.

## 0. 2026-09-12 구현 보정 — URL 재개 대신 동기 대기형 Tool 체인

단계 1의 실제 Codex Desktop 수용 결과는 URL elicitation을 Tool 오류·링크로 표시했고, 브라우저 POST
뒤 원래 Tool 호출을 자동 재시도하지 않았다. 따라서 이 문서의 URL elicitation·서버 worker를 기본으로
삼는 표현은 **현재 구현 경로에서 대체**한다.

```text
documentation_start_adaptive_wizard(phase=intake)
  → loopback HTTP 1차 form 제출까지 Tool 호출 유지
  → 모델이 같은 턴에서 저장소·답변 분석
  → documentation_start_adaptive_wizard(phase=design)
  → loopback HTTP 2차 form 제출까지 Tool 호출 유지
  → DRAFT_READY + spec_id + candidate_root
  → Skill이 candidate_root에 후보 저작
  → package_status → validate_package → preview_package
  → write_policy별 결과(generate_only | safe_auto_apply | manual_apply)
```

- 이 방식은 서버 worker나 모델 API 없이, 이미 실사용에서 확인된 blocking form의 **살아 있는 MCP Tool
  호출**에 모델 재개를 결속한다.
- SQLite Run은 `request_key`, version, 제출 hash, 불변 `write_policy`, 2차 질문, `spec_id`, 서버 발급
  candidate root, candidate revision, preview hash와 적용 결과를 보관한다. 인메모리 기존 `SpecDraft`가
  서버 재시작으로 사라지면 같은 2차 호출이 결정적 `spec_id`로 재수화한다.
- 현재 구현은 2차 제출 뒤 Skill이 candidate를 저작할 경로를 발급하고 `documentation_package_status →
  documentation_validate_package → documentation_preview_package`를 같은 턴에서 진행하도록 한다.
  candidate 본문은 디스크에 남고, process-local preview apply payload만 재시작 뒤 새 preview로 복구한다.
- `safe_auto_apply`는 preview 단계에서 unmanaged 충돌이 없을 때만 기존 exporter를 내부 호출한다. 충돌이면
  사용자 파일은 보존하고 `CONFLICTED` 상태와 candidate·preview를 남긴다.

### 0.1 2026-09-12 실제 Codex Desktop 보정 — 300초 상한과 사전 승인

실사용 수용 테스트에서 첫 blocking Tool 호출은 약 300초 후 `tools/call` timeout으로 종료됐다. Run과
제출값은 SQLite에 남았고, 같은 `request_key`의 재호출은 저장값을 복구했지만, Codex가 timeout 뒤에
스스로 모델 작업을 재개하지는 않았다. 따라서 "제출 뒤 무채팅 진행"은 **Tool 호출이 살아 있는 시간
안에서만 확인됨**으로 기록한다. timeout 뒤 자동 재개는 사용자 결정에 따라 최후순위다.

동일 테스트에서 최초 자연어 요청이 `.mvpmcp/` 자동 반영을 명시적으로 허용했을 때에만 destructive
`documentation_preview_package`가 `safe_auto_apply` 반영까지 진행됐다. Wizard의 정책 선택은 Run
정책이지만, Codex 플랫폼의 파일 쓰기 권한을 단독으로 대체하지 않는다고 본다.

## 1. 최종 결정

`mvp-mcp`는 정적 템플릿을 채우는 MCP가 아니라, 한 번의 안내된 문서 생성 작업 안에서 사용자의
의도와 저장소 맥락을 수집·해석·검증·안전 반영하는 제품으로 발전한다.

```text
Skill              = 요청·저장소·설문 답변 분석, 맞춤 질문 설계, Markdown 후보 작성, 자체 비평
Harness            = 품질 루브릭, 평가 fixture, 가정/권장안 정책, 회귀·수용 기준
Wizard Coordinator = 2단계 Web Wizard, 영속 Run 상태, 중복 방지, 제출 이벤트·재개
MCP Core           = Run 시작·상태, 후보 검증, preview, 충돌 방지, 정책 기반 안전 반영
```

| 결정 | 승인된 정책 |
|---|---|
| 기본 진입 UX | 사용자 요청 뒤 **1차 Web Wizard를 즉시 연다**. 채팅 질의는 기본 경로가 아니다. |
| 1차 입력 | 공통 8개 내외 + 작업 유형별 3~6개. 작업 유형은 신규 구현·기능 추가·리팩터링·결함 수정·문서/운영 개선이다. |
| 2차 입력 | 최초 요청 + 1차 답변 + 대상 저장소 분석으로 만든 맞춤형 3~7개 질문이다. 1차 질문을 반복하지 않는다. |
| 2차 제출 후 | 살아 있는 Tool 호출에서는 별도 “생성할까요?” 또는 “제출했음” 채팅 없이 후보 패키지·품질 검사·preview를 즉시 실행한다. timeout 뒤 자동 재개는 최후순위다. |
| 추가 질문 | 금지하지 않는다. 다만 산출물 방향을 바꾸는 차단 결정에만 1회, 1~3개 **미니 Wizard**를 허용한다. 나머지는 가정·권장안·미해결 결정으로 기록한다. |
| 파일 반영 | 후보 생성은 무조건 자동이다. 기존 `.mvpmcp/` 쓰기는 1차 Wizard에서 정한 `write_policy`에 따라 자동 반영하거나 충돌 보고로 멈춘다. 생성 완료 시점에 별도 승인 팝업을 띄우지 않는다. |
| 영속성 | 2단계 비동기 흐름과 자동 재개가 제품 약속이므로 Run 상태는 영속 저장한다. 인메모리 세션은 사용하지 않는다. |
| 산출물 구조 | `ARCHITECTURE.md`가 기술 스택 표와 디렉터리 구조의 SSOT가 된다. 정적 Kotlin 예시는 사용하지 않고, 설문·저장소 근거에 맞춰 생성한다. |

## 2. 구현 전 최종 검증

| 확인 항목 | 현재 구현 사실 | 최종 판단 |
|---|---|---|
| 공개 Tool | 12개이며 intake·등록·설계·배포 기록까지 Tool 순서가 공개돼 있다 | 문서 저작 Tool을 Skill로 흡수하고 공개 MCP Tool은 6개로 축소한다 |
| Web Wizard | `LocalWebSurveyForm.ask()`가 Tool 호출을 동기 대기한다 | **보정:** 이 검증된 방식을 2단계 영속 Run으로 확장한다. URL elicitation·비차단 재개는 기본 경로로 쓰지 않는다 |
| 재개 코드 | `open()`과 Begin/Submit/Resume UseCase는 있으나 활성 조립·등록 경로가 아니다 | 미등록 코드를 보수하지 않는다. 새 Run 계약과 영속 저장소로 재구성한다 |
| 상태 저장 | `InMemorySpecRepository`와 메모리 preview 상태를 사용한다 | Run·제출·idempotency·후보 메타데이터는 SQLite 기반 저장소로 영속화한다 |
| 산출물 작성 | Pydantic 입력을 renderer가 일반 템플릿 문서로 변환한다 | Skill이 근거 기반 Markdown 후보를 직접 작성하고 MCP는 정책 검증·preview·apply만 맡는다 |
| 적용 안전성 | 현재 exporter는 hash, manifest, unmanaged 충돌, staging, backup, rollback을 제공한다 | 이 계약을 후보 패키지에도 보존·확장한다 |
| 문서 계약 | 현재 `ARCHITECTURE.md`에 기술 스택·디렉터리 구조 섹션이 없다 | 두 섹션을 Architecture 계약에 추가하고 다른 문서에는 요약·참조만 둔다 |

현재 서버는 로컬 HTTP Wizard thread와 비차단 `open()`의 기반은 갖고 있지만, 실제 경로는 blocking
`ask()`와 인메모리 저장소를 사용한다. 2026-09-12 구현은 이 동기 대기 계약을 보존한 채 Run 상태만
SQLite로 영속화했다. 따라서 client 자동 retry나 서버 측 모델 worker를 전제하지 않는다.

## 3. 목표 사용자 흐름과 상태 계약

```text
사용자 요청
  → documentation_start_adaptive_wizard
  → 1차 Wizard 제출
  → 요청·답변·저장소 분석
  → 2차 맞춤 Wizard 제출
  → 후보 문서 생성 + Harness 비평 + validate + preview
  → 후보 산출물·preview 결과 표시
  → write_policy가 safe_auto_apply이고 충돌이 없으면 자동 반영
     그렇지 않으면 후보와 충돌 보고만 제공
```

### 3.1 Run 상태

```text
CREATED
→ INTAKE_OPEN
→ INTAKE_SUBMITTED
→ ANALYZING
→ DESIGN_OPEN
→ DESIGN_SUBMITTED
→ GENERATING
→ CANDIDATE_READY → PREVIEW_READY

보완 필요 시: GENERATING → CLARIFICATION_OPEN → CLARIFICATION_SUBMITTED → GENERATING

자동 반영 시: PREVIEW_READY → APPLIED | CONFLICTED
수동 반영 시: PREVIEW_READY → APPLIED | CONFLICTED
generate_only: PREVIEW_READY를 결과 상태로 유지

사용자 취소 시: INTAKE_OPEN | DESIGN_OPEN | CLARIFICATION_OPEN → CANCELLED

복구 필요 시: 비종결 상태 → FAILED_RETRYABLE → 마지막 멱등 action 재시도 → FAILED
```

- 각 전이는 서버 측 비교-교환 또는 버전 검사를 통과해야 한다.
- 제출에는 `submission_id`와 payload hash를 저장해 더블 클릭·네트워크 재시도를 멱등 처리한다.
- 같은 `run_id`에서 이미 만든 2차 Wizard 또는 후보를 다시 만들지 않는다.
- 재시작 뒤 `documentation_wizard_run_status`는 정확한 다음 상태·복구 링크·실패 이유를 반환한다.
- 만료는 `FAILED_RETRYABLE` 또는 `FAILED`, 사용자의 취소는 `CANCELLED`, 반영 충돌은
  `CONFLICTED`로 명시한다. 어느 경우도 새 설문으로 위장하지 않는다.

| 현재 상태 | 이벤트·실행자 | 단 한 번만 허용되는 부작용 | 다음 상태 | 재시도·복구 규칙 |
|---|---|---|---|---|
| `CREATED` | start Tool / MCP adapter | Run·불변 `write_policy`·1차 URL 저장 | `INTAKE_OPEN` | 같은 `request_key`는 기존 Run 반환 |
| `INTAKE_OPEN` | 1차 POST / Wizard UI | 1차 답변 snapshot 저장 | `INTAKE_SUBMITTED` | 같은 `submission_id`·hash는 기존 결과 반환 |
| `INTAKE_SUBMITTED` | job claim / Coordinator | `ANALYZE_STAGE_1` outbox 기록·전달 | `ANALYZING` | lease 만료 뒤 같은 outbox만 재전달 |
| `ANALYZING` | 1차 분석 완료 / Skill | 2차 schema·URL 저장 | `DESIGN_OPEN` | version이 같으면 기존 2차 Wizard 반환 |
| `DESIGN_OPEN` | 2차 POST / Wizard UI | 2차 답변 snapshot 저장 | `DESIGN_SUBMITTED` | 같은 제출은 멱등 처리 |
| `DESIGN_SUBMITTED` | job claim / Coordinator | continuation outbox 기록·전달 | `GENERATING` | lease 만료 뒤 같은 job만 재전달 |
| `GENERATING` | candidate 작성 / Skill | 후보 revision·hash 기록 또는 차단 질문 schema 저장 | `CANDIDATE_READY` 또는 `CLARIFICATION_OPEN` | 같은 candidate hash면 다시 쓰지 않고 validate부터 재개 |
| `CLARIFICATION_OPEN` | 미니 Wizard POST / UI | 보완 답변 snapshot 저장 | `CLARIFICATION_SUBMITTED` | 최대 한 번, 같은 제출은 멱등 처리 |
| `CLARIFICATION_SUBMITTED` | job claim / Coordinator | `GENERATE_CANDIDATE` outbox 재전달 | `GENERATING` | 같은 lease의 작업만 재시도 |
| `CANDIDATE_READY` | validate·preview / Skill + MCP Core | preview snapshot·hash 기록 | `PREVIEW_READY` | 같은 revision은 기존 preview 반환 |
| `PREVIEW_READY` | safe auto apply / Coordinator | `safe_auto_apply` 정책일 때만 internal Apply UseCase 실행 | `APPLIED` 또는 `CONFLICTED` | hash·manifest·충돌을 다시 검사 |
| `PREVIEW_READY` | manual apply Tool / MCP Core | preview ID·manifest hash가 같은 경우에만 Apply UseCase 실행 | `APPLIED` 또는 `CONFLICTED` | `manual_apply` 정책에서만 허용; 재호출은 같은 결과 반환 |
| `INTAKE_OPEN`·`DESIGN_OPEN`·`CLARIFICATION_OPEN` | 사용자 취소 / Wizard UI | 취소 사유·시각 저장 | `CANCELLED` | 재개하지 않음; 새 요청은 새 `request_key` 필요 |
| `FAILED_RETRYABLE` | lease 만료·일시 오류 / Coordinator | 마지막 action의 outbox 재생성 | 원래 비종결 상태 또는 `FAILED` | retry budget 초과 시 `FAILED` |

`APPLIED`, `CONFLICTED`, `CANCELLED`, `FAILED`는 종결 상태다. `PREVIEW_READY`는
`generate_only`와 `manual_apply`에서는 종결 대기 상태이며, `manual_apply` Tool 호출 뒤에만 전이한다.

### 3.2 질문 예산과 보완 정책

| 단계 | 질문 수 | 반드시 얻을 정보 | 금지 사항 |
|---|---:|---|---|
| 1차 공통 | 8개 내외 | 작업 유형, 대상 저장소, 문제·목표, 영향 사용자, MVP 범위, 성공 기준, 제약·위험, 반영 정책 | 기술 스택만 먼저 묻기, 모든 유형 질문 노출 |
| 1차 유형별 | 3~6개 | 유형에 맞는 영향·호환성·재현·전환·데이터 판단 | 다른 유형의 세부 질문 반복 |
| 2차 맞춤 | 3~7개 | 분석으로 드러난 상호 배타적 선택, 위험, 핵심 설계 결정 | 1차 답변 재질문, 일반적 체크리스트 |
| 보완 미니 Wizard | 1~3개, 최대 1회 | 산출물 방향을 바꾸는 차단 결정 | 무제한 질문 루프 |

각 질문은 `확정값 입력`, `AI 권장안 사용`, `이번 범위에서 제외` 중 하나를 선택할 수 있다.
`AI 권장안 사용`은 확정 사실이 아니며 산출물의 결정 표에 근거·신뢰도와 함께 기록한다.

### 3.3 Codex 자동 재개 의사결정 게이트

> **구현 보정:** 이 게이트의 URL 자동 재개는 실제 Codex Desktop에서 실패했다. 아래의 URL 기반 분기는
> 역사적 검증 기록으로 남기며, 현재 1·2차 Wizard는 blocking Tool 체인으로 진행한다. 서버 측 worker는
> Codex 모델을 독립적으로 재개할 수 없고 모델 API·인증·감사 범위를 새로 요구하므로 이번 경로에 넣지 않는다.

1. 단계 1은 실제 문서 생성기를 만들기 전의 얇은 capability spike다. 최소 영속 Run과 결정적 stub
   continuation만 사용해 URL 완료 이벤트의 전달 여부를 검증한다.
2. spike 통과 기준은 **브라우저 제출 뒤 사용자가 채팅을 입력하지 않아도 같은 Codex thread의
   `ContinuationRequest`가 수신되고 stub Run이 `CONTINUATION_RECEIVED`에 도달하는 것**이다.
3. 전체 흐름의 `PREVIEW_READY` E2E는 단계 5에서 검증한다. 이를 spike의 선행 조건으로 두지 않는다.
4. spike가 통과하면 Codex URL elicitation과 Run Coordinator를 기본 경로로 쓴다.
5. spike가 실패하면 전체 2단계 자동 생성 구현은 `BLOCKED_BY_CLIENT_CAPABILITY`로 멈춘다. 수동
   “계속”을 기본 UX로 되돌리지 않으며, 서버 측 모델 API worker 도입의 비용·인증·감사 범위를
   별도 사용자 결정으로 제시한다.

MCP URL elicitation 완료 알림은 원래 요청을 시작한 클라이언트에만 전달되고, 클라이언트의
자동 재개는 capability와 구현에 좌우된다. 따라서 이 게이트를 건너뛰고 자동 재개를 약속하지 않는다.
`CONTINUATION_RECEIVED`는 단계 1의 stub 테스트 assertion이며 제품 Run 상태가 아니다.
`BLOCKED_BY_CLIENT_CAPABILITY`는 구현 게이트 결과이며 `documentation_wizard_run_status`가 반환하는
사용자 Run 상태가 아니다.

### 3.4 Skill–Coordinator 내부 handoff 계약

이 handoff는 공개 MCP Tool이 아니다. Coordinator는 Tool adapter를 호출하지 않고, 영속 outbox와
`ClientResumePort`를 통해 동일 Codex thread에 다음 불변 envelope를 전달한다.

```text
ContinuationRequest(
  run_id,
  run_version,
  phase,                    # ANALYZE_STAGE_1 | GENERATE_CANDIDATE | CLARIFY
  project_root,
  candidate_root,           # 서버가 발급한 run 전용 경로
  intake_snapshot_hash,
  design_snapshot_hash?,
  workflow_instruction_version,
  lease_token
)
```

1. 재개된 Skill은 먼저 `documentation_wizard_run_status(run_id)`로 현재 version·lease·입력 snapshot을 읽는다.
2. Skill은 발급받은 `candidate_root` 안에만 Markdown 후보를 작성한다. 임의 후보 경로를 Tool 입력으로 넘기지 않는다.
3. Skill은 `documentation_validate_package`와 `documentation_preview_package`에 `run_id`,
   `run_version`, `candidate_revision`을 전달한다.
4. preview UseCase가 candidate hash·preview hash·완료 ACK를 같은 Run version에 기록한다.
5. 후보 작성 중 프로세스가 종료되면 Coordinator는 candidate hash를 검사해 같은 본문을 다시 만들지 않고
   validate/preview부터 재개한다. lease가 유효한 다른 continuation은 완료 ACK를 쓸 수 없다.

따라서 문서 저작은 Skill에 남고, Run 상태·전달·재시도·완료 ACK는 Coordinator에 남는다.

## 4. 책임 경계

| 책임 | Skill | Harness | Wizard Coordinator | MCP Core |
|---|---:|---:|---:|---:|
| 최초 요청·저장소 분석 | 책임 | 조사 기준 | - | 상태 조회 보조 |
| 1차·2차 질문 내용 설계 | 책임 | 질문 품질 기준 | 스키마 렌더·제출 | URL/form 요청 보조 |
| Run 생성·상태 전이·중복 방지 | - | 재개 정책 | 책임 | 상태 Tool 노출 |
| Markdown 후보 본문 저작 | 책임 | 비평 기준 | 작업 dispatch | - |
| 기술 스택·디렉터리 구조 생성 | 책임 | 근거·정합성 검사 | - | 구조 정책 검사 |
| 문서 품질 평가 | 자체 비평 | 책임 | 결과 저장 | 결정적 구조 검사 |
| 후보·기존 패키지 diff | - | - | 결과 연결 | 책임 |
| 파일 충돌·hash·원자적 write·rollback | - | 반영 정책 | 실행 요청 | 책임 |

Skill은 모델의 사고와 문서 저작을 소유한다. Worker는 모델의 사고를 복제하지 않고, 비동기 상태와
작업 재개를 소유한다. 서버 측 모델 API worker는 Codex 재개 capability가 실패했을 때만 별도 승인
후 검토하는 대안이며, 이번 구현의 기본 의존성으로 추가하지 않는다.

## 5. 최종 MCP Tool 계약 — 공개 6개

Wizard의 브라우저 POST·상태 이벤트는 내부 UI API이며 MCP Tool로 노출하지 않는다. 문항별
`register_*` Tool도 다시 만들지 않는다.

| Tool | 주요 입력 | 결과 | 특성 |
|---|---|---|---|
| `documentation_start_adaptive_wizard` | `user_request`, 절대 `project_root`, 불변 `write_policy`, 필수 `request_key` | `run_id`, 1차 URL, `run_version`, 상태 | Run 생성·Wizard 열기. 같은 request key는 기존 Run 반환 |
| `documentation_wizard_run_status` | `run_id` | 현재 상태, 재개 URL, 후보·preview 참조, 오류 | 읽기 전용. 새 Wizard를 만들지 않음 |
| `documentation_validate_package` | `run_id`, `run_version`, `candidate_revision` | 구조·추적성·정책 위반, 다음 version | 결정적 검증 후 성공 revision만 Run에 결속한다. 후보 경로는 서버가 Run으로 해석 |
| `documentation_preview_package` | `run_id`, `run_version`, `candidate_revision` | CREATE/UPDATE/KEEP/CONFLICT/STALE, preview hash | generate/manual은 대상 파일 변경 없음. `safe_auto_apply`는 충돌이 없을 때 내부 Apply도 실행하므로 destructive로 표시 |
| `documentation_apply_package` | `run_id`, preview ID, manifest hash | `APPLIED` / `CONFLICTED` / `POLICY_DENIED`, 적용·보존 파일 | `manual_apply`에서만 실행한다. `safe_auto_apply`는 내부 Apply UseCase가 호출하고 그 밖의 정책은 거부한다 |
| `documentation_package_status` | `run_id` | candidate revision·validation, manifest, 관리 파일, stale, 마지막 적용 상태 | 읽기 전용 진단 |

Tool에는 Pydantic 입력·출력 모델, 좁은 설명, 구조화 결과, `readOnlyHint`/`destructiveHint`/`idempotentHint`
주석을 제공한다. `run_id`, `request_key`, `candidate_revision`, preview ID, manifest hash는 모두 불투명
식별자이며 경로·정책을 클라이언트가 바꾸는 입력으로 받지 않는다. validate는 Run metadata를 기록하므로
read-only가 아니고, `preview_package`는 `safe_auto_apply`일 때 실제 파일 변경이 가능하므로 destructive로
표시한다. 내부 Apply는 1차 Wizard에서 저장한 불변 반영 정책과 hash·충돌 검사를 모두 통과했을 때만 실행한다.

### 5.1 write_policy

| 정책 | 2차 제출 뒤 동작 | `documentation_apply_package` 동작 |
|---|---|---|
| `generate_only` (기본) | 후보 패키지와 preview를 즉시 생성한다. `<project_root>/.mvpmcp/`는 바꾸지 않는다. Run은 `PREVIEW_READY`에 남는다. | `POLICY_DENIED`를 반환한다. |
| `safe_auto_apply` | `documentation_preview_package`가 새 파일 또는 manifest 관리·미수정 파일만 내부 자동 반영한다. 충돌 파일은 보존하고 후보·충돌 보고를 남긴다. | `POLICY_DENIED`를 반환한다. 내부 Apply 성공은 `APPLIED`, 충돌은 `CONFLICTED`다. |
| `manual_apply` | 후보·preview만 생성한 뒤 `PREVIEW_READY`에 남는다. 기존 수동 운영 호환용이다. | preview ID·manifest hash가 일치하면 적용해 `APPLIED` 또는 `CONFLICTED`를 반환한다. |

따라서 “산출물 생성 여부”는 절대 묻지 않는다. 반영 정책은 최초 Wizard에서 한 번만 정해 Run에
고정하며, 이후 Tool·Coordinator·Skill이 이를 승격하거나 완화할 수 없다. `manual_apply`는 1차에서
명시적으로 선택한 호환 정책일 뿐, 후보 생성 후 새 승인 팝업을 요구하는 기본 경로가 아니다. 충돌은
사용자 파일을 덮지 않고 결과로 보고한다.

## 6. 후보 패키지와 산출물 계약

### 6.1 생성 위치와 반영 위치

```text
<mvp_mcp_output_dir>/runs/<run_id>/candidate/   # 2차 제출 뒤 즉시 생성되는 후보
<mvp_mcp_output_dir>/previews/<run_id>/<id>/    # preview snapshot
<project_root>/.mvpmcp/                         # write_policy가 허용할 때만 반영되는 관리 패키지
```

후보와 preview는 산출물이다. 기존 프로젝트의 `.mvpmcp/` 반영이 충돌로 막혀도 사용자는 문서를
받으며, 충돌 파일만 보존된다.

### 6.2 기본 패키지 구조

```text
.mvpmcp/
├── README.md
├── AGENTS.md
├── .manifest.json
├── docs/
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md              # 기술 스택·디렉터리 구조의 SSOT
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TEST_PLAN.md
│   ├── RELEASE_RUNBOOK.md
│   ├── SECURITY_PRIVACY.md          # 조건부
│   └── MIGRATION_PLAN.md            # 조건부
├── api/
│   └── openapi.yaml                 # 조건부
├── prototype/
│   └── index.html                   # 조건부·비권위 자료
└── artifacts/                       # 실제 실행 증거만 기록
```

저위험 프로토타입 프로파일은 기존 계약대로 `DELIVERY_CHECKLIST.md`를 사용해 기본 6문서를
대체할 수 있다. 새 프로파일을 추가하기 전에는 현재 가이드 계약과 coverage fixture를 갱신한다.

| 프로파일 | 선택 조건 | validator가 기대하는 문서 |
|---|---|---|
| 기본 6문서 | `prototype_only`가 아니거나 보안·데이터 변경·운영 위험 신호가 있음 | REQUIREMENTS, ARCHITECTURE, AGENTS, IMPLEMENTATION_PLAN, TEST_PLAN, RELEASE_RUNBOOK |
| `PROTOTYPE_4` | 1차 Wizard에서 프로토타입 전용을 선택하고, 인증·개인정보·결제·외부 쓰기·데이터 마이그레이션이 없으며, 저위험 확인 항목을 모두 통과 | REQUIREMENTS, ARCHITECTURE, AGENTS, DELIVERY_CHECKLIST |
| 보안 확장 | 인증·권한·개인정보·결제·민감 자산·외부 공급망 위험 중 하나가 확인됨 | 기본 6문서 + SECURITY_PRIVACY |
| 마이그레이션 확장 | 기존 데이터 구조·변환·복구 절차가 영향을 받음 | 기본 6문서 + MIGRATION_PLAN |
| 전체 위험 확장 | 보안·마이그레이션 조건이 모두 참 | 기본 6문서 + SECURITY_PRIVACY + MIGRATION_PLAN |

`prototype/index.html`과 `api/openapi.yaml`은 각각 화면 검증 또는 HTTP API 계약이 필요한 경우에만
추가한다. 선택 조건과 실제 파일 집합은 Run에 기록하고 validator가 profile별로 결정한다.

### 6.3 기술 스택 표와 디렉터리 구조의 소유 위치

| 문서 | 새로 또는 계속 소유할 내용 | 중복 방지 규칙 |
|---|---|---|
| `docs/ARCHITECTURE.md` | **`## 기술 스택`**, **`## 디렉터리 구조`**, 구조·컴포넌트·ADR | 기술 선택과 트리의 SSOT. 전체 표·트리는 여기만 둔다. |
| `docs/REQUIREMENTS.md` | 사용자가 요구한 기술 제약·호환성·비범위 | 기술 구현 상세를 반복하지 않고 Architecture 링크를 둔다. |
| `docs/IMPLEMENTATION_PLAN.md` | TASK별 변경 파일·대상 경로·상태·검증 증거 | Architecture의 트리 경로를 참조하고 변경 행만 표시한다. |
| `AGENTS.md` | Agent용 짧은 경로 지도·수정 규칙 | 전체 트리를 복제하지 않고 Architecture 링크를 둔다. |
| `README.md` | 패키지 탐색 링크·생성 범위 | 기술 표를 복제하지 않는다. |
| `SECURITY_PRIVACY.md` | 데이터·권한·외부 연동에 따른 보안 선택 | Architecture의 선택 근거와 TEST-SEC를 참조한다. |

`ARCHITECTURE.md` 계약은 기존 `변경 후 구조` 바로 뒤에 다음 두 섹션을 추가한다.

````markdown
## 기술 스택

| 분류 | 기술·버전 | 역할 | 근거 상태 | 결정·근거 |
|---|---|---|---|---|
| Language | Kotlin 2.x | Android 앱 구현 | CONFIRMED | 1차 Wizard 답변 |
| UI | Jetpack Compose / Material3 | 화면·상태 표현 | DETECTED | Gradle catalog 확인 |

## 디렉터리 구조

```bash
app/
├── feature/alarm/            # [NEW] 알람 기능
├── core/data/                # [KEEP] 데이터 공통 계층
└── ...
```
````

위 Kotlin 표는 형식 예시일 뿐이다. 실제 생성기는 사용자 답변, 저장소 조사, 버전 파일·의존성 파일,
명시된 제약에서 확인한 기술만 기록한다. 각 행은 `CONFIRMED`, `DETECTED`, `RECOMMENDED`,
`UNRESOLVED` 중 하나의 근거 상태와 ADR 또는 조사 근거를 가진다. 미확인 기술·경로는 사실처럼
표시하지 않는다.

디렉터리 구조에는 `[KEEP]`, `[NEW]`, `[MODIFY]`, `[REMOVE]`, `[OPTIONAL]`를 붙이고, 기존
프로젝트에서는 저장소에서 확인한 경로만 표시한다. 신규 프로젝트에서는 계획 경로임을 명확히 한다.

## 7. mvp-mcp 자체의 목표 기술 스택과 디렉터리 구조

이 표와 트리는 **이번 리팩터링 대상 서버**의 구현 계획이다. 아직 설치·구현됐다는 뜻이 아니다.

### 7.1 목표 기술 스택

| 분류 | 기술·방식 | 상태 | 역할 |
|---|---|---|---|
| Language / Runtime | Python 3.11+ | 현재 | 서버·도메인 구현 |
| MCP Runtime | MCP Python SDK + FastMCP | 현재, capability spike 필요 | Tool·Resource·elicitation 연동 |
| 입력·출력 모델 | Pydantic | 현재 | Tool·Run·후보 패키지 계약 검증 |
| Wizard UI | 로컬 loopback Web UI | 단계 2·3 구현 | 2단계 적응형 양식 렌더·제출. URL elicitation은 spike 전용으로 격리 |
| Run 영속성 | SQLite | 변경 예정 | Run·제출·idempotency·후보 메타데이터 복구 |
| 실행 방식 | 현재 Tool 호출을 유지하는 blocking coordinator | 단계 2·3 구현 | 1·2차 제출 뒤 같은 모델 턴으로 반환. 독립 worker는 후보 package 단계의 별도 결정 |
| 문서 생성 | Codex Skill + Harness | 변경 예정 | 저장소 분석·Markdown 후보·자체 비평 |
| 파일 안전성 | SHA-256 manifest, preview, staging, backup, rollback | 현재 유지·확장 | 충돌 방지와 안전 반영 |
| 품질 게이트 | ruff, black, mypy, pytest, Playwright, 평가 fixture | 현재 유지·확장 | 코드·E2E·산출물 품질 회귀 방지 |

서버 측 모델 API, Redis, Celery, 이벤트 버스, 대형 DI 컨테이너는 이번 기본 스택이 아니다. Codex
자동 재개 capability가 실패했을 때만 서버 측 모델 worker를 별도 의사결정으로 평가한다.

### 7.2 목표 소스 구조

```text
mvp-mcp/
├── src/mvp_mcp/
│   ├── main.py                              # Composition Root: 구현체 조립·Tool 등록만
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── security.py                      # 후보·출력 경로 정책
│   ├── domain/spec/
│   │   ├── run_model.py                     # Run, 단계, 제출본, write_policy
│   │   ├── run_ports.py                     # RunRepository·RunDispatcher 등 필요한 Port
│   │   ├── run_usecase.py                   # 시작·제출·상태 전이·재개
│   │   ├── wizard_policy.py                 # 1차/2차 질문 선택·보완 질문 한도
│   │   ├── package_model.py                 # 후보·검증·preview 모델
│   │   ├── package_policy.py                # 문서 구조·추적성·근거 상태 검사
│   │   ├── package_usecase.py               # validate·preview·apply 오케스트레이션
│   │   └── guide_contract.py                # 기술 스택·디렉터리 구조를 포함한 문서 계약
│   ├── data/spec/
│   │   ├── sqlite_run_repository.py         # 영속 Run 저장소
│   │   ├── run_dispatcher.py                # durable Coordinator 구현
│   │   ├── candidate_package_repository.py  # 후보·preview artifact 저장
│   │   └── repository_document_exporter.py  # hash·충돌·원자 반영 유지
│   └── presentation/
│       ├── _safe.py
│       ├── tools/
│       │   ├── documentation_start_adaptive_wizard.py
│       │   ├── documentation_wizard_run_status.py
│       │   ├── documentation_validate_package.py
│       │   ├── documentation_preview_package.py
│       │   ├── documentation_apply_package.py
│       │   └── documentation_package_status.py
│       ├── resources/
│       ├── prompts/
│       └── web/
│           └── adaptive_wizard.py            # 2단계 UI adapter; 비즈니스 규칙 없음
└── tests/
    ├── fixtures/evaluations/
    ├── test_adaptive_wizard.py
    ├── test_run_recovery.py
    ├── test_candidate_package.py
    ├── test_package_policy.py
    └── test_skill_evaluations.py
```

실제 파일 이동은 한 번에 하지 않는다. 기존 `spec` 도메인과 가드레일을 유지한 채 새 경로를
작은 수용 기준 단위로 추가하고, 활성 경로가 전환된 뒤에만 미등록·구형 Tool/UseCase를 제거한다.

## 8. Harness와 평가 fixture

| 품질 범주 | 차단 또는 보완 조건 | 기대 동작 |
|---|---|---|
| 구체성 | 사용자·문제·성공 기준이 일반 문구뿐임 | 2차 질문 또는 가정 표기 |
| 범위 | 제품 수준 기능이 모두 P0에 섞임 | MVP 슬라이스·비범위 분리 |
| 기존 영향 | 기능 추가/리팩터링인데 기존 계약·회귀 범위 없음 | 저장소 조사와 영향 분석 보완 |
| 기술 스택 | 저장소 근거 없는 기술·버전을 확정으로 씀 | `RECOMMENDED`/`UNRESOLVED` 표시 또는 질문 |
| 디렉터리 구조 | 존재하지 않는 경로를 현재 구조처럼 표기 | 계획 경로 라벨 또는 제거 |
| 추적성 | 무관한 요구사항·TASK·TEST를 모두 연결 | 실제 영향 ID만 연결 |
| 불확실성 | 권장 기본값을 확정 사실처럼 표현 | 결정 상태·근거·신뢰도 분리 |

최소 fixture는 아래를 포함한다.

1. 신규 웹 서비스
2. 기존 API 기능 추가와 호환성 변경
3. 레거시 리팩터링과 성능 기준선
4. 재현 가능한 결함 수정
5. 이미지 라벨링·모델 학습처럼 도메인 결정을 먼저 내려야 하는 사례
6. 1차 제출 뒤 2차 Wizard가 중복으로 열리던 실제 결함
7. 브라우저 제출 뒤 별도 채팅 없이 후보·preview까지 진행해야 하는 자동 재개 사례

## 9. 구현 순서

### 2026-09-13 최종 구현 상태

| 단계 | 상태 | 실제 범위 |
|---:|---|---|
| 12 | 🟢 완료 | client-native 질문 UI로 전환하고 Web Wizard·URL elicitation·대기형 timeout 경로를 폐기했다. |
| 13 | 🟢 완료 | SQLite Run 소유 candidate lifecycle, optimistic version, TEST/RELEASE idempotency와 candidate 재검증 연결을 구현했다. |
| 14 | 🟢 완료 | 구형 spec_id·직접 문서 Tool 10개를 제거하고 canonical 12개 E2E·부재 가드레일을 통과했다. |

이후 표와 세부 단계는 계획 수립 당시의 역사 기록이다. 현재 다음 작업은 `HANDOFF.md`의 별도 승인 게이트를 따른다.

### 2026-09-12 현재 이행 상태

| 단계 | 상태 | 실제 범위 |
|---:|---|---|
| 0 | 🟢 완료 | 단절·중복 설문·URL 재개 실패 fixture를 고정했다. |
| 1 | 🟢 완료 | MCP protocol은 통과했지만 실제 Codex URL 자동 재개가 실패했음을 수용 검증했다. |
| 2 | 🟢 완료 | SQLite Run, request_key 멱등성, 제출 hash, version, 재시작 뒤 draft 재수화를 구현·테스트했다. |
| 3 | 🟢 부분 완료 | 1차/2차 blocking loopback form과 Tool 등록을 구현했다. 실제 Codex는 약 300초 뒤 Tool timeout이 나며 자동 재개하지 않는다. 미니 Wizard·browser 완료 화면과 timeout 대응은 후속 UX 단계다. |
| 4 | 🟢 기본 완료 | Codex Skill 원본을 candidate 저작·revision 재개 흐름으로 전환하고 package 계약·MCP memory E2E를 추가했다. |
| 5 | 🟢 기본 완료 | 서버 발급 candidate root, 구조 검증, preview snapshot, conflict 보존, manual/safe-auto write policy, SQLite 상태 결속과 최초 명시 정책 불변성을 구현했다. |
| 6 | 🟢 완료 | 2차 질문을 typed `design_questions`로 구조화하고 Android/iOS/크로스플랫폼의 모바일 우선 분류를 고정했다. |
| 7 | 🟢 완료 | 후보·renderer의 `ARCHITECTURE.md`에 근거 상태 기술 스택 표·라벨된 디렉터리 트리·구현 계획 SSOT 참조를 계약화했다. |
| 8 | 🟢 완료 | 7개 산출물 품질 루브릭, 5개 대표 evaluation fixture, Codex Skill 자체 점검을 추가했다. |
| 9 | 🟢 기본 완료 | canonical 6개·호환 10개·보조 2개 Tool을 감사·가드레일로 고정했다. 삭제는 별도 승인까지 보류한다. |
| 10 | 🟢 완료 | AST domain import 가드레일, opaque workspace 경계, presentation helper 분리, root artifact inventory를 구현·검증했다. 물리 이동·삭제는 보류한다. |
| 11 | 🟡 일부 완료 | 콘텐츠·레이아웃 수용 기준을 구현했다. 화면별 `ScreenSpec.states` Mock, 흐름/오류/접근성 fixture와 browser 회귀는 통과했고, 시각적 완성도 조정은 별도 요청으로 보류한다. |
| 12 | 🟠 최후순위 | Codex 300초 timeout 뒤 자동 재개 전략은 별도 승인 전 도입하지 않는다. |

| 단계 | 작업 | 완료 기준 |
|---:|---|---|
| 0 | 현행 Tool·Wizard·산출물 실패를 fixture와 E2E 기준선으로 고정 | 중복 설문·제출 후 단절·일반적 ML 문서가 회귀 사례로 존재 |
| 1 | Codex URL elicitation/자동 재개 capability spike | 최소 영속 Run + stub continuation으로 같은 thread의 `CONTINUATION_RECEIVED` 여부가 명확 |
| 2 | Run 도메인 모델·SQLite 저장소·상태 전이·멱등 제출 | 재시작·중복 클릭·만료·취소 테스트 통과 |
| 3 | 1차/2차 적응형 Web Wizard와 Coordinator | 질문 예산·분기·재개 URL·미니 Wizard 정책 E2E 통과 |
| 4 | Skill 단일 흐름 원본·Harness·후보 Markdown 계약 | 가이드·저장소 근거로 후보를 만들고 품질 fixture 통과 |
| 5 | 후보 package validate/preview/write_policy 적용 | 살아 있는 Tool 호출 안에서 1·2차 제출 뒤 사용자 채팅 없이 `PREVIEW_READY`, 후보 즉시 생성, 충돌 보존, safe auto apply 안전성 유지 |
| 6 | 2차 질문 계약 구조화·Wizard 문항/유형 재개편 | typed 질문·Android 모바일 우선 분류·1차 중복 차단 회귀 통과 |
| 7 | 문서 계약에 기술 스택·디렉터리 구조·근거 상태 추가 | Architecture SSOT, 표·트리·구현 계획 참조 검증 통과 |
| 8 | 산출물 품질 루브릭·대표 fixture | 7개 루브릭·5개 사례·Skill 자체 점검 회귀 통과 |
| 9 | MCP 공개 Tool 6개 전환·구형 흐름 정리 검토 | canonical/호환/보조 Tool 가드레일 통과, 삭제는 별도 승인 |
| 10 | Clean Architecture·SOLID 정리와 루트 산출물 정리 | 읽기 전용 감사 뒤 승인된 최소 변경만 적용; 이동·삭제 전 참조·보존 확인 |
| 11 | 문서 서술·프로토타입 품질 고도화 | 대표 fixture 수용 리뷰와 실제 생성 HTML의 화면 캡처·가독성 검토 통과 |
| 12 | Codex 300초 timeout 이후 자동 재개 전략 | 별도 사용자 승인과 client capability 확인 뒤에만 검토 |

단계 6~10은 완료 기록이다. 단계 11은 계약 기반 콘텐츠·레이아웃 보완과 자동 회귀를 마쳤다. 프로토타입의
시각적 완성도·문장 다듬기는 사용자 요청에 따라 별도 작업으로 보류한다.

## 10. 구현 수용 기준

### 사용자 경험

- 요청 뒤 1차 Wizard가 열리고, 1차 제출 뒤 같은 `run_id`의 2차 맞춤 Wizard가 한 번만 열린다.
- 2차 제출 뒤 Tool 호출이 살아 있는 경우 별도 채팅·생성 승인 없이 후보 문서와 preview가 생성된다.
- 차단 결정이 없으면 추가 입력을 요구하지 않는다.
- 차단 결정이 있으면 최대 한 번의 1~3개 미니 Wizard만 요구한다.
- 서버 재시작·브라우저 새로 고침·더블 클릭 뒤에도 중복 문서·중복 2차 Wizard가 생성되지 않는다.
- candidate 작성·preview 완료 ACK는 Run version과 lease를 검증하며, 생성 중 중단된 Run은 같은 후보
  revision을 재사용해 validate/preview부터 재개한다.

### MCP와 안전성

- canonical 공개 Tool은 정확히 6개다. 호환 Tool 10개와 보조 질문 Tool 2개는 별도 승인 전 유지하며,
  삭제 전에 등록·대체 경로·실사용 이행 gate를 확인한다.
- `validate_package`는 구조·필수 ID 연결·근거 상태·경로 정책 위반을 결정적으로 거부한다.
- `preview_package`는 대상 파일을 바꾸지 않고 CREATE/UPDATE/KEEP/CONFLICT/STALE을 반환한다.
- `safe_auto_apply`는 manifest 관리 파일과 현재 hash가 일치하고 충돌이 없을 때만 적용한다.
- 충돌·사용자 수정 파일은 자동 덮어쓰지 않고 후보와 보고서만 남긴다.
- `generate_only`와 `manual_apply` Run은 후보와 preview를 만든 뒤 `PREVIEW_READY`에 머문다.
- Tool 입력은 Run에 결속된 opaque ID만 허용하며, 임의 후보 경로·write policy 변경은 거부한다.

### 산출물 품질

- `ARCHITECTURE.md`에는 근거 상태가 있는 기술 스택 표와 `[KEEP/NEW/MODIFY/REMOVE/OPTIONAL]` 디렉터리 트리가 있다.
- 기술·버전·경로는 Wizard 확정값 또는 저장소 조사 근거 없이 확정 사실로 쓰지 않는다.
- `IMPLEMENTATION_PLAN.md`의 변경 파일 표는 Architecture의 트리 및 TASK와 연결된다.
- 신규·기능 추가·리팩터링·결함 수정은 서로 다른 영향 분석·테스트 계획을 가진다.
- 실제 테스트·출시 증거가 없으면 계속 `NOT RUN` 상태를 유지한다.
- 문서 프로파일은 Wizard 선택·위험 신호에 맞는 정확한 파일 집합을 가지며, validator가 이를 검사한다.

### 유지보수성

- 의존성 조립은 `main.py::build()`에만 둔다.
- `presentation → data → domain → core` 단방향 경계와 `@safe_tool` 패턴을 유지한다.
- 각 단계는 `uv run ruff check`, `uv run black --check src tests`, `uv run mypy src`, `uv run pytest -q` 및 해당 E2E/fixture를 통과한다.

## 11. 위험·비목표·결정 게이트

| 항목 | 정책 |
|---|---|
| Codex 자동 재개 지원 | 단계 1 spike 통과 전에는 보장으로 말하지 않는다. 실패 시 서버 측 모델 worker는 별도 사용자 승인 없이는 도입하지 않는다. |
| Web Wizard 보안 | URL에는 opaque `run_id`만 넣고 비밀·개인정보·답변을 넣지 않는다. loopback/인증·만료·CSRF 정책을 설계한다. |
| 모델 API | 기본 의존성이 아니다. Skill이 수행할 문서 저작을 무단으로 서버 API 호출로 옮기지 않는다. |
| 자동 파일 반영 | 후보 생성과 달리 기존 사용자 수정 파일 overwrite는 허용하지 않는다. |
| 과설계 | Redis, Celery, 이벤트 버스, 대형 DI 컨테이너, 범용 workflow engine을 첫 구현에 도입하지 않는다. |
| 루트 정리 | Git 추적·참조·보존 가치를 확인한 뒤에만 이동·삭제한다. |

## 12. 기대 변화 — 구현 전/후

| 항목 | 현재 | 구현 후 기대값 | 조건 |
|---|---|---|---|
| 입력 경험 | 2단계 loopback Wizard이나 Codex Tool은 약 300초 후 timeout될 수 있음 | 2단계 맞춤 Wizard 안에서 필요한 결정을 수집 | timeout 전 제출 또는 이후 명시적 복구 |
| 재개 | timeout 뒤 자동 재개는 불가하나 Run은 보존 | `run_id`와 상태로 정확한 단계 복구 | SQLite·idempotency 구현; 자동 재개는 최후순위 |
| 산출물 | 일반 기본값·넓은 MVP 가능성 | 답변·저장소 근거·결정 상태가 추적되는 후보 문서 | Skill/Harness fixture 품질 |
| 기술·구조 설명 | Architecture 계약에 명시 표·라벨 트리·SSOT 참조가 있음 | 저장소 근거와 연결된 산출물 품질을 유지 | 문서 계약·validator 반영 완료 |
| 파일 안전성 | 수동 preview/apply는 강함 | 후보 즉시 생성 + write policy 기반 자동 안전 반영 | 충돌·hash 정책 유지 |
| MCP 가치 | canonical 6개와 보존된 호환·보조 Tool이 공존 | 호환 사용량·대체 경로 확인 뒤 별도 삭제 판단 | Tool inventory 감사·가드레일 완료 |

## 13. 다음 구현 채팅의 시작 범위

이 계획의 구현 마일스톤은 완료됐다. 다음 새 작업은 `HANDOFF.md`에 정의된 별도 승인 마일스톤으로만 시작한다.

1. `AGENTS.md`, `README.md`, `HANDOFF.md`, `progress/PROGRESS.md`, `progress/IMPROVEMENT_ROADMAP.md`, 이 문서와 현재 tests를 읽는다.
2. 미등록 `start_spec` 레거시의 물리 정리가 요청되면 먼저 등록·참조·재개 경로를 읽기 전용으로 감사하고 최소 변경 계획만 제시한다.
3. 코드 삭제·이동은 사용자의 명시적 승인 뒤에만 수행한다.
4. 서버 모델 API worker, timeout 자동 재개, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경, 플러그인 재설치는 시작하지 않는다.

## 14. 근거 문서

- 현재 제품 계약: `README.md`, `HANDOFF.md`, `src/mvp_mcp/main.py`, `src/mvp_mcp/domain/spec/guide_contract.py`
- 현재 출력·안전성 구현: `src/mvp_mcp/data/spec/guide_document_renderer.py`, `repository_document_exporter.py`
- MCP URL elicitation: <https://modelcontextprotocol.io/specification/draft/client/elicitation>
- MCP Tasks 확장(지원 여부 확인 필요): <https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks>
- Codex App Server elicitation: <https://learn.chatgpt.com/ko-KR/docs/app-server>

## 15. 변경 기록

| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-09-11 | Skill·Harness·MCP Core 책임 분리 초안 작성 | 현재 Tool·UseCase·exporter·실사용 산출물 감사 |
| 2026-09-11 | 2단계 적응형 Wizard, 영속 Run, 자동 후보 생성, write policy, 기술 스택·디렉터리 구조 산출물 계약을 승인 최종안에 반영 | 사용자 승인과 Codex/MCP 가능성 검토 |
| 2026-09-12 | 실제 Codex Desktop에서 300초 blocking Tool timeout·무자동 재개, 질문 schema 오류 2회, 명시적 사전 승인 기반 safe auto apply 성공을 확인 | 실사용 수용 테스트 |
| 2026-09-12 | typed 2차 질문·모바일 분류, Architecture SSOT 계약, 품질 Harness, Tool inventory 감사를 완료하고 명시 write policy의 Run 불변성을 추가 | `progress/PROGRESS.md`의 완료 검증 기록 |
| 2026-09-13 | client-native 질문 UI 전환 뒤 Run-scoped candidate lifecycle과 breaking cutover를 완료했다. 구형 Tool 10개를 제거하고 canonical 12개만 공개한다. | `progress/PROGRESS.md`, `progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md`, 전체 pytest 65 passed |
