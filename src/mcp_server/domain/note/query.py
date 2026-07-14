"""노트 조회/검색 유스케이스(읽기 전용).

생성 유스케이스와 책임을 분리하여, 검색과 목록/단건 노출(Resource)을 담당한다.
리포지토리 인터페이스(Port)에만 의존한다.
"""

from __future__ import annotations

from .model import Note
from .repository import NoteRepository


class SearchNoteUseCase:
    """제목 부분일치로 노트를 검색한다."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def __call__(self, query: str) -> list[Note]:
        # 공백만 있는 질의는 빈 결과로 단락(전체 노출 방지·불필요한 쿼리 회피).
        normalized = query.strip()
        if not normalized:
            return []
        return self._repo.search(normalized)


class ListNotesUseCase:
    """저장된 모든 노트를 반환한다(Resource 목록 노출용)."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def __call__(self) -> list[Note]:
        return self._repo.list_all()


class GetNoteUseCase:
    """id 로 노트 단건을 조회한다(Resource 단건 노출용)."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def __call__(self, note_id: int) -> Note | None:
        return self._repo.find_by_id(note_id)
