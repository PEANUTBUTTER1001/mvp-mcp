# MCP Server Template — 구조와 사용법 지침

이 템플릿은 **Clean Architecture 기반 MCP 서버의 재사용 가능한 뼈대**입니다.
어떤 MCP 서버든 공통으로 필요한 조립 구조만 남긴 뒤, 바로 실행되는 최소 데모 도메인(`note`)을 얹었습니다.
복사 후 도메인만 교체하면 새 MCP 서버를 만들 수 있습니다.

- **의존성:** `mcp[cli]`, `pydantic`, `pydantic-settings` (무거운 네이티브 의존성 없음).
- **Docker 는 선택사항**입니다 — 서버는 `uv run` 만으로 네이티브 실행됩니다([5. 빠른 시작](#5-빠른-시작)의 Docker 절 참고).

> **핵심 사용법 한 줄:** 이 폴더를 복사 → 이름 6곳 치환 → `domain/note` 를 실제 도메인으로
> 교체 → `main.py` 에서 조립. 나머지 뼈대(설정·예외·보안·CI·테스트 규칙)는 그대로 재사용.

> **AI 에이전트가 코드를 작성한다면 [AGENTS.md](AGENTS.md) 를 먼저 읽히세요.** 절대 규칙·코드
> 위치 지도·도구 추가 레시피·검증 명령을 짧게 담아, 콜드스타트 에이전트가 패턴대로 뽑아내게
> 합니다. 규칙 위반은 실행 가능한 가드레일([9. 실행 가능한 가드레일](#9-실행-가능한-가드레일))이
> 테스트로 잡습니다.

---

## 목차

1. [설계 원칙](#1-설계-원칙)
2. [디렉터리 구조](#2-디렉터리-구조)
3. [계층별 역할](#3-계층별-역할)
4. [데이터 흐름](#4-데이터-흐름-요청-→-응답)
5. [빠른 시작](#5-빠른-시작)
6. [새 MCP로 재사용하기 (6단계 개명)](#6-새-mcp로-재사용하기-6단계-개명)
7. [기능 추가 레시피](#7-기능-추가-레시피)
8. [자주 하는 확장](#8-자주-하는-확장)
9. [실행 가능한 가드레일](#9-실행-가능한-가드레일)
10. [무엇을 지우고 무엇을 남길까](#10-무엇을-지우고-무엇을-남길까)
11. [체크리스트](#11-체크리스트)

---

## 1. 설계 원칙

| 원칙 | 의미 | 코드에서의 강제 |
|---|---|---|
| **의존성 역전** | `Presentation → Domain ← Data`. 도메인은 프레임워크를 모른다. | `test_scaffolding.py` 가 domain의 프레임워크 import를 금지 |
| **Composition Root 단일화** | 모든 와이어링은 `main.py` 한 곳에서만. | `build()` 함수 |
| **얇은 어댑터** | Tool/Resource는 검증 + UseCase 위임 + 문자열화만. 로직 없음. | `presentation/*` |
| **Port로 격리** | 외부 협력자(시계·저장소·API)는 `Protocol` 뒤에. | `domain/note/ports.py`, `repository.py` |
| **구조화된 실패** | 실패를 `PipelineError(stage/reason/hint)` 로 설명 가능하게. | `usecase.py` 의 `_run_stage` |
| **재현성** | 동일 입력 → 동일 산출물. 비결정성(시각)은 주입. | `hashing.py`, `Clock` Port |

이 6가지가 "다시 써먹을 수 있는 뼈대"의 실체입니다. 도메인이 무엇이든 그대로 유지됩니다.

---

## 2. 디렉터리 구조

```
mcptemplates/
├── TEMPLATE.md                     # ← 이 문서 (구조·사용법·빠른 시작 통합)
├── AGENTS.md                       # 코딩 에이전트 작업 규칙
├── ARCHITECTURE_REVIEW.md          # 설계 근거·리팩토링 검토
├── pyproject.toml                  # 의존성·빌드·ruff/black/mypy/pytest 설정
├── Dockerfile                      # [선택] 컨테이너 배포용. 없어도 앱 동작 무관
├── .dockerignore / .gitignore
├── .pre-commit-config.yaml         # [선택] 커밋/푸시 시 게이트 자동 실행
├── .github/workflows/ci.yml        # lint + format + type + test 게이트
├── src/mcp_server/
│   ├── main.py                     # 🟢 Composition Root: build() → FastMCP
│   ├── core/
│   │   ├── config.py               # 🟢 환경변수 설정 (env_prefix="MCPSERVER_")
│   │   ├── exceptions.py           # 🟢 MCPServerError · PipelineError
│   │   ├── logging.py              # 🟢 stderr 전용 로깅 (stdout 은 프로토콜 채널)
│   │   └── security.py             # 🟢 경로 안전·파일명 새니타이즈 (파일 다룰 때만)
│   ├── domain/                     # 🔴 순수 도메인 (프레임워크 무의존)
│   │   └── note/                   #    ← 데모 도메인. 통째로 복사해 교체.
│   │       ├── model.py            #    NoteRequest(입력) · Note(엔티티)
│   │       ├── ports.py            #    Clock 등 외부 협력자 Protocol
│   │       ├── repository.py       #    NoteRepository Protocol
│   │       ├── usecase.py          #    CreateNoteUseCase (_run_stage 오케스트레이션)
│   │       ├── query.py            #    Search/List/Get UseCase (읽기 전용)
│   │       └── hashing.py          #    콘텐츠 해시(재현성)
│   ├── data/                       # 🔴 Port 구현체 (I/O·프레임워크 격리)
│   │   ├── system_clock.py         #    SystemClock (Clock 구현)
│   │   └── note/repository_impl.py #    InMemoryNoteRepository (교체 대상)
│   └── presentation/               # 🟡 MCP 어댑터 (등록 패턴 재사용)
│       ├── _safe.py                #    @safe_tool — 어댑터 실패 처리 일원화
│       ├── tools/                  #    register_*_tool(mcp, use_case)
│       ├── resources/              #    register_resources(mcp, ...)
│       └── prompts/                #    register_prompts(mcp)
└── tests/
    ├── test_scaffolding.py         # 🟢 서버 부팅·도메인 무의존 규칙 (유지)
    ├── test_guardrails.py          # 🟢 계층 경계(import-linter)·EXPECTED_TOOLS (유지)
    ├── test_adapters.py            # 🟢 모든 Tool 이 @safe_tool 규칙 준수 (유지)
    └── test_note.py                # 🔴 데모 도메인 테스트 (교체 참고용)
```

🟢 그대로 재사용 · 🟡 패턴 재사용(내용 교체) · 🔴 도메인마다 새로 작성

---

## 3. 계층별 역할

### Presentation (`presentation/`)
MCP 프로토콜과 맞닿는 얇은 어댑터. **비즈니스 로직을 두지 않는다.**
- **Tool** (`@mcp.tool`): 입력 검증 → UseCase 호출 → 사람이 읽을 문자열 반환.
- **Resource** (`@mcp.resource`): 읽기 전용 데이터를 URI로 노출, JSON 직렬화.
- **Prompt** (`@mcp.prompt`): 클라이언트(Claude)에게 도구 사용 절차를 안내. **산출물 품질을
  좌우하는 지시가 여기 모인다** — 아웃풋이 아쉬우면 이 파일부터 다듬는다.

각 어댑터는 `register_*(mcp, use_case)` 함수로 노출하고, `main.py` 가 호출한다.

### Domain (`domain/`)
순수 파이썬. `mcp`·DB 드라이버·렌더러를 **import하지 않는다**(테스트가 강제).
- **model**: 입력 요청(검증)과 엔티티.
- **ports / repository**: 외부 협력자 인터페이스(`Protocol`).
- **usecase**: 오케스트레이션. 협력자는 생성자로 주입받고 `_run_stage` 로 실패를 구조화.
- **query**: 읽기 전용 유스케이스(생성과 책임 분리).

### Data (`data/`)
Port의 실제 구현체. 파일시스템·DB·네트워크·시계 등 **모든 I/O와 프레임워크가 여기 격리**된다.
도메인을 건드리지 않고 여기만 교체하면 저장소를 SQLite/HTTP 등으로 바꿀 수 있다.

### Core (`core/`)
계층 무관 공통 유틸: 설정(`config`), 예외(`exceptions`), 보안 게이트(`security`).

---

## 4. 데이터 흐름 (요청 → 응답)

```
MCP 클라이언트(Claude)
      │  create_note(title, body)
      ▼
[Presentation] tools/create_note.py     ← 입력 검증(NoteRequest), 예외 → 메시지
      │  use_case(request)
      ▼
[Domain] usecase.CreateNoteUseCase       ← _run_stage 로 단계 오케스트레이션
      │  hash → clock.now() → repo.save()
      ▼
[Data] repository_impl / system_clock    ← 실제 저장·시각
      │  Note(id=...)
      ▲
      └──────────── 결과 문자열 반환 ────────────
```

조립은 오직 `main.py::build()` 에서: **구현체 생성 → UseCase 주입 → register_* 등록.**

---

## 5. 빠른 시작

```bash
cd mcptemplates
uv sync                            # 의존성 설치 (.venv 자동 생성)
uv run ruff check                  # 린트
uv run black --check src tests     # 포맷 검사
uv run mypy src                    # strict 타입검사
uv run pytest                      # 스캐폴딩·가드레일(계층 경계 포함)·기능 테스트
uv run mcp-server                  # stdio MCP 서버 실행
```

> 계층 경계는 `pytest` 가 import-linter 를 돌려 강제합니다. 리포트를 직접 보려면
> `uv run lint-imports --config pyproject.toml` (Windows 에서 출력 캡처 시 `PYTHONUTF8=1` 을 앞에).

로컬 커밋 시점에 위 게이트를 자동 실행하려면 pre-commit 을 설치하세요:

```bash
uv run pre-commit install                      # 커밋 시 ruff·black·mypy·import-linter
uv run pre-commit install --hook-type pre-push # push 시 pytest
```

### Claude Desktop 연동 (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "mcp-server": {
      "command": "uv",
      "args": ["run", "--directory", "/절대경로/mcptemplates", "mcp-server"]
    }
  }
}
```

연동하면 `create_note` · `search_note` 도구, `note://notes` 리소스, `note_quickstart`
프롬프트를 사용할 수 있습니다.

### Docker (선택사항)

이 템플릿은 순수 파이썬 의존성만 쓰므로 **Docker 없이 위 `uv run` 만으로 완결**됩니다.
컨테이너 배포·환경 일관성이 필요할 때만 사용하세요. 런타임 의존성만 담아 슬림합니다
(dev 도구 제외).

```bash
docker build -t mcp-server .
docker run --rm -i mcp-server        # stdio MCP 서버
```

필요 없으면 `Dockerfile`·`.dockerignore` 를 삭제해도 앱 동작에는 영향이 없습니다.

---

## 6. 새 MCP로 재사용하기 (6단계 개명)

이 폴더를 새 위치로 복사한 뒤 개명하면 됩니다. **방법 A(스크립트)** 를 추천합니다.

### 방법 A — 개명 스크립트 (추천, Windows 포함 크로스플랫폼)

동봉된 [`scripts/rename_project.py`](scripts/rename_project.py) 가 아래 6가지를 한 번에 치환합니다
(stdlib 만 사용 — sed 불필요). 이름 하나(`weather` 또는 `weather-mcp`)만 주면 나머지를 유도합니다.

```bash
# 프로젝트 루트에서 (예: weather MCP)
python scripts/rename_project.py weather --dry-run   # 먼저 미리보기(변경 없음)
python scripts/rename_project.py weather             # 실제 개명

uv sync
uv run ruff check --fix    # 개명으로 흐트러진 import 정렬 자동 교정
uv run pytest              # 전 게이트 통과 확인
```

유도 규칙: `weather` → 패키지 `weather_mcp` · 배포명 `weather-mcp` · 접두사 `WEATHER_` ·
서버/클래스 `Weather`(`WeatherError` 포함). 옵션 `--drop-template-docs` 로 템플릿 설명문서
(`TEMPLATE.md`·`ARCHITECTURE_REVIEW.md`)까지 함께 지울 수 있습니다. 개명 후 스크립트는 삭제해도 됩니다.

### 방법 B — 수동 치환 (스크립트를 안 쓸 때)

스크립트가 치환하는 6곳:

| # | 대상 | 현재 값 | 바꿀 값(예) |
|---|---|---|---|
| 1 | 패키지 디렉터리 | `src/mcp_server/` | `src/weather_mcp/` |
| 2 | 전체 import 경로 | `mcp_server` | `weather_mcp` |
| 3 | 콘솔 스크립트 / 패키지명 (`pyproject.toml`) | `mcp-server`, `packages=["src/mcp_server"]` | `weather-mcp`, `src/weather_mcp` |
| 4 | 환경변수 접두사 (`core/config.py`) | `env_prefix="MCPSERVER_"` | `env_prefix="WEATHER_"` |
| 5 | 서버 이름 (`main.py`) | `FastMCP("MCPServer")` | `FastMCP("Weather")` |
| 6 | 베이스 예외 (`core/exceptions.py`) | `MCPServerError` | `WeatherError` |

```bash
git mv src/mcp_server src/weather_mcp   # git 미사용 시 일반 mv
grep -rl 'mcp_server'  src tests | xargs sed -i 's/mcp_server/weather_mcp/g'
grep -rl 'mcp-server'  .         | xargs sed -i 's/mcp-server/weather-mcp/g'
sed -i 's/MCPSERVER_/WEATHER_/g'   src/weather_mcp/core/config.py
sed -i 's/MCPServer/Weather/g'     src/weather_mcp/main.py src/weather_mcp/core/exceptions.py src/weather_mcp/domain/*/usecase.py
uv sync && uv run ruff check --fix && uv run pytest
```

두 방법 모두 끝난 뒤 `domain/note`, `data/note`, `presentation/*` 의 `note` 를 실제 도메인으로 교체합니다.

> **PowerShell 사용자:** `(Get-Content file) -replace 'mcp_server','weather_mcp' | Set-Content file`
> 형태로 파일별 치환하거나, Git Bash에서 위 명령을 실행하세요.

---

## 7. 기능 추가 레시피

새 Tool 하나를 추가하는 전형적인 순서 (기존 파일이 모두 예시가 됩니다):

1. **도메인 모델** — `domain/<feature>/model.py` 에 요청/엔티티 정의(Pydantic으로 입력 검증).
2. **Port 필요 시 선언** — 외부 협력자가 필요하면 `ports.py`/`repository.py` 에 `Protocol` 추가.
3. **UseCase 작성** — `usecase.py` 에 오케스트레이션. 실패 가능 단계는 `_run_stage` 로 감싼다.
4. **구현체 작성** — `data/<feature>/` 에 Port 구현(파일/DB/HTTP 등 I/O는 여기서만).
5. **어댑터 등록** — `presentation/tools/<name>.py` 에 `register_*_tool(mcp, use_case)` 작성.
   실패 처리는 `@safe_tool` 이 일괄 담당하므로 어댑터에 `try/except` 를 직접 쓰지 않는다:
   ```python
   from mcp_server.presentation._safe import safe_tool

   def register_xxx_tool(mcp, use_case):
       @mcp.tool()
       @safe_tool                          # ← PipelineError → 메시지 변환을 일원화
       def xxx(arg: str) -> str:
           result = use_case(...)          # 로직은 UseCase에
           return format(result)           # 사람이 읽을 문자열
   ```
6. **조립** — `main.py::build()` 에서 구현체 생성 → UseCase 주입 → `register_xxx_tool(mcp, uc)`.
7. **테스트** — `test_note.py` 처럼 Port에 테스트 더블(고정 시계/인메모리 저장소)을 주입해 검증.

---

## 8. 자주 하는 확장

### 저장소를 SQLite로 교체
`data/note/repository_impl.py` 만 바꾸면 됩니다(도메인·유스케이스 불변).
1. `pyproject.toml` 에 `sqlalchemy>=2.0` 추가.
2. `config.py` 에 `db_path` 필드와 세션 팩토리(`cached_property`) 추가.
3. `SqliteNoteRepository(session_factory)` 작성 후 `main.py` 에서 인메모리 대신 주입.
> `test_scaffolding.py` 의 `forbidden` 집합에 `sqlalchemy` 가 이미 있어, 실수로 도메인에서
> import하면 테스트가 잡아줍니다.

### 파일 산출물(PDF/HTML 등) 생성
1. `pyproject.toml` 에 렌더러(`jinja2`)·변환기(`weasyprint`) 추가.
2. `domain/<feature>/ports.py` 에 `Renderer`·`Exporter` `Protocol` 선언.
3. `data/<feature>/` 에 구현체, `config.py` 에 `template_dir`·`output_dir` 추가.
4. `security.py` 의 `sanitize_filename` 으로 출력 파일명을 안전화(이미 포함됨).

### 외부 API 호출
`domain/<feature>/ports.py` 에 클라이언트 `Protocol` 선언 → `data/` 에 `httpx` 등으로 구현 →
`main.py` 주입. 도메인은 HTTP를 모른 채 인터페이스에만 의존합니다.

---

## 9. 실행 가능한 가드레일

문서로만 있는 규칙은 지켜지지 않습니다. 이 템플릿은 핵심 규칙을 **테스트·린터로 강제**해,
사람이든 AI 에이전트든 규칙을 어기면 게이트가 빨간불로 잡습니다.

| 가드레일 | 강제하는 규칙 | 어디서 |
|---|---|---|
| **import-linter** (`[tool.importlinter]`) | 계층 방향 `presentation → data → domain → core` (역방향 import 금지) | `lint-imports` · CI · pre-commit · `test_guardrails.py` |
| **`test_scaffolding.py`** | domain 이 프레임워크(mcp·pydantic_settings·DB)를 import 하지 않음 | pytest |
| **`test_guardrails.py`** | ① 계층 계약 유지 ② 기대한 Tool 이 모두 등록됨(`EXPECTED_TOOLS`) | pytest |
| **`test_adapters.py`** | 모든 Tool 이 `@safe_tool` 의 3갈래 실패 규칙을 따름 | pytest |
| **mypy strict** | 타입 계약 위반을 컴파일 타임에 차단 | `mypy src` · CI · pre-commit |
| **pre-commit** | 위 게이트를 커밋/푸시 시점에 자동 실행 | `.pre-commit-config.yaml` |

> **새 도구를 추가하면** `test_guardrails.py` 의 `EXPECTED_TOOLS` 에 이름을 더하세요. 등록을
> 빠뜨리면 테스트가 실패해 알려줍니다. 계층을 어긴 import 를 넣으면 `lint-imports` 가 막습니다.

이 가드레일들이 있어, AI 에이전트가 콜드스타트로 작업해도 **아키텍처를 벗어난 코드는 병합 전에
걸러집니다.** 에이전트 작업 규칙은 [AGENTS.md](AGENTS.md) 참고.

---

## 10. 무엇을 지우고 무엇을 남길까

| 파일/의존성 | 남길까? |
|---|---|
| `core/config.py`, `exceptions.py`, `logging.py` | ✅ 항상 남긴다 |
| `presentation/_safe.py` (`@safe_tool`) | ✅ 남긴다(에러 처리 통일) |
| `core/security.py` | 파일을 읽거나 쓰면 남기고, 아니면 삭제 가능 |
| `test_scaffolding.py`, `test_guardrails.py`, `test_adapters.py` | ✅ 남긴다(가드레일). 도메인에 맞게 조정 |
| `domain/note`, `data/note`, `presentation/*` 의 note | 🔁 실제 도메인으로 교체 |
| `hashing.py` | 재현성이 필요 없으면 삭제 가능 |
| 인메모리 리포지토리 | 세션 넘어 영속화가 필요하면 SQLite 등으로 교체 |
| `Dockerfile`, `.dockerignore` | **선택사항.** 컨테이너 배포가 필요 없으면 삭제 가능(앱 동작 무관) |

---

## 11. 체크리스트

새 MCP 서버 개시 후 아래가 모두 초록이면 뼈대가 정상 이식된 것입니다.

- [ ] 6단계 개명 완료 (`grep -r mcp_server src` 결과 없음)
- [ ] `uv sync` 성공
- [ ] `uv run pytest` — `test_build_returns_fastmcp_server` 통과 (서버 조립 OK)
- [ ] `uv run pytest` — `test_domain_has_no_framework_imports` 통과 (계층 분리 OK)
- [ ] `uv run lint-imports --config pyproject.toml` 통과 (계층 경계 OK)
- [ ] `uv run ruff check` / `black --check` / `mypy src` 모두 통과
- [ ] `uv run <스크립트명>` 으로 stdio 서버 기동 확인
- [ ] Claude Desktop에 연동해 도구 호출 확인

---

**요약:** 이 템플릿에서 실제로 "다시 써먹는" 것은 교재도 노트도 아니라, **`main.py` 조립 방식 ·
Port 주입 · `_run_stage` 실패 구조화 · `@safe_tool` 에러 통일 · 도메인 무의존 규칙 · 실행 가능한
가드레일**입니다. 도메인은 매번 새로 짜되, 이 뼈대 위에 얹으면 첫날부터 계층이 분리되고
테스트·타입검사·계층 경계가 자동 강제되는 상태로 출발합니다.
