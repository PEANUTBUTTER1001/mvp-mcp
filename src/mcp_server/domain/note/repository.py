"""노트 영속화 인터페이스.

구조적 타이핑(``Protocol``)으로 정의하여 Domain 이 특정 저장소/ORM 구현에 의존하지
않도록 한다. 구현체는 ``data`` 레이어의 ``InMemoryNoteRepository`` 가 담당하며,
SQLite/파일 등으로 교체해도 도메인은 그대로다.
"""

from __future__ import annotations

from typing import Protocol

from .model import Note


class NoteRepository(Protocol):
    """노트를 저장/조회한다."""

    def save(self, note: Note) -> int:
        """노트를 저장하고 새로 부여된 id 를 반환한다."""
        ...

    def list_all(self) -> list[Note]:
        """저장된 모든 노트를 반환한다."""
        ...

    def find_by_id(self, note_id: int) -> Note | None:
        """id 로 노트 단건을 조회한다. 없으면 ``None``."""
        ...

    def search(self, query: str) -> list[Note]:
        """제목에 ``query`` 가 포함된 노트를 최신순으로 검색한다."""
        ...
