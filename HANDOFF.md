# HANDOFF.md — 현재 인수인계

> 최종 갱신: 2026-09-16
> 현재 상태: **단계 0~14 완료**. 2단계 Adaptive Run은 질문 schema를 즉시 반환하고, 이를 표시·제출하는 UI는
> MCP 클라이언트 호스트의 별도 capability다. 현재 Codex Desktop Default 모드에서는 native form UI가 지원되지 않음이
> 실제 수용 테스트로 확인됐다. localhost Web Wizard·URL elicitation·continuation probe·대기형 timeout 경로는 제거됐고,
> Run 전용 candidate package, Run-scoped 구조화 lifecycle, revision 결속 validate/preview, 산출물 구조·품질 Harness와
> 불변 `write_policy`는 유지한다.

## 2026-09-16 생성 패키지 품질·시각 감사

- 상태: **완료**. 신뢰도: 아래 패키지 무결성·문서 내용·브라우저 관찰은 `확인됨`, 가이드북 반영 점수는 적용 가능한 웹 원칙만 대상으로 한 `추론`이다.
- 대상: 사용자 소유의 추적되지 않은 `recordmvp/adaptive-run-z2kniJ1zXXMTAOXx6ISNDk0G/`를 **읽기 전용**으로 감사했다. 이 패키지와 원본 `design/` 가이드북은 변경하지 않았다.
- 패키지 무결성: `.manifest.json`의 관리 파일 11개가 실제 SHA-256과 모두 일치한다 (`확인됨`). 이는 생성·반영 계약의 무결성만 보장하며, 내용·사용성 품질의 통과를 뜻하지 않는다.
- 디자인 가이드북 반영도: Apple 42/100, Material 3 43/100, 디자인 철학 55/100, 종합 약 47/100 (`추론`). Apple의 하드웨어·visionOS 및 Material의 Android 런타임 전용 항목은 평가에서 제외했다.
- 디자인 계약 한계: `MVPDESIGN.md`는 1~14절 제목은 생성하지만, 결정 상태·근거·전체 팔레트 표 등 완성형 필수 필드가 축약되어 있다. `design-tokens.json`은 light 역할·간격·타입은 있으나 dark·고대비·disabled·container 역할 토큰이 없다. 계약상 직접 Hex 금지와 달리 `prototype/index.html`에는 raw Hex와 인라인 style이 남아 있다 (`확인됨`).
- 프로토타입 한계: 1440px와 375px의 기본 화면은 읽을 수 있으나, 768px에서 입력 작업대의 2열 필드가 우측 요약 패널과 겹친다. 375px에서는 월간 표의 지출 열을 숨겨 핵심 정보를 잃는다. `:focus-visible` 규칙이 없고, 오류 문구는 지출 오류임에도 매출 입력 아래에 표시된다. 날짜·월 이동과 지출 추가는 상태 변화를 만들지 않으며, 빈 상태와 삭제 확인은 실제로 도달할 수 없다 (`확인됨`).
- 자동 검토 한계: 생성된 `prototype/REVIEW.md`의 375/768/1440px 항목은 모두 `NOT RUN`이다. 따라서 자동 산출물의 검토 문서는 실제 브라우저·상호작용 검토 결과를 대체하지 못한다 (`확인됨`).
- 비디자인 문서 품질: `REQUIREMENTS.md` 85/100, `ARCHITECTURE.md` 82/100, `IMPLEMENTATION_PLAN.md` 65/100, `TEST_PLAN.md` 70/100, `RELEASE_RUNBOOK.md` 73/100, 패키지 `AGENTS.md` 78/100, `README.md` 82/100 (`추론`). 전체는 개발 착수용 문서 패키지로 약 74/100이며, 운영 준비도는 약 52/100이다. API 요청·응답·오류 계약, DB 제약, 작업별 파일·완료 증거, 실행 가능한 테스트 절차, 운영 명령·책임자·복구 목표가 남은 보강 항목이다.
- 기존 서버 품질 게이트의 2026-09-16 결과(Ruff·Black·mypy 통과, pytest 77 passed)는 그대로 유효한 과거 검증 기록이다 (`확인됨`). 이번 감사는 문서·정적 목업만 읽고 검토했으므로 애플리케이션 테스트를 재실행하지 않았다.

## 2026-09-16 디자인 계약 기반 문서·프로토타입 생성

