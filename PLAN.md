# PLAN.md — MVP 설계 전문 MCP 구현 계획서 (실행 명세)

> **이 문서는 자기완결적 구현 명세다.** 새 세션의 에이전트는 이 문서만 읽고 바로 구현을
> 시작할 수 있어야 한다. 작업 규칙은 [AGENTS.md](AGENTS.md)를 따르고, 뼈대 배경이 궁금할
> 때만 [TEMPLATE.md](TEMPLATE.md)를 참고한다. 기획 원문은 [PROPOSAL.md](PROPOSAL.md).
>
> **작성일:** 2026-07-11 · **대상 저장소:** 이 저장소(Clean Architecture MCP 템플릿, 데모 도메인 `note` 포함)

---

## 0. 무엇을 만드는가 (기획의도 요약)

사용자의 짧고 모호한 요청("메신저 만들어줘")을 **구현 가능한 MVP 프로젝트 명세(Specification)**
로 변환하는 MCP 서버. 답을 대신 생성하는 것이 아니라, **LLM보다 먼저 생각하는 PM** 역할을 한다.

PROPOSAL.md의 9단계가 곧 도메인이다:
① 프로젝트 분류 → ② 도메인 템플릿 → ③ 요구사항 분석 → ④ 부족한 정보 식별 → ⑤ 추가 질문
→ ⑥ MVP 범위 제한 → ⑦ 기술 스택 → ⑧ 산출물 형식 → ⑨ 품질 검증

**핵심 설계 판단 — 역할 분담.** MCP 서버는 추론하지 못한다. 따라서:

- **서버가 소유(결정적):** 유형별 템플릿(기능 포함/제외), 필수 필드 검사, 질문 뱅크, 기본
  기술 스택, 11섹션 출력 형식, 품질 체크리스트, 명세 초안(상태).
- **클라이언트 LLM이 담당(의미 해석):** 요청을 유형으로 분류, 사용자 답변을 필드 값으로 정리,
  최종 컨텍스트에 따라 명세 문서 생성.

기획의 두 축을 코드로 강제한다:
- **"추측해서 결정하지 않는다"** → 필수 필드가 비면 `finalize_spec`이 `PipelineError`로 거부.
- **"MVP 범위를 제한한다"** → `scope_mvp`가 템플릿의 제외 목록 기반으로 기능을 컷.

---

## 1. 절대 규칙 (AGENTS.md 요약 — 위반 시 가드레일 테스트가 실패한다)

1. 계층 방향 단방향: `presentation → data → domain → core`. `domain/`은 `mcp`·
   `pydantic_settings`·DB 드라이버를 import하지 않는다(pydantic은 허용).
2. 의존성 조립은 오직 `main.py::build()`에서만.
3. Tool/Resource 어댑터에 비즈니스 로직 금지 — 검증 → UseCase 호출 → 문자열화만.
4. 로그는 stderr로만(`core/logging.py`). `print()` 금지.
5. 에러 처리는 항상 `@safe_tool`(직접 try/except 금지). 실패 가능 단계는 UseCase의
   `_run_stage`로 감싸 `PipelineError(stage, reason, hint)`로 구조화.
6. 과설계 금지: 구현 하나뿐인 협력자 Port화 금지, 서비스 레이어 추가 금지, 이벤트 버스/CQRS 금지.

**모든 작업 후 통과해야 하는 게이트:**

```bash
uv run ruff check && uv run black --check src tests && uv run mypy src && uv run pytest -q
```

---

## 2. Phase 0 — 프로젝트 개명 (가장 먼저 실행)

동봉 스크립트로 템플릿 이름을 실제 프로젝트 이름으로 치환한다.

```bash
python scripts/rename_project.py mvp --dry-run   # 미리보기
python scripts/rename_project.py mvp             # 실행
uv sync && uv run ruff check --fix && uv run pytest -q
```

결과: 패키지 `src/mvp_mcp/` · 배포명 `mvp-mcp` · 콘솔 스크립트 `mvp-mcp` · 환경변수 접두사
`MVP_` · 서버명 `FastMCP("Mvp")` · 베이스 예외 `MvpError`. **이후 이 문서의 모든 경로·코드는
개명 후 기준(`mvp_mcp`, `MvpError`)으로 표기한다.**

