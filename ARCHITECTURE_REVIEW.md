# 아키텍처 검토 보고서

> 두 가지 질문에 답합니다.
> **(1)** 이 Clean Architecture 구조는 다른 사람들의 MCP 서버에서도 흔히 보이는 패턴인가?
> **(2)** 리팩토링·유지보수성을 더 높일 요소는 없는가?

---

## Part 1. 이 구조는 다른 MCP에서도 흔한 패턴인가?

**한 줄 결론:** MCP와 맞닿는 *표면*은 100% 업계 표준이고, 그 *뒤의 레이어링*은
"흔한 기본형"이 아니라 **규모가 커진 팀이 의도적으로 채택하는 소수파(프로덕션 지향) 패턴**입니다.
두 층위를 나눠 봐야 정확합니다.

### 층위 A — MCP 표면(Tool / Resource / Prompt): **완전한 표준**

`@mcp.tool` · `@mcp.resource` · `@mcp.prompt` 데코레이터로 프로토콜 보일러플레이트를
평범한 파이썬 함수로 접는 방식은 공식 SDK(FastMCP)가 밀고, 사실상 모든 파이썬 MCP 서버가
이렇게 씁니다. 이 프로젝트도 정확히 이 표준을 따릅니다. → **여기는 이견 없이 "남들과 같다".**

### 층위 B — 내부 레이어링(Domain/Data/Presentation, Port, DI): **소수의 규율파**

생태계 현황을 대조하면 스펙트럼이 이렇습니다.

| 유형 | 구조 | 얼마나 흔한가 |
|---|---|---|
| **단일 파일** | `server.py` 하나에 데코레이터 함수 나열 | 압도적 다수(입문·소형 서버의 기본형) |
| **기능별 모듈 분할** | `tools/`, `resources/` 로만 파일 나눔 | 중간 규모에서 흔함 |
| **Clean Arch / 헥사고날 / DDD** | 도메인·포트·어댑터 분리 + DI (← **이 프로젝트**) | 소수. "프로덕션/확장성" 주제의 블로그·레포로 별도 소개됨 |

핵심은 **Clean Architecture/DDD를 MCP에 적용한 사례가 "따로 글로 쓰일 만큼" 존재**한다는 점입니다.
즉 존재하고 인정받는 패턴이지만, *기본값은 아닙니다*. 사람들이 일부러 "우리는 이렇게 했다"고
소개하는 것 자체가, 이게 표준 관성이 아니라 **의도적 선택**임을 방증합니다. 대표적으로 Clean
Architecture MCP 서버 구현 레포, DDD로 확장 가능한 MCP를 다룬 글, .NET Clean Architecture +
MCP 예제 등이 공개돼 있습니다.

### Part 1 판정

- **당신은 표준을 벗어난 게 아니라, 표준 표면 위에 "더 규율 있는 소수파" 내부 구조를 얹은 것**입니다.
- 이 선택은 **서버가 커질수록**(도구 다수·외부 연동·팀 협업·테스트 요구) 정당화됩니다. 반대로
  도구 1~2개짜리 초소형 서버에는 과한 형식이 될 수 있습니다(→ Part 2의 "과설계 경고" 참조).
- 원본 `vibetutor-mcp`처럼 파이프라인(스캔→렌더→변환→저장)이 있고 재현성·실패 진단이 중요한
  도메인에서는 이 구조가 특히 값을 합니다. **선택은 타당합니다.**

---

## Part 2. 유지보수성·리팩토링 향상 요소 (우선순위별)

지금 구조는 이미 견고합니다(계층 분리·DI·구조화 실패·테스트 규칙). 아래는 "더 얹으면 좋은"
것들을, **비용 대비 효과 순**으로 3티어로 정리했습니다.

### 🟢 Tier 1 — 지금 바로 (저비용·고효과)

**1. 로깅을 stderr로 (MCP 특유의 함정 — 가장 중요)**
stdio 전송에서 **stdout은 JSON-RPC 프로토콜 전용 채널**입니다. `print()` 나 stdout으로 나가는
로그는 프로토콜을 오염시켜 클라이언트 연결을 깨뜨립니다. 현재 코드엔 로깅이 아예 없어, 장애 추적이
어렵습니다. 표준 `logging` 을 **stderr 핸들러로** 붙이세요.
```python
# core/logging.py
import logging, sys
def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stderr)   # ← 반드시 stderr
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler])
# main.py build() 첫 줄에서 configure_logging() 호출, 모듈마다 logging.getLogger(__name__)
```

**2. 어댑터 에러 처리 통일 (현재 불일치 존재)**
`create_note` 는 `PipelineError` 를 잡아 메시지로 바꾸지만 `search_note` 는 안 잡습니다. 규칙이
어댑터마다 다르면 유지보수 시 빠뜨리기 쉽습니다. **공용 헬퍼/데코레이터로 한 곳에 모으세요.**
```python
# presentation/_safe.py
from functools import wraps
from mcp_server.core.exceptions import PipelineError
def safe_tool(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        try:
            return fn(*a, **k)
        except PipelineError as e:
            return f"실패 [{e.stage}] {e.reason}\n힌트: {e.hint}"
    return wrapper
# 각 @mcp.tool() 내부 함수에 @safe_tool 을 함께 붙이면 처리 일원화
```

**3. 시작 시 설정 검증(fail fast)**
잘못된 경로·권한을 서버 부팅 시점에 명확한 예외로 끊으면, 첫 도구 호출에서 모호하게 터지는 것보다
디버깅이 쉽습니다. `Settings` 에 `@model_validator` 로 출력 디렉터리 생성 가능 여부 등을 확인.