- 제품 UI의 2차 설문은 기존 intake와 겹치지 않게 자주 하는 작업, 시각 톤, Seed/Main color를 필수로 받고 웹 앱에는 반응형 동작을 추가한다.
- `DRAFT_READY`에서 서버는 `docs/MVPDESIGN.md`, `docs/design-tokens.json`, `prototype/index.html`, `prototype/REVIEW.md`를 candidate에 초기화한다. 네 파일은 같은 `design_hash`로 결속되며 candidate 검증은 누락·불일치를 거부한다.
- Seed/Main color의 Light/Dark semantic palette와 HTML의 primary·surface·outline·상태·focus 역할 토큰은 구현 계약이다. 다만 같은 날 생성된 식당 기록 관리 표본 감사에서 dark·상태 토큰 완결성, raw Hex 제거, 반응형·상호작용 준수가 충분하지 않음이 확인됐다. 상단의 품질·시각 감사 절이 이 구현 완료 기록보다 우선하는 산출물 품질 사실이다.
- 사용자가 제공한 Apple·Material 3·design philosophy 가이드의 항목별 추적성 매핑은 사용자가 추후 고도화로 미뤘으므로 이번 범위에 넣지 않았다.
- 원본 `design/` 디렉터리는 사용자 작업물로 보존한다.

## 2026-09-14 현재 상태 보정

이 절이 아래의 과거 단계 기록·과거 검증 표와 충돌하는 표현보다 우선한다. 상세 이력은 보존하되,
다음 작업의 현재 사실·승인 게이트는 이 절과 `README.md`, `progress/IMPROVEMENT_ROADMAP.md`,
`progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md`를 따른다.

- 공개 MCP Tool은 **canonical 12개만** 등록한다: Adaptive Run 3개, candidate lifecycle 5개, candidate package 4개.
- `documentation_start`, `answer_question`, 기존 validate/preview/apply, requirements/architecture/delivery/test/release의 spec_id Tool 10개는 **제거 완료**다. MCP 목록과 호출 경로에 없다.
- 서버는 질문 schema만 반환한다. HTML·브라우저·localhost form은 제품 경로가 아니며 자동으로 열리면 회귀다. 실제 UI는
  그 schema를 표시·구조화 답변 제출할 capability를 가진 호스트에서만 가능하다.
- source schema는 `allow_other`, `other_label`, `max_selections`를 지원한다. 선택지는 최대 20개이며,
  선택+기타는 `{"selected": [...], "other_text": "..."}`로 보존한다. 기존 `str`·`list[str]` 답변은 그대로
  호환된다. Run status도 이 구조화 답변을 JSON으로 안전하게 반환한다.
- source integration 지침은 Codex Plan의 `request_user_input`, Claude의 `AskUserQuestion`, Gemini CLI의
  `ask_user`, Antigravity의 `ask_question`을 사용해 조건부 문항을 1~3개씩 묶는다. 4~20개 선택지는
  `다음 선택지`로 페이지를 넘기고, 복수 선택은 포함/제외로 수집한다. Codex는 사용자가 수동으로 Plan 모드를
  켠 경우만 Run을 연다. 스킬은 `/plan`을 자동 활성화하지 않는다. 저장 방식은 native 질문으로 묻지 않으며,
  기본 `safe_auto_apply`가 검증된 문서를 `.mvpmcp/<spec_id>/`에만 반영한다.
- 새 Run은 `write_policy`를 생략하면 `safe_auto_apply`로 고정된다. `generate_only`는 사용자가 후보만
  명시적으로 요청할 때만 사용한다. 같은 Run은 자신이 관리한 문서를 갱신할 수 있지만, 기존 `.mvpmcp` 루트와
  다른 `<spec_id>` 폴더는 절대 덮어쓰지 않는다.
- 2026-09-14 P0에서 저장소의 최신 Codex Skill·`.mcp.json`·manifest 설명을 개인 원본
  `C:\\Users\\user\\plugins\\mvpmcp`에 동기화하고, 공식 cachebuster·재설치로 설치본에 반영했다. 사용자
  `.mvpmcp/`와 후보 문서는 변경하지 않았다.
- 기본 Run의 candidate 작성·검증·preview 완료는 `.mvpmcp/<spec_id>/` 문서 패키지 저장 완료일 뿐 제품 코드
  구현 권한이 아니다. 완료 뒤 제품 구현을 묻지 않으며 **`MVP 제품 코드 구현 시작`**이라는 명시 요청 없이는
  대상 제품 소스를 만들 수 없다. 명시적 `generate_only`만 candidate·preview만 남긴다.
- 2026-09-13 사용자가 Ruff·Black·mypy·전체 pytest를 직접 재실행하여 **65 passed**를 확인했다 (`확인됨`).
- 설치된 개인 플러그인 cache는 2026-09-14 `mvpmcp@personal` 공식 재설치로
  `0.2.0+codex.20260914012647`이 됐다. 저장소·원본·설치 cache의 Codex Skill SHA-256은 일치하고,
  원본과 설치 cache 모두 plugin validation을 통과했다. cache는 직접 수정하지 않았다.
