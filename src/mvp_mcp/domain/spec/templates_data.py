"""유형별 템플릿 데이터(순수 데이터, 로직 없음).

PROPOSAL 의 예시를 그대로 데이터화한다. **유형 추가는 이 파일에 항목만 추가하면
되도록** 유지한다(코드 변경 없이 데이터 확충).
"""

from __future__ import annotations

from .model import DomainTemplate, ProjectType
from .template_sections import (
    DATA_GUIDE,
    DATA_SECTIONS,
    DEV_GUIDE,
    DEV_SECTIONS,
    ML_GUIDE,
    ML_SECTIONS,
)

# 기존 유형 분류에 사용하는 기본 기술 스택.
DEFAULT_STACK: dict[str, str] = {
    "frontend": "Flutter",
    "backend": "FastAPI",
    "database": "PostgreSQL",
    "orm": "SQLAlchemy",
    "auth": "JWT",
    "storage": "Supabase Storage",
    "deployment": "Docker",
}

# Android/iOS 앱의 기본 권장안. 사용자가 스택을 확정하지 않은 경우에만 사용한다.
MOBILE_STACK: dict[str, str] = {
    "platform": "Android",
    "language": "Kotlin",
    "ui": "Jetpack Compose / Material 3",
    "build": "Gradle",
    "testing": "JUnit + Compose UI Test",
}

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
    ProjectType.MOBILE_APP: DomainTemplate(
        type=ProjectType.MOBILE_APP,
        display_name="모바일 앱",
        core_features=[
            "앱 시작과 초기 상태",
            "핵심 사용자 흐름",
            "입력·오류 상태 처리",
            "접근성·화면 크기 대응",
            "기기별 권한·설정 처리",
        ],
        excluded_features=[
            "iOS 동시 지원",
            "오프라인 동기화",
            "푸시 알림",
            "앱 내 결제",
            "다국어 지원",
        ],
        default_stack=MOBILE_STACK,
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
        # 요청 기능은 MVP 범위 판정에서 최대 7개 승인.
        core_features=[],
        excluded_features=[],
        default_stack=DEFAULT_STACK,
        required_fields=list(COMMON_REQUIRED_FIELDS),
    ),
}

# ETC 유형에서 MVP 범위 판정이 승인하는 최대 기능 수.
ETC_MAX_FEATURES = 7
