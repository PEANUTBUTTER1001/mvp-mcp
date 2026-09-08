"""프로세스 수명 동안 웹 설문 세션을 보관하는 저장소."""

from __future__ import annotations

import threading

from mvp_mcp.domain.spec.survey import SurveySession


class InMemorySurveySessionRepository:
    """세션별 제출 상태를 동기화해 저장한다."""

    def __init__(self) -> None:
        self._items: dict[str, SurveySession] = {}
        self._lock = threading.Lock()

    def save(self, session: SurveySession) -> None:
        with self._lock:
            self._items[session.id] = session.model_copy(deep=True)

    def find_by_id(self, session_id: str) -> SurveySession | None:
        with self._lock:
            item = self._items.get(session_id)
            return item.model_copy(deep=True) if item is not None else None