---

## 3. 파일 변경 지도

### 신규 작성 (🆕)

```
src/mvp_mcp/domain/spec/
├── __init__.py
├── model.py            # ProjectType, SpecRequest, Question, DomainTemplate, SpecDraft, FinalSpec
├── templates_data.py   # 유형별 템플릿 데이터 4종 + 질문 뱅크 (순수 데이터, §5)
├── output_format.py    # 11섹션 출력 형식 상수 (§6)
├── repository.py       # SpecRepository, TemplateRepository Protocol
├── ports.py            # Clock Protocol (note의 것을 이동/재사용)
├── usecase.py          # StartSpec / AnswerQuestion / ScopeMvp / FinalizeSpec (쓰기)
├── query.py            # GetMissingInfo / GetDraft / ListProjectTypes / GetTemplate (읽기)
└── checklist.py        # ⑨ 품질 체크리스트 판정 함수

src/mvp_mcp/data/spec/
├── __init__.py
├── template_repository_impl.py   # templates_data 를 읽는 InMemoryTemplateRepository
└── spec_repository_impl.py       # InMemorySpecRepository (save가 id 발급)

src/mvp_mcp/presentation/tools/
├── start_spec.py
├── answer_question.py
├── get_missing_info.py
├── scope_mvp.py
└── finalize_spec.py

src/mvp_mcp/presentation/resources/spec.py    # spec://project-types, templates/{type}, drafts/{id}
src/mvp_mcp/presentation/prompts/workflow.py  # mvp_spec_workflow 프롬프트

tests/test_spec.py       # 유스케이스 테스트 (§9 시나리오)
```

### 수정 (✏️)

| 파일 | 변경 |
|---|---|
| `src/mvp_mcp/main.py` | note 조립 제거 → spec 조립(§8) |
| `tests/test_guardrails.py` | `EXPECTED_TOOLS = {"start_spec", "answer_question", "get_missing_info", "scope_mvp", "finalize_spec"}` |
| `pyproject.toml` | import-linter 계약에 도메인 경로 변화가 있으면 반영(레이어명 기준이면 무변경) |

### 삭제 (🗑️)

`domain/note/` 전체 · `data/note/` 전체 · `presentation/tools/create_note.py`,
`search_note.py` · `presentation/resources/notes.py` · `presentation/prompts/template.py` ·
`tests/test_note.py` · `core/security.py`(파일 I/O 없음) · `domain/note/hashing.py`(재현성 해시 불필요).
`test_scaffolding.py`·`test_adapters.py`·`test_guardrails.py`는 **유지**(도메인 무관 가드레일).

---

## 4. 도메인 모델 명세 — `domain/spec/model.py`

기존 `note/model.py`의 스타일(Pydantic, `from __future__ import annotations`)을 따른다.

```python
class ProjectType(str, Enum):
    MESSENGER = "messenger"
    SHOPPING_MALL = "shopping_mall"
    BLOG = "blog"
    ETC = "etc"                      # 폴백: 미지원 유형은 전부 여기로

class SpecRequest(BaseModel):
    """start_spec 입력 검증."""
    project_type: ProjectType
    user_request: str = Field(min_length=1, description="사용자의 원문 요청")
    known_info: dict[str, str] = Field(default_factory=dict,
        description="LLM이 요청에서 이미 추출한 필드값 (예: {'platform': '모바일'})")

class Question(BaseModel):
    field: str                       # 답이 저장될 필드 키
    text: str                        # 사용자에게 물을 문구
    options: list[str] = []          # 보기(있으면 객관식으로 제시)

class DomainTemplate(BaseModel):
    type: ProjectType
    display_name: str
    core_features: list[str]         # ⑥ MVP 포함 기능
    excluded_features: list[str]     # ⑥ MVP 제외 기능(확장 계획으로 이동)
    default_stack: dict[str, str]    # ⑦ 기본 기술 스택
    required_fields: list[str]       # ④ 필수 정보 키 목록

class SpecDraft(BaseModel):
    """진행 중 명세 초안(엔티티). 서버가 소유하는 상태."""
    id: str | None = None
    project_type: ProjectType
    user_request: str
    answers: dict[str, str] = {}             # field → 답변
    features: list[str] = []                 # 확정된 MVP 기능
    deferred: list[str] = []                 # 컷된 기능(사유 포함 "기능 — 사유" 형식)
    tech_stack: dict[str, str] = {}
    status: Literal["collecting", "scoped", "finalized"] = "collecting"
    created_at: datetime | None = None

class FinalSpec(BaseModel):
    """finalize 결과: LLM에게 전달할 최종 컨텍스트."""
    draft: SpecDraft
    context: str                     # §6 형식으로 렌더링된 마크다운
```