- 동기화 원본은 `C:\\Users\\user\\plugins\\mvpmcp`이며 개인 marketplace `personal`이 이를 가리킨다.
  이번 동기화 전 세 배포 파일은 `C:\\Users\\user\\plugins\\mvpmcp.backup-20260914-092702`에 백업했다.
  기본 `.mvpmcp/<spec_id>` 저장 계약 동기화 전 파일은
  `C:\\Users\\user\\plugins\\mvpmcp.backup-20260914-102534`에 추가 보존했다.
  새 Skill·MCP Tool은 **새 Codex `/plan` task**에서만 로드된다. 2026-09-14 사용자 수용 테스트에서 새
  Plan task의 `$mvpmcp` 대표 요청이 native 질문 묶음, `safe_auto_apply`, `APPLIED`까지 완료하고
  `C:\\Users\\user\\Documents\\rrr\\.mvpmcp\\adaptive-run-Ie_LD2OjUrCy3fj3DiVU2Xpr`에 문서 패키지를
  저장했다 (`확인됨`). 이 Run에서 Android 제품 코드·빌드·테스트·배포 Tool 호출은 없었다 (`확인됨`).
- 수용 기록에 보인 Codex UI의 `Plan implementation — Status: running`은 문서 저장 뒤 표시된 호스트 UI
  상태다. MCP 결과는 문서만 `APPLIED`로 반환했고 제품 코드 Tool 호출 근거가 없으므로, 제품 구현 시작을 뜻하지
  않는 것으로 판단한다 (`추론`). UI 문구 자체는 여전히 사용자에게 혼동을 줄 수 있다.
- 기본 문서 저장 계약 배포 후 저장소 품질 게이트는 Ruff·Black·mypy 통과 및 pytest **73 passed**다. Black/pytest cache의
  Windows 쓰기 권한 경고만 있었고 결과에는 영향을 주지 않았다.
