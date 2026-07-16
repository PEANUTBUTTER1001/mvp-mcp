"""유형별 템플릿 데이터와 질문 뱅크 (순수 데이터, 로직 없음).

PROPOSAL 의 예시를 그대로 데이터화한다. **유형 추가는 이 파일에 항목만 추가하면
되도록** 유지한다(코드 변경 없이 데이터 확충).
"""

from __future__ import annotations

from .model import DomainTemplate, ProjectType, Question
from .output_format import (
    DATA_GUIDE,
    DATA_SECTIONS,
    DEV_GUIDE,
    DEV_SECTIONS,
    ML_GUIDE,
    ML_SECTIONS,
)

# ⑦ 기본 기술 스택. platform 답변이 "웹"이면 frontend 를 치환(FinalizeSpecUseCase 에서).
DEFAULT_STACK: dict[str, str] = {
    "frontend": "Flutter",
    "backend": "FastAPI",
    "database": "PostgreSQL",
    "orm": "SQLAlchemy",
    "auth": "JWT",
    "storage": "Supabase Storage",
    "deployment": "Docker",
}

# platform 답변이 "웹" 일 때 frontend 대체값.
WEB_FRONTEND = "React (Next.js)"

# 모든 유형 공통 코어 필드. (작업 인원·기간은 묻지 않는다.)
CORE_FIELDS: list[str] = ["purpose", "tech_stack"]

# ④⑤ 앱/웹 유형(messenger·shopping_mall·blog)의 필수 필드.
COMMON_REQUIRED_FIELDS: list[str] = [
    "platform",
    *CORE_FIELDS,
    "auth_method",
    "realtime",
]

# 개발 도구(MCP 서버) 유형의 필수 필드.
DEV_REQUIRED_FIELDS: list[str] = [*CORE_FIELDS, "interface", "runtime", "distribution"]

# ML 프로젝트 유형의 필수 필드.
ML_REQUIRED_FIELDS: list[str] = [*CORE_FIELDS, "data_source", "task_type", "deployment_target"]

# 데이터 파이프라인 유형의 필수 필드.
DATA_REQUIRED_FIELDS: list[str] = [*CORE_FIELDS, "data_source", "deployment_target"]