**필수 필드(공통, PROPOSAL ④⑤ 기반) — 모든 유형에 적용:**

| field | 질문 | options |
|---|---|---|
| `platform` | 어떤 플랫폼인가요? | 웹, 모바일, 둘 다 |
| `purpose` | 개발 목적은 무엇인가요? | 개인 프로젝트, 회사 프로젝트, 포트폴리오, 상용 서비스 |
| `duration` | 예상 개발 기간은? | 1주, 2주, 1개월, 3개월 이상 |
| `team` | 혼자 개발하시나요, 팀인가요? | 혼자, 팀 |
| `tech_stack` | 정해둔 기술 스택이 있나요? | 기본 스택 사용, 직접 지정 |
| `auth_method` | 로그인 방식은? | 이메일/비밀번호, 소셜 로그인, 없음 |
| `realtime` | 실시간 기능이 필요한가요? | 필요, 불필요 |

질문 뱅크는 `templates_data.py`에 `QUESTION_BANK: dict[str, Question]`으로 둔다.
질문은 **미충족 필드에 대해서만** 반환한다(질문 최소화 원칙).

---

## 5. 템플릿 데이터 — `domain/spec/templates_data.py`

순수 데이터 모듈(로직 없음). PROPOSAL의 예시를 그대로 데이터화. **유형 추가는 이 파일에
항목만 추가하면 되도록** 유지한다.

```python
DEFAULT_STACK = {
    "frontend": "Flutter", "backend": "FastAPI", "database": "PostgreSQL",
    "orm": "SQLAlchemy", "auth": "JWT", "storage": "Supabase Storage",
    "deployment": "Docker",
}
# 규칙: platform 답변이 "웹"이면 frontend 를 "React (Next.js)" 로 치환 (FinalizeSpecUseCase 에서).

TEMPLATES: dict[ProjectType, DomainTemplate] = {
    ProjectType.MESSENGER: DomainTemplate(
        type=ProjectType.MESSENGER, display_name="메신저",
        core_features=["회원가입", "로그인", "친구목록", "채팅방", "1:1 채팅", "메시지 저장", "채팅목록", "알림"],
        excluded_features=["영상통화", "음성통화", "AI 번역", "AI 요약", "커뮤니티", "채널", "라이브", "이모티콘 스토어"],
        default_stack=DEFAULT_STACK, required_fields=[...공통 7개...],
    ),
    ProjectType.SHOPPING_MALL: DomainTemplate(
        ..., display_name="쇼핑몰",
        core_features=["회원가입", "로그인", "상품목록", "상품상세", "장바구니", "주문", "결제", "마이페이지"],
        excluded_features=["상품 리뷰", "쿠폰/포인트", "추천 알고리즘", "판매자 입점", "실시간 상담", "정기구독"],
        ...,
    ),
    ProjectType.BLOG: DomainTemplate(
        ..., display_name="블로그",
        core_features=["게시글 작성/조회", "댓글", "카테고리", "검색", "관리자"],
        excluded_features=["뉴스레터", "유료 멤버십", "통계 대시보드", "다중 작성자 권한", "SEO 고급 기능"],
        ...,
    ),
    ProjectType.ETC: DomainTemplate(
        ..., display_name="기타",
        core_features=[],            # LLM이 요청에서 뽑은 기능을 scope_mvp 로 제안 → 최대 7개 승인
        excluded_features=[],
        ...,
    ),
}
```

---

