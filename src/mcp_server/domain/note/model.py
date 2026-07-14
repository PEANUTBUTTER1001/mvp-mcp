"""노트 도메인 모델.

입력 경계에서 검증되는 요청 모델(``NoteRequest``)과 저장/조회되는 엔티티(``Note``)를
정의한다. Pydantic 모델이라 프레임워크가 아니라 검증 라이브러리에만 의존한다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NoteRequest(BaseModel):
    """노트 생성 요청(입력 경계 검증용). 공백 제목은 여기서 차단된다."""

    title: str = Field(min_length=1, description="노트 제목")
    body: str = Field(default="", description="노트 본문")


class Note(BaseModel):
    """저장/조회되는 노트 엔티티."""

    id: int | None = None
    title: str
    body: str = ""
    created_at: datetime | None = None
    content_hash: str = ""
