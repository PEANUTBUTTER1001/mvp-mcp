# mvp-mcp — MVP 설계 전문 MCP 서버

> 사용자의 짧고 모호한 한 줄 요청("메신저 만들어줘")을 **구현 가능한 MVP 프로젝트 명세(Specification)** 로 변환하는 MCP 서버.
> 답을 대신 생성하지 않고, **LLM보다 먼저 생각하는 PM(Product Manager)** 역할을 한다.

```
사용자 → [ mvp-mcp: 요구사항 분석·설계 ] → LLM(설계·구현)
```

좋은 결과물은 좋은 답변이 아니라 **좋은 요구사항**에서 시작한다. 이 서버는 사용자의 한 줄 요청을
프로젝트 유형 분류 → 도메인 템플릿 적용 → 부족한 정보 질문 → MVP 범위 제한 → 기술 스택 결정 →
품질 검증을 거쳐, LLM이 최고의 결과를 내도록 **입력 컨텍스트의 품질**을 끌어올린다.

---

## 핵심 아이디어 — 역할 분담

MCP 서버는 스스로 추론하지 않는다. 그래서 책임을 명확히 나눈다.

| 서버가 소유 (결정적) | 클라이언트 LLM이 담당 (의미 해석) |
|---|---|
| 유형별 템플릿(포함/제외 기능), 필수 필드 검사, 질문 뱅크 | 사용자 요청을 유형으로 분류 |
| 기본 기술 스택, 11섹션 출력 형식, 품질 체크리스트 | 사용자 답변을 필드 값으로 정리 |
| 명세 초안 상태(수집→범위확정→최종화) | 최종 컨텍스트에 따라 명세 문서 작성 |

이 설계로 기획의 두 축을 코드로 **강제**한다.

- **"추측해서 결정하지 않는다"** → 필수 필드가 비면 `finalize_spec`이 오류로 거부한다.
- **"MVP 범위를 제한한다"** → `scope_mvp`가 템플릿의 제외 목록 기반으로 기능을 컷한다.

---

## 빠른 시작

### 요구사항
- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (패키지·실행 관리)

### 설치 & 실행

```bash
git clone <이 저장소 URL>
cd mvp-mcp
uv sync                 # 의존성 설치 (.venv 자동 생성)
uv run mvp-mcp          # stdio MCP 서버 실행
```

서버가 도구 5개·리소스 3종·프롬프트 1개를 등록하는지 스모크 테스트:

```bash
uv run python -c "from mvp_mcp.main import build; s=build(); print(sorted(t.name for t in s._tool_manager.list_tools()))"
# → ['answer_question', 'finalize_spec', 'get_missing_info', 'scope_mvp', 'start_spec']
```

### Claude Desktop 연동

`claude_desktop_config.json` 에 아래를 추가하고 Claude Desktop을 재시작한다.

```json
{
  "mcpServers": {
    "mvp-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/절대경로/mvp-mcp", "mvp-mcp"]
    }
  }
}
```

> Windows 경로 예: `"C:/Users/이름/mvp-mcp"` (역슬래시 대신 슬래시 권장).

연동 후 `mvp_spec_workflow` 프롬프트를 선택하거나, 그냥 "메신저 만들어줘"처럼 요청하면 된다.

### Docker (선택)

```bash
docker build -t mvp-mcp .
docker run --rm -i mvp-mcp        # stdio MCP 서버
```

순수 파이썬 의존성만 쓰므로 Docker 없이 `uv run` 만으로 완결된다. 필요 없으면 `Dockerfile` 삭제 가능.

---

## 사용 흐름 (9단계 파이프라인)

```
사용자 요청
   │
   ▼
① 프로젝트 분류 ─ ② 도메인 템플릿 ─ ③ 요구사항 분석 ─ ④ 부족한 정보 식별
   │
   ▼
⑤ 추가 질문 ─ ⑥ MVP 범위 제한 ─ ⑦ 기술 스택 ─ ⑧ 산출물 형식 ─ ⑨ 품질 검증
   │
   ▼
LLM에게 최종 컨텍스트 전달
```

도구 호출 순서: **`start_spec` → (`answer_question` 반복) → `scope_mvp` → `finalize_spec`**

---

## 제공 도구 (Tools)

| 도구 | 파라미터 | 하는 일 |
|---|---|---|
| `start_spec` | `project_type`, `user_request`, `known_info?` | 유형 템플릿을 적용해 명세 세션을 시작하고 `spec_id` 발급, **부족한 정보의 질문 목록** 반환 |
| `answer_question` | `spec_id`, `field`, `value` | 답 하나를 초안에 반영하고 **남은 질문** 반환 |
| `get_missing_info` | `spec_id` | 아직 미충족인 필수 정보의 질문을 재조회 |
| `scope_mvp` | `spec_id`, `requested_features?` | 요청 기능을 MVP 범위로 판정(포함 / 컷+사유) |
| `finalize_spec` | `spec_id` | 품질 검증 통과 시 **최종 명세 컨텍스트 전문** 반환, 미통과 시 사유 안내 |