## 6. 출력 형식 — `domain/spec/output_format.py`

PROPOSAL ⑧의 11섹션을 상수로 고정. `FinalizeSpecUseCase`가 이 순서로 최종 컨텍스트를
렌더링한다.

```python
OUTPUT_SECTIONS = (
    "1. 프로젝트 개요", "2. 요구사항", "3. 핵심 기능", "4. 화면 목록", "5. 사용자 플로우",
    "6. DB 설계", "7. API 설계", "8. 폴더 구조", "9. 개발 일정", "10. 구현 순서",
    "11. 이후 확장 계획",
)
```

최종 컨텍스트(마크다운)의 구성 — 서버가 채울 수 있는 것은 채우고(1~3, 11의 재료, 스택,
제약), 나머지 섹션은 **LLM에게 내리는 작성 지시**로 채운다:

```
# MVP 프로젝트 명세 컨텍스트
## 확정 정보
- 프로젝트 유형 / 원문 요청 / 플랫폼 / 목적 / 기간 / 팀 / 인증 / 실시간 / 기술 스택(표)
## MVP 범위 (이 목록을 벗어난 기능을 추가하지 말 것)
- 포함: {features}
- 제외(11번 확장 계획에만 언급): {deferred}
## 출력 지시
아래 11개 섹션을 이 순서 그대로 작성하라. 6·7번은 테이블/엔드포인트 목록으로 구체화하라.
{OUTPUT_SECTIONS 나열}
## 제약
- 위 MVP 범위의 기능만 설계한다. 정보를 추측으로 채우지 않는다.
- 일정은 {duration}·{team} 기준으로 현실적으로 배분한다.
```

---

## 7. UseCase 명세 — `domain/spec/usecase.py` · `query.py` · `checklist.py`

모든 협력자는 생성자 주입. 실패 가능 단계는 `note/usecase.py`의 `_run_stage` 패턴을 그대로
복제(staticmethod 포함)한다.

| UseCase | 시그니처 | 동작 |
|---|---|---|
| `StartSpecUseCase(template_repo, spec_repo, clock)` | `__call__(request: SpecRequest) -> tuple[SpecDraft, list[Question]]` | 템플릿 조회(stage `"template"`) → `known_info` 중 required_fields에 해당하는 것만 answers로 채택 → 초안 생성·저장(stage `"persist"`, save가 id 발급) → 미충족 필드의 질문 목록 반환 |
| `AnswerQuestionUseCase(spec_repo, template_repo)` | `__call__(spec_id, field, value) -> tuple[SpecDraft, list[Question]]` | 초안 조회(없으면 stage `"load"` 실패) → field가 required_fields에 없으면 stage `"validate"` 실패 → 저장 → 남은 질문 반환 |
| `ScopeMvpUseCase(spec_repo, template_repo)` | `__call__(spec_id, requested: list[str]) -> SpecDraft` | ⑥ 범위 판정: 요청 기능을 core(포함)/excluded(컷+사유)/미등재(컷, "MVP 이후 검토")로 분류. `features = core_features ∪ (요청∩core)`, 컷은 `deferred`에. ETC 유형은 요청 기능 중 최대 7개를 features로 승인, 초과분은 deferred. status → `"scoped"` |
| `FinalizeSpecUseCase(spec_repo, template_repo)` | `__call__(spec_id) -> FinalSpec` | `checklist.validate(draft, template)` 실행 → 미통과 항목이 있으면 stage `"checklist"` `PipelineError`(reason에 미통과 항목, hint에 다음 행동) → 통과 시 스택 확정(tech_stack 답변 "직접 지정"이면 answers의 값 사용, platform="웹"이면 frontend 치환) → §6 컨텍스트 렌더링 → status `"finalized"` |

`query.py` (읽기 전용, 실패 구조화 불필요한 단순 조회):
`GetMissingInfoUseCase` · `GetDraftUseCase` · `ListProjectTypesUseCase` · `GetTemplateUseCase`.

`checklist.py` — ⑨를 코드로. `validate(draft, template) -> list[str]` (미통과 항목 반환):

