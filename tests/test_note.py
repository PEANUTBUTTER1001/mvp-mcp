"""노트 도메인 단위/통합 테스트(데모).

인메모리 리포지토리와 고정 시계를 주입해 유스케이스를 프레임워크 없이 검증한다.
새 도메인을 만들 때 이 파일을 참고해 같은 방식(Port에 테스트 더블 주입)으로 테스트한다.
"""

from __future__ import annotations

from datetime import datetime

from mcp_server.data.note.repository_impl import InMemoryNoteRepository
from mcp_server.domain.note.model import NoteRequest
from mcp_server.domain.note.query import SearchNoteUseCase
from mcp_server.domain.note.usecase import CreateNoteUseCase


class _FixedClock:
    """테스트용 고정 시계(재현성 보장)."""

    def now(self) -> datetime:
        return datetime(2026, 1, 1, 0, 0, 0)


def test_create_note_assigns_id_and_hash() -> None:
    repo = InMemoryNoteRepository()
    create = CreateNoteUseCase(repository=repo, clock=_FixedClock())

    note = create(NoteRequest(title="첫 노트", body="본문"))

    assert note.id == 1
    assert note.content_hash != ""
    assert note.created_at == datetime(2026, 1, 1, 0, 0, 0)


def test_same_input_same_hash() -> None:
    """동일 입력 → 동일 콘텐츠 해시(재현성)."""
    repo = InMemoryNoteRepository()
    create = CreateNoteUseCase(repository=repo, clock=_FixedClock())

    a = create(NoteRequest(title="같은 제목", body="같은 본문"))
    b = create(NoteRequest(title="같은 제목", body="같은 본문"))

    assert a.content_hash == b.content_hash


def test_search_matches_title_substring() -> None:
    repo = InMemoryNoteRepository()
    create = CreateNoteUseCase(repository=repo, clock=_FixedClock())
    create(NoteRequest(title="파이썬 기초"))
    create(NoteRequest(title="자바 기초"))

    results = SearchNoteUseCase(repo)("파이썬")

    assert len(results) == 1
    assert results[0].title == "파이썬 기초"
