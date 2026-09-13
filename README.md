# mvp-mcp — Human–AI 협업 문서 패키지 생성기

사용자의 제품 아이디어를 클라이언트 native 구조화 질문으로 구체화하고, 모델이 작성한 Run 전용 후보 문서를 검증·미리보기한
뒤 불변 `write_policy`에 따라 구현·테스트·운영용 저장소 문서를 `.mvpmcp/`에 안전하게 반영하는 MCP
서버다.

이 저장소의 문서 계약은
`HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.md`를 유일한 기준으로 삼는다. 과거 6문서
계약이나 별도 보조 계획서는 생성 규칙의 근거로 사용하지 않는다.

```text
아이디어
→ 1차 적응형 질문 schema → 클라이언트 native 질문 UI
→ 요청·저장소·1차 답변 분석
→ 2차 맞춤 질문 schema → 클라이언트 native 질문 UI
→ Run-scoped requirements → architecture → delivery 계약
→ <output>/runs/<run_id>/candidate/ 후보 저작
→ candidate revision 검증
→ 변경 미리보기
→ generate_only | safe_auto_apply | manual_apply 정책 처리
→ <project_root>/.mvpmcp/ 원자적 적용(허용된 경우만)
```

## 핵심 원칙

- 사람과 AI의 지속 협업을 기본 전제로 하며 협업 여부는 묻지 않는다.
- `FR/AC → TASK → TEST` 연결과 실제 실행 증거를 검증한다.
- 테스트를 실행하지 않았으면 `NOT RUN`으로 기록하며 임의로 `PASS` 처리하지 않는다.
- 후보 문서는 2차 제출 뒤 별도 생성 승인 없이 즉시 작성한다.
- `.mvpmcp/` 반영은 1차 질문에서 고정한 `write_policy`로만 결정한다. `safe_auto_apply`는
  unmanaged 충돌이 없을 때만 자동 반영하고, `manual_apply`만 별도 반영 요청을 기다린다.
- 관리 이력이 없는 기존 파일은 덮어쓰지 않고 충돌로 처리한다.
- 선택한 경우에만 `.mvpmcp/prototype/index.html`을 생성한다. 프로토타입은 설명용이며
  Markdown 문서가 SSOT다.

## 설치와 실행

