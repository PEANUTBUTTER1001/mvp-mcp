# AGENTS.md — 코딩 에이전트를 위한 작업 규칙

> 이 저장소의 코드는 AI 에이전트가 작성/수정한다. 이 문서는 **매 세션 시작에 로드하는
> 맥락**이다. 짧게 유지한다(장황한 설명 대신 규칙과 레시피만). 아키텍처 배경 설명은
> `TEMPLATE.md`, 설계 근거는 `ARCHITECTURE_REVIEW.md` 참고.

## 이 서버가 하는 일

Clean Architecture 기반 MCP 서버. 현재 데모 도메인은 `note`(노트 생성/검색). MCP 클라이언트
(Claude 등)에 Tool·Resource·Prompt 를 제공한다.

## 절대 규칙 (위반하면 가드레일이 실패시킨다)

1. **계층 방향은 단방향이다:** `presentation → data → domain → core`.
   낮은 레이어는 높은 레이어를 **절대 import 하지 않는다.**
   - `domain/` 은 `mcp`·`pydantic_settings`·DB 드라이버·렌더러 등 **프레임워크를 import 하지 않는다.**
   - 이 규칙은 `tests/test_guardrails.py`(import-linter)와 `tests/test_scaffolding.py` 가 강제한다.
2. **의존성 조립은 오직 `src/mvp_mcp/main.py::build()` 에서만** 한다. 다른 곳에서 구현체를
   직접 생성하지 않는다.
3. **Tool/Resource 어댑터에 비즈니스 로직을 두지 않는다.** 검증 → UseCase 호출 → 문자열화만.
4. **로그는 stderr 로만** 나간다(`core/logging.py`). `print()` 금지 — stdout 은 프로토콜 채널이다.
5. **한 가지 패턴만 반복한다.** 새 기능은 아래 레시피를 그대로 복제한다. 독자적 구조를 발명하지 않는다.

## 코드 위치 지도 (무엇을 어디에 두나)

| 넣을 것 | 위치 |
|---|---|
| 입력/출력 모델(Pydantic) | `domain/<feature>/model.py` |
| 외부 협력자 인터페이스(Protocol) | `domain/<feature>/ports.py`, `repository.py` |
| 비즈니스 오케스트레이션 | `domain/<feature>/usecase.py` (쓰기), `query.py` (읽기) |
| Port 구현체(DB·파일·API·시계) | `data/<feature>/...`, `data/system_clock.py` |
| Tool 어댑터 | `presentation/tools/<name>.py` |
| Resource 어댑터 | `presentation/resources/<name>.py` |
| Prompt 어댑터 | `presentation/prompts/<name>.py` |
| 설정(환경변수) | `core/config.py` |
| 공통 예외 | `core/exceptions.py` |
| 조립(와이어링) | `main.py::build()` |

## 고정 패턴 — 새 Tool 추가 레시피

기존 `note` 를 그대로 본떠 아래 순서로 만든다. **이 형태에서 벗어나지 않는다.**

1. **모델** `domain/<feature>/model.py`: 요청 모델(Pydantic, 입력 검증)과 엔티티.
2. **Port(필요 시)** `ports.py`/`repository.py` 에 `Protocol` 선언.
3. **UseCase** `usecase.py`: 협력자는 생성자로 주입. 실패 가능 단계는 `_run_stage` 로 감싼다.
4. **구현체** `data/<feature>/...`: Port 를 구현(모든 I/O 는 여기서만).
5. **어댑터** `presentation/tools/<name>.py` — 정확히 이 골격:
   ```python
   from mcp.server.fastmcp import FastMCP
   from mvp_mcp.presentation._safe import safe_tool

   def register_<name>_tool(mcp: FastMCP, use_case: <UseCase>) -> None:
       @mcp.tool()
       @safe_tool                       # ← 실패 처리는 여기에 위임(try/except 직접 쓰지 말 것)
       def <name>(arg: str) -> str:
           result = use_case(...)       # 로직은 UseCase 에
           return f"...{result}..."     # 사람이 읽을 문자열
   ```
6. **조립** `main.py::build()`: 구현체 생성 → UseCase 주입 → `register_<name>_tool(mcp, uc)`.
7. **가드레일 갱신** `tests/test_guardrails.py` 의 `EXPECTED_TOOLS` 에 도구 이름 추가.
8. **테스트** `tests/test_<feature>.py`: Port 에 테스트 더블(고정 시계·인메모리 저장소) 주입.

## 작업을 마치기 전 반드시 실행 (모두 통과해야 함)

```bash
uv run ruff check
uv run black --check src tests
uv run mypy src
uv run pytest -q        # 스캐폴딩·가드레일(계층 경계 포함)·기능 테스트
```

한 줄 검증: `uv run ruff check && uv run black --check src tests && uv run mypy src && uv run pytest -q`

> **계층 경계**는 `pytest`(`test_guardrails.py`)가 import-linter 를 Python API 로 돌려 강제하므로
> 위 `pytest` 한 번으로 검증된다. 리포트를 눈으로 보려면 `uv run lint-imports --config pyproject.toml`
> 을 쓰되, **Windows 에서 출력을 파일/파이프로 캡처하면 rich 인코딩(cp949)으로 깨진다** — 그때는
> 앞에 `PYTHONUTF8=1` 을 붙여라(예: `PYTHONUTF8=1 uv run lint-imports --config pyproject.toml`).

## 하지 말 것 (과설계 금지)

- 구현이 하나뿐인 협력자를 Port 로 추상화하지 않는다(교체·테스트 대역이 실제 필요할 때만).
- 유스케이스 위에 서비스 레이어를 한 겹 더 쌓지 않는다.
- 도메인 이벤트 버스/CQRS 등 인프라를 도입하지 않는다.
- 어댑터마다 다른 에러 처리 방식을 만들지 않는다 — 항상 `@safe_tool`.