### 제공 리소스 (Resources)

| URI | 내용 |
|---|---|
| `spec://project-types` | 지원 유형 목록 + `display_name` + 핵심 기능 (JSON) |
| `spec://templates/{type}` | 해당 유형 템플릿 전체 직렬화 (JSON) |
| `spec://drafts/{spec_id}` | 초안 현재 상태 (JSON) |

### 제공 프롬프트 (Prompt)

- `mvp_spec_workflow` — 클라이언트 LLM에게 위 도구를 어떤 순서로 쓰는지, "모르는 값을 추측하지 말 것" 등 원칙을 안내한다. **산출물 품질을 좌우하는 지시가 여기 모여 있다.**

> **출력 언어:** 최종 명세는 기본적으로 **한국어**로 작성된다(`finalize_spec` 컨텍스트와 프롬프트에 지시가 포함됨). 다른 언어로 받고 싶으면 대화에서 그 언어로 요청하면 된다.

---

## 지원 프로젝트 유형

**유형마다 질문·기본 스택·출력 형식(섹션)이 다릅니다.** 유형은 크게 세 그룹으로 나뉩니다.

**① 앱/웹 소프트웨어** — 출력 형식: 화면 목록·DB 설계·API 설계 등 11섹션

| 유형(`project_type`) | 포함(MVP 코어) | 제외(확장 계획으로) |
|---|---|---|
| `messenger` | 회원가입, 로그인, 친구목록, 채팅방, 1:1 채팅, 메시지 저장, 채팅목록, 알림 | 영상/음성통화, AI 번역·요약, 커뮤니티, 채널, 라이브, 이모티콘 스토어 |
| `shopping_mall` | 회원가입, 로그인, 상품목록/상세, 장바구니, 주문, 결제, 마이페이지 | 리뷰, 쿠폰/포인트, 추천 알고리즘, 판매자 입점, 실시간 상담, 정기구독 |
| `blog` | 게시글 작성/조회, 댓글, 카테고리, 검색, 관리자 | 뉴스레터, 유료 멤버십, 통계 대시보드, 다중 작성자, SEO 고급 |

**② 개발 도구** — 출력 형식: 인터페이스 설계(Tool/Resource/Prompt)·입출력 계약·배포·통합 등 12섹션

| 유형(`project_type`) | 포함(MVP 코어) | 제외(확장 계획으로) |
|---|---|---|
| `mcp_server` | 도구 정의, 리소스 노출, 프롬프트 제공, 입력 검증, 에러 처리, 설정 로딩 | 인증/권한, 다중 전송(SSE/HTTP), 영속 저장소, 관측성/메트릭, 레이트 리미팅 |

**③ ML/데이터** — 출력 형식: 데이터 명세·모델/평가 또는 파이프라인 아키텍처·스케줄링 등 12섹션

| 유형(`project_type`) | 포함(MVP 코어) | 제외(확장 계획으로) |
|---|---|---|
| `ml_project` | 데이터 로딩, 전처리, 피처 엔지니어링, 베이스라인 모델, 평가, 실험 로깅 | 하이퍼파라미터 자동탐색, 분산 학습, 모델 서빙 API, A/B 테스트, 피처 스토어 |
| `data_pipeline` | 데이터 수집, 정제/변환, 적재, 스케줄링, 실패 재시도, 로깅 | 실시간 스트리밍, 데이터 카탈로그, 리니지 추적, 자동 스케일링, 품질 대시보드 |

**④ 폴백** — `etc`: 어디에도 안 맞을 때. 요청 기능 중 최대 7개를 승인, 초과분은 컷. 앱용 11섹션 형식 사용.

> 유형 추가는 코드 변경 없이 [`templates_data.py`](src/mvp_mcp/domain/spec/templates_data.py)에 항목만 더하면 된다. 지원하지 않는 값이나 생략 시 자동으로 `etc`로 처리된다.

**필수 정보(유형별로 다름):** 모든 유형 공통 2개(개발 목적, 기술 스택 지정 여부)에 더해 —
- 앱/웹: 플랫폼, 로그인 방식, 실시간 여부
- 개발 도구: 인터페이스, 런타임/언어, 배포 방식
- ML/데이터: 데이터 출처, (ML만) 문제 유형, 산출물 형태

미답변 필수 항목이 있으면 `finalize_spec`이 거부한다("추측 금지").

**기본 기술 스택(유형별):**
- 앱/웹: Flutter · FastAPI · PostgreSQL · SQLAlchemy · JWT · Supabase Storage · Docker (플랫폼이 "웹"이면 프런트엔드를 `React (Next.js)`로 치환)
- 개발 도구: Python · mcp[cli] (FastMCP) · Pydantic · uv+hatchling · PyPI · stdio
- ML: Python · pandas/numpy · scikit-learn/PyTorch · MLflow · Jupyter
- 데이터: Python · pandas/Polars · Prefect/Airflow · PostgreSQL/Parquet · Docker