# 질문 뱅크 — 미충족 필드에 대해서만 반환한다(질문 최소화 원칙).
QUESTION_BANK: dict[str, Question] = {
    "platform": Question(
        field="platform",
        text="어떤 플랫폼인가요?",
        options=["웹", "모바일", "둘 다"],
        description="서비스가 실제로 돌아갈 환경.",
        hint="MVP는 한 플랫폼(웹 또는 모바일)에 집중하는 편이 빠릅니다. '둘 다'는 공수가 커집니다.",
    ),
    "purpose": Question(
        field="purpose",
        text="개발 목적은 무엇인가요?",
        options=["개인 프로젝트", "회사 프로젝트", "포트폴리오", "상용 서비스"],
        description="이 프로젝트를 왜 만드는지.",
        hint="개인/포트폴리오면 범위를 좁게, 상용 서비스면 안정성·보안을 더 챙깁니다.",
    ),
    "tech_stack": Question(
        field="tech_stack",
        text="정해둔 기술 스택이 있나요?",
        options=["기본 스택 사용", "직접 지정"],
        description="스택을 직접 정할지, 유형별 추천 기본값을 쓸지.",
        hint="학습·속도가 우선이면 '기본 스택 사용'을 권장합니다.",
    ),
    "auth_method": Question(
        field="auth_method",
        text="로그인 방식은?",
        options=["이메일/비밀번호", "소셜 로그인", "없음"],
        description="사용자 인증 방식.",
        hint="초기엔 이메일/비밀번호가 단순합니다. 소셜 로그인은 나중에 추가하세요.",
    ),
    "realtime": Question(
        field="realtime",
        text="실시간 기능이 필요한가요?",
        options=["필요", "불필요"],
        description="채팅·알림처럼 즉시 갱신되는 기능의 필요 여부.",
        hint="꼭 필요할 때만 '필요'. 실시간은 구현 난이도를 크게 올립니다.",
    ),
    # 개발 도구(MCP 서버) 유형 질문
    "interface": Question(
        field="interface",
        text="어떤 인터페이스로 제공하나요?",
        options=["MCP 도구", "CLI", "라이브러리 API", "HTTP API"],
        description="도구를 어떤 형태로 노출할지.",
        hint="LLM(Claude 등) 연동이 목적이면 'MCP 도구'가 표준입니다.",
    ),
    "runtime": Question(
        field="runtime",
        text="실행 환경/언어는?",
        options=["Python", "Node.js", "Go", "기타"],
        description="구현 언어와 실행 런타임.",
        hint="MCP·데이터 도구는 생태계가 풍부한 Python이 무난합니다.",
    ),
    "distribution": Question(
        field="distribution",
        text="배포 방식은?",
        options=["PyPI/npm", "Docker", "소스 직접"],
        description="사용자에게 전달·설치되는 방식.",
        hint="초기엔 '소스 직접'이 가장 간단합니다. 패키지 배포는 나중에 자동화하세요.",
    ),
    # ML/데이터 유형 질문
    "data_source": Question(
        field="data_source",
        text="데이터 출처/형태는?",
        options=["CSV/파일", "DB", "API 수집", "스트리밍"],
        description="다룰 데이터가 어디서 어떤 형태로 오는지.",
        hint="처음엔 파일(CSV) 하나로 시작해 파이프라인을 검증하는 편이 빠릅니다.",
    ),
    "task_type": Question(
        field="task_type",
        text="문제 유형은?",
        options=["분류", "회귀", "생성", "추천", "탐색 분석"],
        description="풀려는 머신러닝 문제의 종류.",
        hint="라벨이 있으면 분류/회귀, 없으면 탐색 분석부터 시작하세요.",
    ),
    "deployment_target": Question(
        field="deployment_target",
        text="산출물 형태는?",
        options=["배치 파이프라인", "실시간 API", "노트북 리포트"],
        description="최종 결과물이 어떻게 쓰이는지.",
        hint="MVP는 배치/노트북 리포트가 실시간 API보다 빠르게 검증됩니다.",
    ),
}

# 개발 도구(MCP 서버) 기본 스택.
DEV_STACK: dict[str, str] = {
    "language": "Python",
    "framework": "mcp[cli] (FastMCP)",
    "validation": "Pydantic",
    "packaging": "uv + hatchling",
    "distribution": "PyPI",
    "transport": "stdio",
}

# ML 프로젝트 기본 스택.
ML_STACK: dict[str, str] = {
    "language": "Python",
    "data": "pandas/numpy",
    "ml": "scikit-learn/PyTorch",
    "tracking": "MLflow",
    "notebook": "Jupyter",
    "env": "uv",
}

# 데이터 파이프라인 기본 스택.
DATA_STACK: dict[str, str] = {
    "language": "Python",
    "processing": "pandas/Polars",
    "orchestration": "Prefect/Airflow",
    "storage": "PostgreSQL/Parquet",
    "env": "uv",
    "deployment": "Docker",
}


