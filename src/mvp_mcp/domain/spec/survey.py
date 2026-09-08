"""비차단 웹 설문 세션 모델."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .model import WebSurveyAnswer


class SurveySession(BaseModel):
    """브라우저 제출과 MCP 재개 사이를 잇는 단기 세션."""

    id: str = Field(min_length=1)
    user_request: str = Field(min_length=1)
    project_root: str = Field(min_length=1)
    status: Literal["open", "submitted", "consumed", "expired"] = "open"
    expires_at: datetime
    answer: WebSurveyAnswer | None = None