| 검사 | 판정 |
|---|---|
| 요구사항 누락 없음 | required_fields ⊆ answers.keys() |
| MVP 범위 확정됨 | status == "scoped" (scope_mvp 미실행 시 미통과) |
| 범위 초과 없음 | features 중 excluded_features 교집합 없음 |
| 일정 현실성 | duration이 "1주"인데 features > 5개면 경고 항목 추가(차단은 아님 — 컨텍스트의 제약에 명시) |

---

## 8. Presentation + 조립 명세

### Tool 어댑터 (5개 — 전부 아래 골격, `@safe_tool` 필수)

```python
# presentation/tools/start_spec.py  — 나머지 4개도 동일 골격
from mcp.server.fastmcp import FastMCP
from mvp_mcp.domain.spec.model import ProjectType, SpecRequest
from mvp_mcp.domain.spec.usecase import StartSpecUseCase
from mvp_mcp.presentation._safe import safe_tool

def register_start_spec_tool(mcp: FastMCP, use_case: StartSpecUseCase) -> None:
    @mcp.tool()
    @safe_tool
    def start_spec(project_type: str, user_request: str,
                   known_info: dict[str, str] | None = None) -> str:
        """MVP 명세 세션을 시작한다. 유형 템플릿을 적용하고 부족한 정보의 질문을 돌려준다."""
        request = SpecRequest(project_type=ProjectType(project_type),
                              user_request=user_request, known_info=known_info or {})
        draft, questions = use_case(request)
        return _format(draft, questions)   # 사람이 읽을 문자열(질문은 번호+보기 나열)
```

| Tool | 파라미터 | 반환(문자열 내용) |
|---|---|---|
| `start_spec` | `project_type, user_request, known_info?` | spec_id + 적용된 템플릿 요약 + **남은 질문 목록** |
| `answer_question` | `spec_id, field, value` | 반영 결과 + 남은 질문(없으면 "scope_mvp를 호출하세요") |
| `get_missing_info` | `spec_id` | 미충족 필드 + 질문 재조회 |
| `scope_mvp` | `spec_id, requested_features?` (list[str]) | 확정 포함 기능 / 컷된 기능+사유 |
| `finalize_spec` | `spec_id` | 통과 시 **최종 컨텍스트 전문**, 미통과 시 `@safe_tool`이 미통과 항목 안내 |

### Resources — `presentation/resources/spec.py`

```python
@mcp.resource("spec://project-types")      # 유형 목록 + display_name + 한 줄 판별 기준 (JSON)
@mcp.resource("spec://templates/{type}")   # 해당 유형 DomainTemplate 직렬화 (JSON)
@mcp.resource("spec://drafts/{spec_id}")   # 초안 현재 상태 (JSON)
```

### Prompt — `presentation/prompts/workflow.py`

`mvp_spec_workflow` 프롬프트 본문(요지 — 이 문구가 산출물 품질을 좌우하므로 그대로 담을 것):

> 너는 MVP 설계 PM 도구를 사용한다. 사용자가 프로젝트 요청을 하면:
> 1. `spec://project-types`를 보고 유형을 하나 고른다(애매하면 `etc`).
> 2. 요청에서 이미 알 수 있는 필드만 `known_info`로 담아 `start_spec`을 호출한다.
>    **모르는 값을 추측해 채우지 마라.**
> 3. 반환된 질문을 사용자에게 **그대로, 한 번에** 묻고, 답을 `answer_question`으로 반영한다.
> 4. 질문이 소진되면 사용자가 언급한 기능 목록으로 `scope_mvp`를 호출한다. 컷된 기능을
>    사용자에게 알리되 되살리지 마라.
> 5. `finalize_spec`이 돌려준 컨텍스트의 지시·순서·범위를 **그대로** 따라 명세를 작성한다.
>    컨텍스트에 없는 기능을 추가하지 마라.

### 조립 — `main.py::build()` (전체 교체)

