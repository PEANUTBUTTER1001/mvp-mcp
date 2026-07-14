"""노트 목록/단건 MCP Resource 어댑터 (얇은 어댑터).

``note://notes`` (목록)와 ``note://notes/{id}`` (단건) Resource 로 노출한다. 비즈니스
로직 없이 UseCase 로 위임하고, 결과를 JSON 문자열로 직렬화해 반환한다.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mcp_server.domain.note.model import Note
from mcp_server.domain.note.query import GetNoteUseCase, ListNotesUseCase


def _to_dict(note: Note) -> dict[str, object]:
    """도메인 엔티티를 JSON 직렬화 가능한 딕셔너리로 변환한다."""
    return {
        "id": note.id,
        "title": note.title,
        "body": note.body,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "content_hash": note.content_hash,
    }


def register_resources(
    mcp: FastMCP,
    list_use_case: ListNotesUseCase,
    get_use_case: GetNoteUseCase,
) -> None:
    """노트 Resource(목록/단건)를 MCP 서버에 등록한다."""

    @mcp.resource("note://notes")
    def list_notes_resource() -> str:
        """저장된 모든 노트를 JSON 배열로 반환한다."""
        notes = list_use_case()
        return json.dumps([_to_dict(n) for n in notes], ensure_ascii=False, indent=2)

    @mcp.resource("note://notes/{note_id}")
    def get_note_resource(note_id: str) -> str:
        """id 로 노트 단건을 JSON 으로 반환한다. 없으면 ``{}`` (예외 없이 빈 객체)."""
        try:
            parsed = int(note_id)
        except ValueError:
            return json.dumps({"error": f"유효하지 않은 노트 id: {note_id}"}, ensure_ascii=False)
        note = get_use_case(parsed)
        if note is None:
            return json.dumps({}, ensure_ascii=False)
        return json.dumps(_to_dict(note), ensure_ascii=False, indent=2)