스택을 "직접 지정"으로 택하면 서버는 스택을 추측하지 않고 LLM에게 위임한다.

---

## 예시: "메신저 만들어줘"

1. LLM이 `spec://project-types`를 보고 유형을 `messenger`로 정한다.
2. `start_spec(project_type="messenger", user_request="메신저 만들어줘")` → `spec_id`와 **다음 질문 하나**(설명·보기·힌트 포함) 반환.
3. 사용자가 답하면 `answer_question`으로 반영 → 다음 질문 하나. 질문이 소진될 때까지 **한 번에 하나씩** 문답(플랫폼·목적·기술 스택·로그인·실시간).
4. `scope_mvp(spec_id, requested_features=["영상통화", "1:1 채팅"])`
   → "1:1 채팅"은 코어라 포함, **"영상통화"는 컷**되어 확장 계획으로.
5. `finalize_spec(spec_id)` → 아래 형태의 최종 컨텍스트를 반환. LLM은 이를 따라 **두 문서(기획서 + 실행 명세서)**를 작성한다.

```markdown
# MVP 프로젝트 명세 컨텍스트

## 확정 정보
- 프로젝트 유형: 메신저
- 원문 요청: 메신저 만들어줘
- 목적: 개인 프로젝트
- 플랫폼: 모바일
...

### 기술 스택
- frontend: Flutter
...

## MVP 범위 (이 목록을 벗어난 기능을 추가하지 말 것)
- 포함: 회원가입, 로그인, 친구목록, 채팅방, 1:1 채팅, 메시지 저장, 채팅목록, 알림
- 제외(확장 계획에만 언급): 영상통화 — MVP 범위 밖(핵심 이후 확장)

## 출력 지시
**모든 문서는 한국어(한글)로 작성하라.** 아래 두 개의 문서를 순서대로 작성하라: ① 기획서(PROPOSAL) ② 실행 명세서(PLAN).

## 문서 1 — 기획서 (PROPOSAL)
### 1. 배경 & 문제 정의 / 2. 목표 & 기대 효과 / 3. 대상 사용자 / 4. 핵심 가치 / 5. MVP 범위 / 6. 성공 지표 / 7. 리스크 & 가정

## 문서 2 — 실행 명세서 (PLAN)
### 1. 프로젝트 개요 ... 6. DB 설계(컬럼·제약까지) ... 7. API 설계(Method·Path 목록) ... 11. 이후 확장 계획

## 제약
- 위 MVP 범위의 기능만 설계한다. 정보를 추측으로 채우지 않는다.
```

LLM은 이 컨텍스트의 **순서·범위·섹션별 지침을 그대로 따라** 표·DB 스키마·API 목록·주 단위 일정까지 담긴 완결된 11섹션 명세를 작성한다.

---

## 개발

```bash
uv run pytest -q                 # 테스트 (도메인·가드레일·어댑터)
uv run ruff check                # 린트
uv run black --check src tests   # 포맷 검사
uv run mypy src                  # strict 타입 검사
```

전 게이트 한 번에 (bash 기준):

```bash
uv run ruff check && uv run black --check src tests && uv run mypy src && uv run pytest -q
```

### 아키텍처

Clean Architecture 단방향 계층: **`presentation → data → domain → core`**.
`domain/`은 프레임워크(`mcp`·DB 드라이버)를 import하지 않는다. 이 규칙은 문서가 아니라
[import-linter](pyproject.toml)와 `tests/`의 가드레일 테스트가 **강제**한다.

```
src/mvp_mcp/
├── main.py                 # Composition Root: build() → FastMCP
├── core/                   # 설정·예외·로깅 (계층 무관 공통)
├── domain/spec/            # 순수 도메인: model·templates_data·usecase·query·checklist·output_format
├── data/spec/              # Port 구현체: 인메모리 저장소·템플릿 저장소
└── presentation/           # MCP 어댑터: tools·resources·prompts
```

- 아키텍처 배경: [TEMPLATE.md](TEMPLATE.md)
- 에이전트 작업 규칙: [AGENTS.md](AGENTS.md)
- 구현 명세: [PLAN.md](PLAN.md) · 기획 원문: [PROPOSAL.md](PROPOSAL.md)

### 확장 아이디어

1. 프로젝트 유형 확충(SNS·게임·예약 시스템 등) — `templates_data.py`에 데이터만 추가
2. 초안 영속화(인메모리 → SQLite) — `data/spec/`의 저장소 구현체만 교체
3. 명세 마크다운/PDF 내보내기 도구
4. 유형별 출력 형식 오버라이드

---

## 라이선스

MIT