요구사항은 Python 3.11 이상과 [uv](https://docs.astral.sh/uv/)다.

```powershell
uv sync --group dev
uv run mvp-mcp
```

Claude Desktop 등 stdio MCP 클라이언트에는 다음과 같이 등록한다.

```json
{
  "mcpServers": {
    "mvp": {
      "command": "uv",
      "args": ["--directory", "C:/path/to/mvp-mcp", "run", "mvp-mcp"]
    }
  }
}
```

## 권장 워크플로

1. `documentation_start_adaptive_wizard(phase="intake")`에 아이디어, 절대 프로젝트 루트와 작업별
   `request_key`를 전달한다. Tool은 1차 `questions` schema를 즉시 반환한다.
2. 클라이언트는 반환된 질문을 자신의 native 질문 UI로 표시하고, 확정 답을 같은 `run_id`와
   `phase="intake"`의 `documentation_submit_adaptive_wizard_answers`에 한 번 제출한다. Codex는
   `request_user_input`, Claude Code는 `AskUserQuestion`, Gemini CLI는 `ask_user`를 사용한다. 사용자가
   채팅에 `제출했음`을 다시 입력하지 않는다.
3. 1차 답변과 저장소 근거를 분석해 같은 `run_id`의 `phase="design"` 호출에 3~7개 맞춤 질문을
   제공하고, 같은 native UI → 제출 흐름으로 2차 답변을 저장한다. 2차 제출의 `DRAFT_READY`와
   `candidate_root`를 받으면 최초 요청·두 단계 답변·저장소 근거를
   바탕으로 먼저 `documentation_update_candidate_requirements` →
   `documentation_update_candidate_architecture` → `documentation_update_candidate_delivery`를 호출한다.
   각 호출은 최신 `expected_run_version`을 사용하며, 반환된 `candidate_lifecycle`을 바탕으로 그 경로 안에
   UTF-8 후보 문서를 작성한다. 이 단계에서 추가 채팅 질문이나 생성 승인을 요구하지 않는다.
4. `documentation_package_status(run_id)`로 구조화 `candidate_lifecycle`, `candidate_sync_required`,
   서버가 계산한 `current_candidate_revision`, 최신 `run_version`을 읽는다. 구조화 계약을 바꾼 뒤에는
   candidate Markdown을 갱신하지 않은 상태로 검증할 수 없다.
5. `documentation_validate_package(run_id, run_version, candidate_revision)`로 문서 프로파일, 전체
   계약 목차, `FR/AC → TASK → TEST → REL` 최소 추적성, 경로·UTF-8 규칙을 검증한다.
6. 반환된 version으로 `documentation_preview_package`를 호출해 CREATE/UPDATE/KEEP/CONFLICT/STALE을
   만든다. `safe_auto_apply`는 충돌이 없을 때 이 단계에서만 내부적으로 반영한다.
7. `generate_only`는 candidate와 preview를 결과로 제공하고, `manual_apply`는 별도 반영 요청이 있을
   때만 `documentation_apply_package`를 호출한다. `documentation_package_status`는 재시작 뒤에도
   candidate revision·preview binding·manifest 상태를 보여준다.

`documentation_start`, `answer_question`, `documentation_validate`, `documentation_preview`,
`documentation_apply`, `documentation_register_requirements`, `documentation_register_architecture`,
`documentation_register_delivery`, `documentation_record_test_run`, `documentation_record_release`은 기존
spec_id 경로의 Tool이며 이번 breaking release에서 **제거 완료**됐다. 구형 이름은 MCP에서 찾을 수 없으므로,
새 작업은 adaptive 시작·답변 제출·Run-scoped candidate lifecycle·package Tool만 사용한다.
`documentation_wizard_run_status`는 native 질문 단계가 중단된 뒤 Run 상태를 읽기 전용으로 복구한다.

## 공개 Tool 분류

새 문서 생성의 canonical Tool은 `documentation_start_adaptive_wizard`,
`documentation_submit_adaptive_wizard_answers`, `documentation_wizard_run_status`,
`documentation_update_candidate_requirements`, `documentation_update_candidate_architecture`,
`documentation_update_candidate_delivery`, `documentation_record_candidate_test_run`,
`documentation_record_candidate_release`, `documentation_validate_package`,
`documentation_preview_package`, `documentation_apply_package`, `documentation_package_status` 12개다.
기존 spec_id Tool 10개는 직접 대체된 뒤 이번 breaking release에서 **제거 완료**됐다.
전체 inventory와 migration 근거는
[`progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md`](progress/MCP_PUBLIC_TOOL_TRANSITION_AUDIT.md)를 참고한다.

## 2단계 적응형 Wizard (현재 기본)

- canonical 시작 호출은 `write_policy`를 함께 보내며, 사용자가 `generate_only`를 요청했거나 자동 반영을
  명시적으로 허용하지 않으면 `generate_only`로 고정한다. 이 경우 1차 질문 schema는 파일 반영 정책을 다시
  묻지 않는다. `write_policy`를 생략한 호출만 1차 질문에서 정책을 선택한다. 이후 2차 질문은 정책을 다시 묻지 않는다.
- 1차 질문 schema는 작업 유형, 산출물 유형, 대상 맥락, 문제·목표, 영향 사용자, MVP 범위, 성공 기준,
  제약·위험, 기술 스택 선호를 묻고, 선택한 작업 유형에 맞는 3개 세부 문항만 표시한다.
- 2차 질문 schema는 최초 요청·1차 답변·저장소 근거를 바탕으로 모델이 만든 3~7개 질문만 표시한다. 1차
  문항을 반복하지 않는다.
- Run은 SQLite에 `request_key`, 제출 snapshot hash, version, 불변 `write_policy`, `spec_id`, 서버 발급
  `candidate_root`, Run-scoped 요구사항·설계·전달·검증·릴리스 lifecycle, candidate 검증 revision,
  preview hash와 적용 이력을 저장한다. 동일 요청·같은 2차 질문의 재호출은 새 설문이나 새 초안을 만들지
  않는다.
- localhost HTTP form·`file://` URL·URL elicitation을 제품 경로로 사용하지 않는다. 질문 UI는 각
  MCP 클라이언트가 소유하고, 서버는 질문 schema와 Run·답변만 영속한다.
- 2차 제출 결과는 비어 있는 Run 전용 candidate root를 발급한다. 모델은 그 안에서만 문서를 작성하며,
  MCP는 본문을 대신 작성하지 않고 deterministic 검증·preview·충돌 보존·원자 반영을 맡는다.
- `documentation_preview_package`는 `safe_auto_apply`일 때 실제 반영까지 수행할 수 있으므로
  destructive Tool로 표시된다. 다른 정책에서는 대상 프로젝트를 바꾸지 않는다.

### Run-scoped candidate lifecycle

- 구조화 계약 변경 Tool은 `run_id`와 최신 `expected_run_version`을 받는다. 오래된 version은 거절하며,
  테스트·릴리스 기록은 `idempotency_key`로 같은 재시도를 안전하게 반환한다.
- 요구사항 변경은 설계·전달·검증·릴리스를, 설계 변경은 전달·검증·릴리스를, 전달 변경은 검증·릴리스를
  재검토 상태로 만든다. TEST·RELEASED 기록은 append-only이며 RELEASED에는 현재 TEST 계약 전체의 PASS
  증거가 필요하다.
- 구조화 변경은 기존 candidate validate/preview binding을 지우고 `candidate_sync_required`를 설정한다.
  모델은 `documentation_package_status`가 반환한 lifecycle을 candidate Markdown에 반영한 뒤 다시
  validate/preview해야 한다. 이 과정은 `.mvpmcp/`를 쓰지 않는다.

### 클라이언트 질문 대기와 자동 반영 권한

- 질문 대기는 MCP Tool 호출이 아니라 클라이언트 native 질문 UI가 소유한다. 따라서 서버가 브라우저
  제출을 기다리며 Tool timeout과 결합하지 않는다. 사용자가 몇 분 또는 수십 분 뒤 답해도 클라이언트가
  답을 반환하면 같은 모델 흐름에서 `documentation_submit_adaptive_wizard_answers`로 즉시 이어간다.
  앱·클라이언트 자체의 세션 만료·재개 보장은 각 클라이언트의 기능 범위이며, 서버 모델 worker나
  timeout 뒤 자동 재개 기능은 도입하지 않는다.
- Codex에서 `safe_auto_apply`를 사용하려면 최초 자연어 요청에도 “`.mvpmcp/` 자동 반영을 허용한다”는
  명시적 권한을 포함한다. Wizard의 정책 선택만으로는 destructive preview Tool의 플랫폼 안전 심사를
  통과한다고 보장할 수 없다.

## 후보·생성 구조

```text
<mvp_mcp_output_dir>/runs/<run_id>/candidate/   # 모델이 실제로 작성하는 후보
<mvp_mcp_output_dir>/previews/<run_id>/<id>/    # exporter가 보존하는 preview snapshot
<project_root>/.mvpmcp/                         # write_policy가 허용할 때만 반영
```

```text
<project_root>/.mvpmcp/
├── AGENTS.md
├── README.md
├── docs/
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TEST_PLAN.md
│   ├── RELEASE_RUNBOOK.md
│   ├── SECURITY_PRIVACY.md     # 위험 신호가 있을 때
│   └── MIGRATION_PLAN.md       # 기존 데이터 변경 시
├── api/
│   └── openapi.yaml            # HTTP API 제공·변경 시
├── prototype/
│   └── index.html              # 설문에서 요청한 경우
└── .manifest.json              # 관리 파일 해시·생성 근거
```

일반 adaptive Wizard는 핵심 6문서를 생성한다. `PROTOTYPE_4`와 네 가지 저위험
확인 진술을 충족한 1인·로컬 프로토타입만 세 실행 문서를 `DELIVERY_CHECKLIST.md`로 합쳐 핵심
4문서를 생성한다. 위험 또는 운영 조건이 생기거나 확인 진술이 빠지면 자동으로 6문서로 승격한다.
`SECURITY_PRIVACY.md`와 `MIGRATION_PLAN.md`는 조건부 문서이므로 일반 프로젝트는 6개, 위험과
데이터 변경이 모두 있는 프로젝트는 8개 Markdown 문서가 된다.
`openapi.yaml`과 HTML은 문서 수에 포함하지 않는 보조 산출물이다.

각 Markdown 문서는 가이드의 전체 목적·목차를 유지한다. 해당 없는 절은 삭제하지 않고
근거가 있는 `해당 없음` 또는 후속 계획을 남겨 구조 비교와 인수인계가 가능하게 한다.
`docs/ARCHITECTURE.md`는 기술 선택의 근거 상태를 포함한 `## 기술 스택` 표와
`[KEEP/NEW/MODIFY/REMOVE/OPTIONAL]` 라벨을 쓴 `## 디렉터리 구조`를 기술 SSOT로 둔다.

## HTML 프로토타입 계약

- 외부 CDN·폰트·네트워크 요청이 없는 단일 HTML이다.
- 키보드 포커스와 축소 화면을 지원한다.
- 데이터는 샘플이며 상태는 브라우저 메모리에만 존재한다.
- `DesignContract`에 기록된 사용자 흐름과 오류 상태가 있으면 정상 단계·예외 복구 안내를 함께 표시한다.
- 탭 전환과 화면별 `ScreenSpec.states` Mock 선택은 키보드로 조작하며, 선택 누락·성공 상태를 보조기술에 구분해 알린다.
- 문서로 확정되지 않은 상호작용은 프로토타입이 요구사항을 새로 만들지 않는다.
- 화면 정의가 없으면 문서 생성 워크플로를 설명하는 기본 시뮬레이터를 만든다.

## 안전한 적용

미리보기는 각 파일을 `CREATE`, `UPDATE`, `KEEP`, `CONFLICT`, `STALE`로 분류한다. 적용 시
미리보기 이후 대상 해시가 바뀌지 않았는지 다시 확인하고, 임시 경로에 쓴 뒤 교체한다. 실패하면
이미 변경한 파일을 복구한다. 이전 manifest가 관리하던 오래된 파일은 자동 삭제하지 않고
`STALE`로 보고한다. candidate 본문·run version·preview manifest hash 중 하나라도 달라지면 다시
검증·미리보기를 해야 하며, unmanaged 사용자 파일은 어떤 정책에서도 덮어쓰지 않는다.

## 개발 검증

```powershell
uv run ruff check
uv run black --check src tests
uv run mypy src
uv run pytest -q
```

구조와 도구 목록은 테스트가 강제한다. 의존성 조립은 `src/mvp_mcp/main.py::build()`에만 두고,
도메인 계층에는 MCP·저장소 드라이버·렌더러 의존성을 넣지 않는다.

개인 Codex 플러그인은 `scripts/sync_codex_plugin.py`로 저장소의 `integrations/codex/SKILL.md`와
실행 파일 경로를 플러그인 원본에 동기화한 뒤 공식 cachebuster·validation·재설치 흐름을 사용한다.
설치 캐시는 직접 수정하지 않는다.
