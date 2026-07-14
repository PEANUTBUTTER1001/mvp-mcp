"""인메모리 노트 리포지토리 구현체.

``NoteRepository`` Port 를 프로세스 메모리로 구현한다. MCP 서버는 stdio 세션 동안
하나의 프로세스로 떠 있으므로 세션 내에서는 정상 동작하지만, 서버를 재시작하면
데이터가 사라진다. 영속화가 필요하면 이 파일을 SQLite/파일 구현으로 교체한다
(도메인·유스케이스는 변경 불필요 — Port 만 만족하면 된다).
"""

from __future__ import annotations

from mcp_server.domain.note.model import Note


class InMemoryNoteRepository:
    """프로세스 메모리에 노트를 저장하는 리포지토리."""

    def __init__(self) -> None:
        self._items: dict[int, Note] = {}
        self._seq = 0

    def save(self, note: Note) -> int:
        self._seq += 1
        self._items[self._seq] = note.model_copy(update={"id": self._seq})
        return self._seq

    def list_all(self) -> list[Note]:
        # 최신순(id 내림차순).
        return [self._items[k] for k in sorted(self._items, reverse=True)]

    def find_by_id(self, note_id: int) -> Note | None:
        return self._items.get(note_id)

    def search(self, query: str) -> list[Note]:
        lowered = query.lower()
        return [n for n in self.list_all() if lowered in n.title.lower()]