- 2026-09-13 실제 Codex Desktop 재개 수용 테스트에서 `documentation_wizard_run_status(run_id)`는 `INTAKE_OPEN`과 저장된 `intake_questions`를 반환했다(`확인됨`). Default 모드는 native form UI를 지원하지 않아 질문 표시·답변 제출 없이 종료했다(`확인됨`). 공식 [Codex App Server 문서](https://learn.chatgpt.com/docs/app-server)는 `openai/form`을 capability를 선언한 호스트 통합의 기능으로 설명하며, 현재 Desktop에서 선택할 수 있는 모드라고 보장하지 않는다.
- 미등록 `start_spec` 및 구형 채팅형 adapter 체인은 2026-09-13 별도 승인 마일스톤에서 제거 완료했다. canonical 12개 공개 Tool과 Adaptive Wizard·Resource 계약은 유지한다.

## 먼저 읽을 문서

1. `AGENTS.md` — 계층·조립·검증 절대 규칙
2. `README.md` — 현재 공개 워크플로와 `.mvpmcp/` 산출 계약
3. 이 문서 — 최신 구현 상태·한계·다음 승인 게이트
4. `progress/PROGRESS.md` — 작업별 시간순 기록과 완료 검증 근거
5. `progress/IMPROVEMENT_ROADMAP.md` — 단계 0~14 완료 상태와 범위 원칙
6. `progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md` — canonical 12개·제거된 구형 Tool 10개 공개 계약
7. `progress/FINAL_SKILL_HARNESS_MCP_REFACTORING_PLAN.md` — **역사 계획**: 아래 과거 Web/URL·6개 Tool 표현보다 상단 2026-09-13 보정이 우선
8. `progress/ROOT_ARTIFACT_AUDIT.md` — 물리 정리 전 루트 문서·설정·runtime 산출물의 보존 역할과 참조 게이트

제품 문서 계약의 유일한 기준은 사용자가 제공한
`HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.md`다. 고정 원본 SHA-256은
`2c4d944af733a37e4d6b4925695fb261cb30a0715087e26505ab35544702f96d`이며
`references/HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.sha256`과 coverage fixture가 이를 확인한다.
다른 계획 문서는 제품 계약의 근거로 사용하지 않는다.

## 현재 제품 계약

```text
documentation_start_adaptive_wizard(phase=intake)
→ 1차 questions schema 즉시 반환
→ schema를 표시할 capability가 있는 MCP 클라이언트 호스트
→ documentation_submit_adaptive_wizard_answers(phase=intake, answers)
→ 같은 모델 턴에서 요청·저장소·1차 답변 분석
→ documentation_start_adaptive_wizard(phase=design)
→ 2차 questions schema 즉시 반환 → capability가 있는 호스트 UI
→ documentation_submit_adaptive_wizard_answers(phase=design, answers)
→ DRAFT_READY + spec_id + candidate_root
→ documentation_update_candidate_requirements → architecture → delivery
→ Skill/모델이 candidate_lifecycle를 candidate_root의 후보 문서에 반영
→ documentation_package_status
→ documentation_validate_package
→ documentation_preview_package
→ 기본 safe_auto_apply로 <project_root>/.mvpmcp/<spec_id>/ 문서만 반영
```

canonical 호출은 `write_policy`를 생략하며 서버가 기본 `safe_auto_apply`를 Run에 결속한다. 이 정책은
1·2차 질문 schema에서 묻지 않고, 검증·preview에 충돌이 없을 때 Run 전용 `.mvpmcp/<spec_id>/`에만 문서를
반영한다. 사용자가 후보만 명시적으로 요청한 경우만 `generate_only`를 전달한다. 2차 질문의
`document_output_mode` 재질문과 같은 `request_key`의 정책 변경은 거부된다.

기존 `documentation_start`, `answer_question`, `documentation_validate`/`documentation_preview`/
`documentation_apply`, requirements·architecture·delivery·test run·release의 spec_id Tool 10개는 이번
breaking release에서 **제거 완료**됐다. 각각 Run-scoped candidate lifecycle Tool로 직접 대체되며, 구형
이름은 MCP에서 찾을 수 없다.
`documentation_wizard_run_status`는 Run snapshot과 현재 열린 질문 schema를,
`documentation_package_status`는 candidate·preview·manifest 복구 정보를 읽기 전용으로 반환한다.
새 경로는 브라우저 POST나 별도 `제출했음` 채팅을 요구하지 않는다. 그러나 현재 Codex Desktop Default 모드는
schema를 native form으로 표시할 수 없으므로 이 제품 흐름을 끝까지 수행할 수 없다. `request_user_input`은
사용자가 Desktop에서 켜는 MCP form 기능이 아니다. 호스트 UI의 세션 만료·재개 보장은 각 클라이언트 책임이며,
서버 worker/timeout 자동 재개는 구현하지 않았다.

실제 테스트·출시가 있으면 각각 `documentation_record_candidate_test_run`,
`documentation_record_candidate_release`로 Run에 append-only 기록한다. 실행하지 않은 결과는 `NOT RUN`이다.

### 2026-09-13 Run-scoped candidate lifecycle

- `documentation_update_candidate_requirements`·architecture·delivery와
  `documentation_record_candidate_test_run`·release가 SQLite Run 안에 구조화 계약과 실행 기록을 저장한다.
  모든 변경은 `expected_run_version`을 확인하고, TEST/RELEASE 재시도는 `idempotency_key`를 유지한다.
- 요구사항/설계/전달 변경은 하위 lifecycle 계약을 재검토 상태로 전환한다. 구조화 변경 뒤에는
  `candidate_sync_required`가 설정되므로, 모델은 `documentation_package_status`의 lifecycle snapshot을
  candidate Markdown에 반영하고 validate/preview를 다시 수행해야 한다. 이 경로는 `.mvpmcp/`를 직접 쓰지 않는다.
- 기존 spec_id Tool 10개는 모두 직접 Run-scoped 대체가 생겼고 canonical 12개 E2E와 Tool 부재 검증을
  통과한 뒤 이번 breaking release에서 **제거 완료**됐다.

### 2026-09-13 breaking cutover 검증

| 검증 | 결과 |
|---|---|
| Composition Root MCP E2E | lifecycle 5개 기록 → candidate sync → validate → preview, `generate_only`의 `.mvpmcp/` 무반영 확인 |
| 공개 Tool 가드레일 | canonical 12개 정확 일치, 구형 10개 미등록 확인 |
| 정적 품질 게이트 | `ruff check src tests`, `black --check src tests`, `mypy --no-incremental src` 통과 — 67 source files |
| 전체 회귀 | `pytest -q --basetemp .pytest-tmp\\legacy-tool-removal-full-20260913 tests` 통과 — 65 passed |

사용자 재확인(2026-09-13): `.venv-exec` 환경에서 Ruff·Black·mypy·전체 pytest를 다시 실행했다.
Ruff 통과, Black `80 files would be left unchanged`, mypy `67 source files` 문제 없음, pytest `65 passed`
결과를 사용자가 직접 제공했다 (`확인됨`). 이 문서 수정 뒤에는 애플리케이션 테스트를 다시 실행하지 않는다.

미등록 `start_spec`과 구형 `clarify_intent`·`get_missing_info`·`scope_mvp` adapter 및 전용 질문
체인은 2026-09-13 별도 승인 마일스톤에서 제거했다. Adaptive Wizard 재개가 사용하는
`ScopeMvpUseCase`·`SpecDraft`·`SpecRepository`·`spec://drafts/{spec_id}` Resource는 활성 경로이므로
유지한다. 이후 물리 정리는 별도 감사·승인에서만 검토한다.

### 2026-09-13 client-native 질문 전환 검증

| 검증 | 결과 |
|---|---|
| Native adaptive Run·MCP schema/submit·계층 가드레일 | 19 passed |
| Codex Skill·workflow Prompt 품질 계약 | 6 passed |
| `ruff check src tests` | 통과 |
| `black --check src tests` | 통과 |
| `mypy --no-incremental src` | 통과 — 71 source files |
| `pytest -q --basetemp .pytest-tmp\\native-question-final2-20260913 tests` | 통과 — 67 passed |
| 실제 Codex Desktop `run_id` 재개 | schema 반환 통과 — `INTAKE_OPEN`·`intake_questions`; Default 모드 form 표시 불가 (`확인됨`) |

Web Wizard·URL elicitation/continuation probe·대기형 timeout 경로의 production/통합/현재 문서 참조는
정적 탐색에서 0건이다. Git 작업 트리에는 이전 단계의 사용자 변경도 함께 있으므로 이 전환에 속하지
않는 변경을 되돌리거나 정리하지 않았다.

| 입력 조건 | Markdown 프로파일 | 보조 산출물 |
|---|---|---|
| 일반 Wizard | 핵심 6문서 | 조건에 따라 OpenAPI·HTML |
| 명시적 PROTOTYPE_4 + 저위험 확인 4개 | 핵심 4문서 | HTML 선택과 독립 |
| 인증·개인정보·결제·위험 | 핵심 6 + SECURITY_PRIVACY | API/HTML 선택 가능 |
| 기존 데이터 변경 | 핵심 6 + MIGRATION_PLAN | API/HTML 선택 가능 |
| 보안 + 데이터 변경 | 핵심 6 + 조건부 2 | API/HTML 선택 가능 |

후보는 `<mvp_mcp_output_dir>/runs/<run_id>/candidate/`, preview snapshot은
`<mvp_mcp_output_dir>/previews/<run_id>/<preview_id>/`에 남는다. 실제 반영은
`<project_root>/.mvpmcp/` 안에서만 일어난다. `README.md`와 `AGENTS.md`는 패키지 루트,
핵심·조건부 문서는 `docs/`, OpenAPI는 `api/`, 선택 HTML은 `prototype/index.html`에 둔다.
`.manifest.json`은 관리 파일 hash·프로토타입 원본 계약 hash·적용 정보를 보유한다.

## 구현된 안전·품질 계약

- 가이드의 기본 6문서, 조건부 2문서, 4문서용 DELIVERY_CHECKLIST 전체 목차를 코드 계약으로 관리한다.
- BIZ/FR/NFR/DATA/SEC, AC, TASK, TEST, REL 식별자와 참조를 검증한다.
- 저위험 빈값·`계획 미정`은 보수적 권장값으로 해소하고 결정 출처·근거·신뢰도를 기록한다.
- 설계 결정은 `open`/`resolved`를 구분하며 실제 open 항목만 preview를 차단한다.
- 2차 native 답변 제출이 `DRAFT_READY`를 반환하면 별도 채팅 확인 없이 같은 흐름에서 후속 Tool을 진행한다.
- Adaptive Run은 SQLite에 `request_key`, version, 제출 snapshot hash, 최초 요청의
  `requested_write_policy`, 불변 `write_policy`, 2차 질문, `spec_id`, 서버 발급 candidate root, Run 소유
  requirements·architecture·delivery·verification·release lifecycle, candidate revision, preview binding,
  적용 이력을 보관한다. 동일 request_key·동일 2차 질문은 새 질문 UI·새 초안을 만들지 않는다.
- `DRAFT_READY`의 기존 초안은 현재 InMemorySpecRepository에 남는다. 서버 재시작으로 사라졌다면,
  같은 2차 질문의 `phase=design` 재호출이 결정적 `spec_id`로 scoped draft를 재수화한다.
- 서버는 Web Form·`file://`·loopback HTTP·URL elicitation을 사용하지 않는다. 질문 UI는 각 MCP
  클라이언트가 소유하고 서버는 schema·답변·Run 상태를 소유한다.
- Run-scoped 후보 요구사항은 stable ID upsert로 개정하고 lifecycle revision을 올리며 설계·TASK·TEST·릴리스를
  안전하게 무효화한다. 구조화 변경 뒤 모델은 candidate Markdown을 갱신하고 validate/preview를 다시 해야 한다.
- TEST PASS와 RELEASED는 실행자·시각·증거 등 필수 근거 없이는 생성할 수 없다.
- preview는 CREATE/UPDATE_MANAGED/KEEP_VALID/CONFLICT_UNMANAGED와 STALE을 보고한다.
- unmanaged 파일을 덮어쓰지 않고, preview 뒤 파일·manifest 변경을 SHA-256으로 재검사한다.
- 적용은 임시 staging·backup·교체·실패 복구 순서로 수행하며 stale 파일을 자동 삭제하지 않는다.
- 후보 reader는 서버 발급 root 밖 경로, symlink/reparse, 비 UTF-8, 1 MiB 초과 파일, 지원하지 않는
  경로를 거부한다. candidate revision·Run version·preview manifest hash가 달라지면 재검증한다.
- `safe_auto_apply`는 preview 중 충돌이 없고 manifest가 관리하거나 새 파일인 경우에만 내부 Apply
  UseCase를 호출한다. 충돌이면 `.mvpmcp`를 바꾸지 않고 `CONFLICTED`와 후보·preview를 남긴다.
- HTML은 단일 파일, CSP `connect-src 'none'`, mock-only, NON-SSOT이며 실제 Chromium에서 검증한다.
- 과거 2문서·소문자 6문서 경로는 이미 제거됐다. 이 문서 아래에 남은 호환 Tool 유지 표현은
  breaking cutover 이전의 이력이며, 현재 공개 계약은 상단의 canonical 12개와 구형 Tool 10개 제거 상태를 따른다.

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

### 2026-09-11 2단계 Wizard 단계 0·1 검증

| 검증 | 결과 |
|---|---|
| URL elicitation 상태·SQLite·loopback form·notification 테스트 | 통과 |
| MCP protocol E2E | 통과 — completion notification 뒤 수동 retry가 `continuation_received`를 반환 |
| `ruff check src tests scripts` | 통과 |
| `black --check src tests scripts` | 통과 (사용자 Black cache 읽기 권한 경고만 있음) |
| `mypy src` | 통과 — 68 source files |
| `pytest -q --basetemp .pytest-tmp-quality-20260911` | 62 passed, 2 xfailed |
| `scripts/run_mcp_evaluations.py` | 10/10 passed |
| 실제 Codex 자동 retry | 실패 — Desktop에서 URL elicitation이 Tool 오류·링크로 표시됐고, 브라우저 제출 후 원래 Tool 호출이 자동 재시도되지 않음 |

따라서 MCP URL elicitation을 제품 UX 계약으로 쓰지 않는다. 서버 worker는 Codex 모델을 독립적으로
재개할 수 없으므로 모델 API·인증·감사 범위를 새로 승인하지 않는 한 기본 해법이 아니다. 현재 구현은
살아 있는 blocking Tool 호출을 1·2차 form 제출까지 유지하는 방식으로 같은 모델 턴을 이어간다.

### 2026-09-12 blocking Adaptive Wizard 구현·검증

| 검증 | 결과 |
|---|---|
| 1·2차 Run 상태·SQLite·중복 request/design·재수화 | 통과 |
| loopback form GET/POST·CSRF token·CSP | 통과 |
| MCP memory E2E | 통과 — 1차 제출 → 2차 제출 → `DRAFT_READY + spec_id`, 별도 채팅 재입력 없음 |
| `ruff check src tests scripts` | 통과 |
| `black --check src tests scripts` | 통과 (사용자 Black cache 읽기 권한 경고만 있음) |
| `mypy src` | 통과 — 76 source files |
| `pytest -q --basetemp .pytest-tmp-final-adaptive` | 통과 — 68 passed, 2 xfailed |
| `scripts/run_mcp_evaluations.py` | 통과 — 10/10 |

### 2026-09-12 candidate package·write_policy 구현

| 검증 | 결과 |
|---|---|
| candidate validate/preview/apply·SQLite 재시작·충돌 보존·정책 거부 | 통과 — generate_only, manual_apply, safe_auto_apply, stale revision 회귀 포함 |
| MCP memory E2E | 통과 — package status → validate → preview 체인을 직접 검증 |
| `ruff check src tests scripts` / `black --check src tests scripts` / `mypy src` | 모두 통과 — 84 source files |
| `pytest -q --basetemp .pytest-tmp-final-candidate2` | 통과 — 76 passed, 2 xfailed |
| `scripts/run_mcp_evaluations.py` | 통과 — 10/10 |

### 2026-09-12 Codex Desktop 실제 2단계 Wizard·자동 반영 수용 테스트

| 검증 | 결과 | 근거 신뢰도 |
|---|---|---|
| 1차 blocking Wizard 대기 | 실패 — `tools/call`이 약 300초 뒤 timeout | 확인됨 |
| timeout 뒤 제출값 보존·복구 | 통과 — 동일 `request_key` 재호출이 `INTAKE_SUBMITTED` snapshot을 반환 | 확인됨 |
| timeout 뒤 채팅 없는 자동 재개 | 실패 — 사용자의 `제출함` 메시지 뒤 재호출되어 진행 | 확인됨 |
| 2차 질문 생성 | 최종 통과, 단 `title/type` 및 `single_select` 형식으로 두 번 거부된 뒤 `label/kind=select|multiselect`로 성공 | 확인됨 |
| 후보 검증 | 통과 — `MVP_6_FULL_RISK`, 9개 파일, 오류·경고 없음 | 확인됨 |
| `safe_auto_apply` | 통과 — 최초 요청에서 `.mvpmcp/` 자동 반영 권한을 명시한 경우, 기존 관리 문서 9개를 충돌 없이 `UPDATE_MANAGED` | 확인됨 |

이 수용 테스트는 문서 구조·추적성 계약의 통과를 확인한 것이며, 산출물 본문의 실무 품질 평가는 별도
루브릭·대표 fixture 단계에서 수행해야 한다.

### 2026-09-12 후속 Harness·정책 불변성 검증

| 검증 | 결과 | 근거 신뢰도 |
|---|---|---|
| 2차 질문 구조화·Android 모바일 분류 | 통과 — typed `design_questions`, Android 우선 분류 회귀 포함 | 확인됨 |
| Architecture 기술 스택·디렉터리 구조 계약 | 통과 — 5열 근거 상태 표·라벨된 트리·SSOT 참조 검증 | 확인됨 |
| 산출물 품질 Harness | 통과 — 7개 루브릭·5개 대표 evaluation fixture·Skill 자체 점검 | 확인됨 |
| Tool inventory 감사 | 통과 — canonical 6개·호환 10개·보조 2개를 가드레일로 고정, 삭제 보류 | 확인됨 |
| `generate_only` 정책 불변성 | 통과 — 최초 명시 정책 결속, 동일 key 정책 변경·2차 `document_output_mode` 거부 | 확인됨 |
| 전체 품질 게이트 | `ruff`, `black --check`, `mypy` 통과; `pytest -q --basetemp .pytest-tmp-policy-full` 94 passed, 2 xfailed | 확인됨 |

## 운영 시 주의점

- candidate 본문과 Run revision·preview binding은 디스크/SQLite에 남는다. exporter의 실제 apply payload는
  프로세스 메모리이므로, 서버 재시작 뒤 `manual_apply` 전에는 같은 candidate revision으로 새 preview를
  만들어 binding을 복구해야 한다.
- 실행 중이던 기존 MCP 프로세스가 원래 `.venv` 실행 파일을 잠가, 이번 작업은 `.venv-exec` 격리
  환경에서 검증했다. 기존 서버를 종료한 다음 표준 `.venv`를 다시 `uv sync --group dev`하면 된다.
- 2026-09-10에는 개인 Codex 플러그인 `0.2.0+codex.20260910103953`의 설치 Skill과
  `integrations/codex/SKILL.md` 해시 일치를 기록했으나, 이는 현재 설치 상태의 보증이 아니다.
- `scripts/sync_codex_plugin.py`로 배포 원본을 동기화하고 설치 캐시는 직접 수정하지 않는다.
- Codex 연동 Skill의 조건부 보안 문서 안내는 생성 계약과 같은
  `SECURITY_PRIVACY.md`로 정정됐다. 설치 Skill은 다음 플러그인 릴리스에서 원본과 함께
  동기화·재설치해야 한다 (`미확인`).
- 실제 수용 테스트의 실행 기록은 설치 캐시의 `mvpmcp` Skill이 오래된 "명시적 승인 뒤 반영" 문구를
  읽은 사실을 보인다. 소스 `integrations/codex/SKILL.md`와 설치된 플러그인의 재동기화 여부는
  **충돌** 상태이며, 다음 플러그인 배포·재설치에서 확인해야 한다.
- 이번 `write_policy` 불변성 지침도 저장소 원본 Skill에만 반영했다. 설치된 플러그인이 이 정책 입력을
  보내는지는 아직 **미확인**이며, 공식 동기화·재설치 뒤 별도 실클라이언트 수용 테스트가 필요하다.
- 이번 사용자 수용 확인은 새 Codex 작업의 최종 고도화 산출물이 정상 생성된 범위다. Claude·Gemini
  등 다른 MCP 클라이언트의 동일 흐름은 이번 마일스톤에서 실사용 검증하지 않았다 (`미확인`).
- 실제 대상 프로젝트 코드 구현·테스트 실행·배포는 이 서버의 책임이 아니다.
- Adaptive `write_policy`는 Run에 고정된다. `generate_only`는 후보·preview만 제공하고,
  `safe_auto_apply`는 충돌 없는 preview에서 자동 반영하며, `manual_apply`는 별도 요청에만
  `documentation_apply_package`를 허용한다.

## 다음 마일스톤 — 별도 승인 전에는 시작하지 않음

가장 가까운 후보는 **디자인 산출물 품질 강화**다. 이는 2026-09-16 읽기 전용 감사에서 확인된 생성 결과의 품질 한계를 해결하는 별도 구현 마일스톤이며, 아직 승인되지 않았다. 승인되면 다음 순서로만 진행한다.

1. `MVPDESIGN.md` 렌더러에 결정 상태·근거·완전한 Light/Dark/고대비·상태 팔레트와 화면별 수용 기준을 채운다.
2. `design-tokens.json`의 역할 토큰을 완결하고, HTML renderer가 raw Hex·인라인 style 없이 토큰만 사용하도록 한다.
3. compact·medium·expanded 레이아웃, `:focus-visible`, 오류 대상 연결, 빈·삭제 확인 상태와 프로토타입 핵심 상호작용을 검증한다.
4. 생성 패키지의 문서 품질 계약(API·DB·TASK·TEST·운영 실행 기준)을 강화하고, 표본 패키지를 변경하지 않는 회귀 테스트를 추가한다.

허용 범위는 서버의 디자인 artifact renderer·도메인 계약·테스트·관련 클라이언트 지침 및 현재 상태 문서다. 사용자 소유 `design/`, `recordmvp/`, 기존 사용자 `.mvpmcp/`, 플러그인 동기화·재설치, 제품 앱 구현·배포는 포함하지 않는다.

### 병렬 후보 — 다른 MCP 클라이언트 수용 범위

`start_spec`과 구형 채팅형 adapter 체인의 물리 정리는 2026-09-13에 완료됐다. 질문 UI 제품 경계는
**서버 schema + 각 클라이언트의 기존 native 질문 Tool**로 결정됐다. Codex Plan의 실제 문서 저장 수용은
완료됐다 (`확인됨`). 다음 후보는 Claude·Gemini·Antigravity의 실제 수용 확인과 Codex의 혼동 가능한
Plan UI 상태 표시에 대한 읽기 전용 범위 판단이다. 명시적 승인 전에는 시작하지 않는다.

서버 모델 API worker, timeout 자동 재개, 대규모 파일 이동, 기존 사용자 `.mvpmcp` 변경, 플러그인 동기화·재설치,
프로토타입 시각 디자인 변경, App Server 호스트 클라이언트 구현은 별도 요청과 승인 없이는 시작하지 않는다.

## 다음 채팅 시작 문구

```text
먼저 AGENTS.md, README.md, HANDOFF.md, progress/PROGRESS.md,
progress/IMPROVEMENT_ROADMAP.md, progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md,
progress/FINAL_SKILL_HARNESS_MCP_REFACTORING_PLAN.md, progress/ROOT_ARTIFACT_AUDIT.md를 읽어줘.

`HANDOFF.md`의 2026-09-16 생성 패키지 품질·시각 감사를 기준으로, 디자인 산출물 품질 강화의 구현 계획을 작성해줘. 범위는 MVPDESIGN renderer, design token contract, HTML renderer, 관련 테스트·클라이언트 지침뿐이다. 우선 완성형 디자인 결정 필드와 Light/Dark/고대비·상태 토큰, raw Hex·인라인 style 제거, 375/768/1440px 반응형, 포커스·오류 대상·빈/삭제 상태·핵심 목업 상호작용의 검증 방안을 제시해줘.

서버 모델 API worker, timeout 자동 재개, 대규모 파일 이동, 기존 사용자 .mvpmcp 변경, 플러그인 동기화·재설치, 사용자 소유 design/·recordmvp/ 변경, 제품 앱 구현·배포, App Server 호스트 클라이언트 구현은 시작하지 마. 코드 수정은 계획을 확인받은 뒤에만 시작해줘.
```