**4. pre-commit 훅**
CI가 이미 ruff/black/mypy/pytest를 돌리지만, 커밋 시점에 로컬에서 먼저 걸러주면 왕복이 줄고
"CI에서만 실패"가 사라집니다. `.pre-commit-config.yaml` 추가(ruff·black·mypy).

### 🟡 Tier 2 — 도구가 5개를 넘어가면

**5. 기능별 등록을 하나로 묶기 (`main.py` 비대화 방지)**
현재 `build()` 는 도구가 늘 때마다 지역변수(구현체·유스케이스)와 `register_*` 호출이 함께
늘어납니다. **기능 단위 진입점** `register_note_feature(mcp, container)` 로 묶으면 `build()` 는
기능 목록만 순회하게 됩니다.
```python
FEATURES = [register_note_feature, register_weather_feature, ...]
for feature in FEATURES:
    feature(mcp, container)
```
> 단, "명시적 조립"의 장점(어디서 뭐가 붙는지 한눈에 보임)을 잃지 않도록, 목록은 여전히 `main.py`
> 한곳에 두세요. 자동 스캔(파일 자동 로딩)까지 가면 추적성이 오히려 나빠집니다.

**6. 경량 DI 컨테이너**
구현체가 늘면 `build()` 의 지역변수가 난립합니다. `@dataclass(frozen=True) Container` 하나에
공용 의존성(clock·repository·logger·settings)을 모아 기능 등록 함수에 넘기면 시그니처가 안정됩니다.

**7. I/O 바운드 도구는 async로**
외부 API·DB를 호출하는 도구는 `async def` 로 두면 FastMCP가 동시성을 살립니다. 지금은 CPU/메모리
작업이라 sync가 맞지만, HTTP 연동을 붙일 땐 어댑터를 async로.

**8. 프로토콜 경계 통합 테스트**
현재 테스트는 유스케이스까지입니다. **실제 MCP 서버 인스턴스에 도구를 호출**해 스키마·직렬화까지
검증하는 테스트를 추가하면 어댑터 회귀를 잡습니다(SDK의 인메모리 클라이언트 활용).

### 🔵 Tier 3 — 팀·장기 관점

- **ADR(아키텍처 결정 기록)**: "왜 Clean Architecture인가", "왜 인메모리 대신 SQLite로 갔나" 등을
  `docs/adr/0001-*.md` 로 남기면 신규 인원 온보딩과 되돌아보기가 쉬워집니다.
- **`py.typed` 마커 + `__all__`**: 패키지를 배포/재사용할 경우 다운스트림에 타입을 제공하고 공개
  API 경계를 명확히 합니다.
- **에러 taxonomy 세분화**: `PipelineError` 아래에 `RenderError`·`PersistError` 등 단계별 하위
  예외를 두면 어댑터가 상황별로 다른 안내를 줄 수 있습니다(지금은 문자열 stage로 구분).

### ⛔ 과설계 경고 — "안 하는 게 유지보수"인 것들

규모에 비해 아래를 도입하면 **오히려 부채**가 됩니다.
- 도메인 이벤트 버스 / CQRS 인프라 / 메시지 큐 — 도구 2~3개 서버엔 불필요한 무게.
- 리포지토리 위에 또 서비스 레이어 한 겹 더 쌓기 — 지금은 유스케이스가 그 역할을 충분히 함.
- 모든 것을 인터페이스로 추상화 — 구현이 하나뿐인 협력자까지 Port로 만들면 탐색 비용만 늘어남.
  (Port는 "교체·테스트 대역이 실제로 필요한 곳"에만.)

---

## 우선 적용 추천 (Top 3)

규모와 효과를 함께 보면, 지금 당장은 이 세 가지가 가장 값집니다.

1. **stderr 로깅** — MCP 함정 제거 + 장애 추적성 확보. (거의 필수)
2. **어댑터 에러 처리 통일** — 이미 있는 불일치를 제거, 새 도구 추가 시 실수 방지.
3. **pre-commit 훅** — CI 게이트를 로컬로 당겨 왕복 비용 절감.

나머지(기능별 등록·DI 컨테이너·통합 테스트)는 **도구 개수가 실제로 늘어나는 시점**에 도입하는 게
비용 대비 효율적입니다. 원한다면 위 Top 3를 이 템플릿에 바로 반영해 드리겠습니다.

---

### 출처

- [MCP Best Practices: Architecture & Implementation Guide](https://modelcontextprotocol.info/docs/best-practices/)
- [Architecture overview — Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)
- [GitHub — kattatzu-resources/mcp-server (clean architecture MCP server)](https://github.com/kattatzu-resources/mcp-server)
- [Building Scalable MCP Servers with Domain-Driven Design (Chris Hughes)](https://medium.com/@chris.p.hughes10/building-scalable-mcp-servers-with-domain-driven-design-fb9454d4c726)
- [Building a Production-Ready Weather MCP Server with Clean Architecture (DEV)](https://dev.to/glaucia86/building-a-production-ready-weather-mcp-server-with-clean-architecture-redis-cache-and-solid-32cp)
- [GitHub — danielmackay/dotnet-mcp-hero (Clean Architecture + MCP)](https://github.com/danielmackay/dotnet-mcp-hero)
- [FastMCP (PrefectHQ) — GitHub](https://github.com/PrefectHQ/fastmcp)
