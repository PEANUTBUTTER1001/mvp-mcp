# mvp-mcp — Human–AI 협업 문서 패키지 생성기

사용자의 제품 아이디어를 설문으로 구체화하고, 사람이 승인할 수 있는 변경 미리보기와 함께
구현·테스트·운영에 필요한 저장소 문서를 `.mvpmcp/`에 생성하는 MCP 서버다.

이 저장소의 문서 계약은
`HUMAN_AI_REPOSITORY_DOCUMENTATION_GUIDE.md`를 유일한 기준으로 삼는다. 과거 6문서
계약이나 별도 보조 계획서는 생성 규칙의 근거로 사용하지 않는다.

```text
아이디어
→ 통합 설문
→ 요구사항·설계·작업·테스트 ID 등록
→ 문서 품질 검증
→ 변경 미리보기
→ 사용자 승인
→ <project_root>/.mvpmcp/ 원자적 적용
```

## 핵심 원칙

- 사람과 AI의 지속 협업을 기본 전제로 하며 협업 여부는 묻지 않는다.
- `FR/AC → TASK → TEST` 연결과 실제 실행 증거를 검증한다.
- 테스트를 실행하지 않았으면 `NOT RUN`으로 기록하며 임의로 `PASS` 처리하지 않는다.
- 파일을 쓰기 전에 생성·수정·유지·충돌·오래된 파일을 모두 미리 보여준다.
- 사용자가 명시적으로 승인해야 `.mvpmcp/`에 반영한다.
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

1. `documentation_collect_intake`로 아이디어와 프로젝트 루트를 전달하고 통합 설문을 완료한다.
2. `documentation_register_requirements`로 BIZ/FR/NFR/DATA/SEC 요구사항과 수용 기준을 등록한다.
3. `documentation_register_architecture`로 화면·흐름·데이터·인터페이스·규칙·오류 설계를 등록한다.
4. `documentation_register_delivery`로 요구사항에 연결된 TASK와 TEST를 등록한다.
5. 필요한 경우 `documentation_record_test_run`과 `documentation_record_release`에 실제 근거를
   append-only로 기록한다.
6. `documentation_validate`가 구조·추적성·품질 게이트를 통과하는지 확인한다.
7. `documentation_preview`에서 파일별 변경과 충돌을 검토한다.
8. 사용자에게 명시적 승인을 받은 뒤에만 `documentation_apply`를 호출한다.

`documentation_start`는 자동 설문을 사용하지 않는 클라이언트의 세션 시작용이다.
`ask_web_question`과 `ask_elicitation_question`은 범용 보충 질문 도구다.

## 통합 설문

| 영역 | 입력 방식 | 판단 결과 |
|---|---|---|
| 작업 성격 | 신규/기존 변경 라디오 | 기존 시스템 변경·마이그레이션 범위 |
| 사용·배포 | 로컬 실험/실사용 배포 라디오 | 운영 문서 깊이 |
| 사용자 화면 | 웹·모바일·관리자 등 복수 선택 | 화면·접근성 설계 |
| HTTP API | 제공/변경/없음 라디오 | `openapi.yaml` 생성 여부 |
| 데이터 저장 | 필요/불필요/미정 라디오 | 데이터 설계 질문 표시 |
| 기존 데이터 변경 | 있음/없음/미정 라디오 | `MIGRATION_PLAN.md` 생성 여부 |
| 인증·권한 | 로그인·세션·역할·복구·없음·미정 복수 선택 | 보안 문서·결정 게이트 |
| 개인정보 | 유형·없음·미정 복수 선택 | 개인정보 수명주기·보안 문서 |
| 결제·고가치 자산 | 있음/없음/미정 라디오 | 고위험 통제 |
| 기타 위험 | 위치·업로드·외부 입력·비밀정보·없음·미정 복수 선택 | 위협·검증 범위 |
| 운영 복구 | 필요/불필요/미정 라디오 | 백업·롤백·장애 대응 |
| HTML 프로토타입 | 필요/불필요 라디오 | 설명용 단일 HTML 생성 |

`없음`과 `미정`은 실제 항목과 함께 선택할 수 없다. 선택 상세가 비었거나 되돌릴 수 있는
저위험 항목이 `미정`이면 프로젝트 유형별 보수적 권장값으로 해소하고 값·근거·출처·신뢰도를
문서에 기록한다. 실제 고위험 미해결 결정만 Open Decision으로 남아 preview를 차단한다.

Wizard Tool이 `spec_id`를 반환한 시점에는 제출이 이미 완료된 것이다. 클라이언트는 사용자에게
`제출함` 메시지를 요구하지 않고 같은 턴에서 요구사항·설계·전달 계약·검증·preview까지 이어간다.

## 생성 구조

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

일반 Wizard는 핵심 6문서를 생성한다. `documentation_start`에서 `PROTOTYPE_4`와 네 가지 저위험
확인 진술을 명시한 1인·로컬 프로토타입만 세 실행 문서를 `DELIVERY_CHECKLIST.md`로 합쳐 핵심
4문서를 생성한다. 위험 또는 운영 조건이 생기거나 확인 진술이 빠지면 자동으로 6문서로 승격한다.
`SECURITY_PRIVACY.md`와 `MIGRATION_PLAN.md`는 조건부 문서이므로 일반 프로젝트는 6개, 위험과
데이터 변경이 모두 있는 프로젝트는 8개 Markdown 문서가 된다.
`openapi.yaml`과 HTML은 문서 수에 포함하지 않는 보조 산출물이다.

각 Markdown 문서는 가이드의 전체 목적·목차를 유지한다. 해당 없는 절은 삭제하지 않고
근거가 있는 `해당 없음` 또는 후속 계획을 남겨 구조 비교와 인수인계가 가능하게 한다.

## HTML 프로토타입 계약

- 외부 CDN·폰트·네트워크 요청이 없는 단일 HTML이다.
- 키보드 포커스와 축소 화면을 지원한다.
- 데이터는 샘플이며 상태는 브라우저 메모리에만 존재한다.
- 문서로 확정되지 않은 상호작용은 프로토타입이 요구사항을 새로 만들지 않는다.
- 화면 정의가 없으면 문서 생성 워크플로를 설명하는 기본 시뮬레이터를 만든다.

## 안전한 적용

미리보기는 각 파일을 `CREATE`, `UPDATE`, `KEEP`, `CONFLICT`, `STALE`로 분류한다. 적용 시
미리보기 이후 대상 해시가 바뀌지 않았는지 다시 확인하고, 임시 경로에 쓴 뒤 교체한다. 실패하면
이미 변경한 파일을 복구한다. 이전 manifest가 관리하던 오래된 파일은 자동 삭제하지 않고
`STALE`로 보고한다.

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