TEMPLATES: dict[ProjectType, DomainTemplate] = {
    ProjectType.MESSENGER: DomainTemplate(
        type=ProjectType.MESSENGER,
        display_name="메신저",
        core_features=[
            "회원가입",
            "로그인",
            "친구목록",
            "채팅방",
            "1:1 채팅",
            "메시지 저장",
            "채팅목록",
            "알림",
        ],
        excluded_features=[
            "영상통화",
            "음성통화",
            "AI 번역",
            "AI 요약",
            "커뮤니티",
            "채널",
            "라이브",
            "이모티콘 스토어",
        ],
        default_stack=DEFAULT_STACK,
        required_fields=list(COMMON_REQUIRED_FIELDS),
    ),
    ProjectType.SHOPPING_MALL: DomainTemplate(
        type=ProjectType.SHOPPING_MALL,
        display_name="쇼핑몰",
        core_features=[
            "회원가입",
            "로그인",
            "상품목록",
            "상품상세",
            "장바구니",
            "주문",
            "결제",
            "마이페이지",
        ],
        excluded_features=[
            "상품 리뷰",
            "쿠폰/포인트",
            "추천 알고리즘",
            "판매자 입점",
            "실시간 상담",
            "정기구독",
        ],
        default_stack=DEFAULT_STACK,
        required_fields=list(COMMON_REQUIRED_FIELDS),
    ),
    ProjectType.BLOG: DomainTemplate(
        type=ProjectType.BLOG,
        display_name="블로그",
        core_features=[
            "게시글 작성/조회",
            "댓글",
            "카테고리",
            "검색",
            "관리자",
        ],
        excluded_features=[
            "뉴스레터",
            "유료 멤버십",
            "통계 대시보드",
            "다중 작성자 권한",
            "SEO 고급 기능",
        ],
        default_stack=DEFAULT_STACK,
        required_fields=list(COMMON_REQUIRED_FIELDS),
    ),
    ProjectType.MCP_SERVER: DomainTemplate(
        type=ProjectType.MCP_SERVER,
        display_name="MCP 서버",
        core_features=[
            "도구(Tool) 정의",
            "리소스(Resource) 노출",
            "프롬프트(Prompt) 제공",
            "입력 검증",
            "에러 처리",
            "설정 로딩",
        ],
        excluded_features=[
            "인증/권한",
            "다중 전송(SSE/HTTP)",
            "영속 저장소",
            "관측성/메트릭",
            "레이트 리미팅",
        ],
        default_stack=DEV_STACK,
        required_fields=list(DEV_REQUIRED_FIELDS),
        output_sections=DEV_SECTIONS,
        output_guide=DEV_GUIDE,
    ),
    ProjectType.ML_PROJECT: DomainTemplate(
        type=ProjectType.ML_PROJECT,
        display_name="ML 프로젝트",
        core_features=[
            "데이터 로딩",
            "전처리",
            "피처 엔지니어링",
            "베이스라인 모델",
            "평가",
            "실험 로깅",
        ],
        excluded_features=[
            "하이퍼파라미터 자동탐색",
            "분산 학습",
            "모델 서빙 API",
            "A/B 테스트",
            "피처 스토어",
        ],
        default_stack=ML_STACK,
        required_fields=list(ML_REQUIRED_FIELDS),
        output_sections=ML_SECTIONS,
        output_guide=ML_GUIDE,
    ),
    ProjectType.DATA_PIPELINE: DomainTemplate(
        type=ProjectType.DATA_PIPELINE,
        display_name="데이터 파이프라인",
        core_features=[
            "데이터 수집",
            "정제/변환",
            "적재",
            "스케줄링",
            "실패 재시도",
            "로깅",
        ],
        excluded_features=[
            "실시간 스트리밍",
            "데이터 카탈로그",
            "리니지 추적",
            "자동 스케일링",
            "품질 대시보드",
        ],
        default_stack=DATA_STACK,
        required_fields=list(DATA_REQUIRED_FIELDS),
        output_sections=DATA_SECTIONS,
        output_guide=DATA_GUIDE,
    ),
    ProjectType.ETC: DomainTemplate(
        type=ProjectType.ETC,
        display_name="기타",
        # LLM 이 요청에서 뽑은 기능을 scope_mvp 로 제안 → 최대 7개 승인.
        core_features=[],
        excluded_features=[],
        default_stack=DEFAULT_STACK,
        required_fields=list(COMMON_REQUIRED_FIELDS),
    ),
}

# ETC 유형에서 scope_mvp 가 승인하는 최대 기능 수.
ETC_MAX_FEATURES = 7
