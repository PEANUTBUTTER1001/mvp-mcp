"""MVP 명세 도메인 모델.

입력 경계에서 검증되는 요청 모델과, 서버가 소유하는 상태 엔티티(``SpecDraft``)를
정의한다. Pydantic 모델이라 프레임워크가 아니라 검증 라이브러리에만 의존한다.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ProjectType(StrEnum):
    """지원 프로젝트 유형. 미지원 요청은 ``ETC`` 로 폴백한다."""

    MESSENGER = "messenger"
    SHOPPING_MALL = "shopping_mall"
    BLOG = "blog"
    MCP_SERVER = "mcp_server"
    ML_PROJECT = "ml_project"
    DATA_PIPELINE = "data_pipeline"
    ETC = "etc"

    @classmethod
    def coerce(cls, value: str | None) -> ProjectType:
        """문자열을 유형으로 변환한다. 비거나 미지원 값이면 ``ETC`` 로 폴백한다.

        LLM 이 임의의 유형 문자열(예: "mcp-server")을 넘기거나 값을 생략해도
        크래시 대신 ``ETC`` 로 흡수한다(기획: "미지원 유형은 전부 기타로").
        """
        if not value:
            return cls.ETC
        try:
            return cls(value.strip().lower())
        except ValueError:
            return cls.ETC


class SpecRequest(BaseModel):
    """``start_spec`` 입력 검증."""

    project_type: ProjectType
    user_request: str = Field(min_length=1, description="사용자의 원문 요청")
    known_info: dict[str, str] = Field(
        default_factory=dict,
        description="LLM 이 요청에서 이미 추출한 필드값 (예: {'platform': '모바일'})",
    )


class Question(BaseModel):
    """미충족 필드에 대해 사용자에게 물을 질문."""

    field: str = Field(description="답이 저장될 필드 키")
    text: str = Field(description="사용자에게 물을 문구")
    options: list[str] = Field(default_factory=list, description="보기(있으면 객관식)")
    description: str = Field(default="", description="이 항목이 무엇인지 한 줄 설명")
    hint: str = Field(default="", description="어떤 선택이 좋은지 안내하는 힌트")


class DomainTemplate(BaseModel):
    """유형별 MVP 템플릿(서버가 소유하는 결정적 데이터)."""

    type: ProjectType
    display_name: str
    core_features: list[str] = Field(description="MVP 포함 기능")
    excluded_features: list[str] = Field(description="MVP 제외 기능(확장 계획으로 이동)")
    default_stack: dict[str, str] = Field(description="기본 기술 스택")
    required_fields: list[str] = Field(description="필수 정보 키 목록")
    # 유형별 출력 형식 오버라이드. None 이면 앱용 기본 11섹션을 쓴다.
    output_sections: list[str] | None = Field(
        default=None, description="산출물 섹션 순서(유형별 오버라이드)"
    )
    output_guide: dict[str, str] | None = Field(
        default=None, description="섹션별 작성 지침(유형별 오버라이드)"
    )


class SpecDraft(BaseModel):
    """진행 중 명세 초안(엔티티). 서버가 소유하는 상태."""

    id: str | None = None
    project_type: ProjectType
    user_request: str
    answers: dict[str, str] = Field(default_factory=dict, description="field → 답변")
    features: list[str] = Field(default_factory=list, description="확정된 MVP 기능")
    deferred: list[str] = Field(default_factory=list, description="컷된 기능('기능 — 사유' 형식)")
    tech_stack: dict[str, str] = Field(default_factory=dict)
    status: Literal["collecting", "scoped", "finalized"] = "collecting"
    created_at: datetime | None = None


class FinalSpec(BaseModel):
    """finalize 결과: LLM 에게 전달할 최종 컨텍스트."""

    draft: SpecDraft
    context: str = Field(description="출력 형식으로 렌더링된 마크다운 컨텍스트")