```python
def build() -> FastMCP:
    configure_logging()
    _cfg = Settings()
    # 1. 구현체 (data)
    template_repo = InMemoryTemplateRepository()
    spec_repo = InMemorySpecRepository()
    clock = SystemClock()
    # 2. UseCase (domain)
    start_uc = StartSpecUseCase(template_repo, spec_repo, clock)
    answer_uc = AnswerQuestionUseCase(spec_repo, template_repo)
    scope_uc = ScopeMvpUseCase(spec_repo, template_repo)
    finalize_uc = FinalizeSpecUseCase(spec_repo, template_repo)
    missing_uc = GetMissingInfoUseCase(spec_repo, template_repo)
    draft_uc = GetDraftUseCase(spec_repo)
    types_uc = ListProjectTypesUseCase(template_repo)
    template_uc = GetTemplateUseCase(template_repo)
    # 3. 등록 (presentation)
    mcp = FastMCP("Mvp")
    register_prompts(mcp)
    register_start_spec_tool(mcp, start_uc)
    register_answer_question_tool(mcp, answer_uc)
    register_get_missing_info_tool(mcp, missing_uc)
    register_scope_mvp_tool(mcp, scope_uc)
    register_finalize_spec_tool(mcp, finalize_uc)
    register_resources(mcp, types_uc, template_uc, draft_uc)
    return mcp
```

---

## 9. 테스트 명세 — `tests/test_spec.py`

Port에 테스트 더블 주입(고정 시계 `FixedClock`, 인메모리 저장소는 실제 구현 재사용 가능).
**필수 시나리오 4건:**

1. **행복 경로:** messenger로 start → 질문 7개 반환 → 전부 answer → scope_mvp([]) →
   finalize → 컨텍스트에 11섹션 제목 전부와 "친구목록" 포함, "영상통화"는 확장 언급에만.
2. **추측 금지:** 필드 2개 미답변 상태에서 finalize → `PipelineError` (stage=="checklist",
   reason에 미답변 필드명 포함).
3. **범위 강제:** scope_mvp(["영상통화", "1:1 채팅"]) → features에 "영상통화" 없음,
   deferred에 사유와 함께 존재.
4. **폴백:** etc 유형 + 기능 9개 요청 → 7개만 features, 2개 deferred.

**가드레일 갱신:** `tests/test_guardrails.py`의
`EXPECTED_TOOLS = {"start_spec", "answer_question", "get_missing_info", "scope_mvp", "finalize_spec"}`.

---

## 10. 구현 순서 (커밋 단위)

| # | 작업 | 완료 기준 |
|---|---|---|
| 1 | Phase 0 개명(§2) | `grep -r mvp_mcp src` 없음, 전 게이트 통과 |
| 2 | `domain/spec/` 전체(§4~7) + `tests/test_spec.py` | pytest에서 spec 테스트 4건 통과 (아직 note 공존 OK) |
| 3 | `data/spec/` 구현체 2개 | 유스케이스 테스트가 실제 구현체로도 통과 |
| 4 | `presentation/` 도구 5·리소스·프롬프트 + `main.py` 재조립 + note 삭제(§3 🗑️) + `EXPECTED_TOOLS` 갱신 | 전 게이트 통과 |
| 5 | E2E: Claude Desktop 연동(TEMPLATE.md §5 설정) → "메신저 만들어줘" 전 과정 실측, 프롬프트 문구 튜닝 | 최종 명세가 11섹션·MVP 범위 내로 출력 |

각 단계 후 게이트 실행: `uv run ruff check && uv run black --check src tests && uv run mypy src && uv run pytest -q`

---

## 11. 범위 제한 — 이번 구현에서 하지 않는 것

- 프로젝트 유형 4종 초과(17종 확충은 `templates_data.py`에 데이터 추가만으로 가능하게 유지)
- 초안 영속화(SQLite) — 인메모리로 충분. 필요 시 TEMPLATE.md §8 레시피로 교체
- 명세 파일 내보내기(PDF/MD), 웹 UI, 다국어
- LLM API 직접 호출 — 의미 해석은 전적으로 클라이언트 LLM의 몫(§0 역할 분담)

## 12. 이후 확장 계획

1. 유형 17종 전체 템플릿 확충 → 2. 초안 SQLite 영속화 → 3. 명세 마크다운 내보내기 도구
(파일 I/O 도입 시 `core/security.py` 복원) → 4. 유형별 출력 형식 오버라이드(예: 게임=씬 구성).
