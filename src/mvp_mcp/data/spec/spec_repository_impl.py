"""인메모리 명세 초안 리포지토리 구현체.

``SpecRepository`` Port 를 프로세스 메모리로 구현한다. ``save`` 는 id 가 없으면 새
id 를 발급하고, 있으면 해당 초안을 덮어쓴다. MCP 서버는 stdio 세션 동안 하나의
프로세스로 떠 있으므로 세션 내에서는 정상 동작하지만 재시작하면 데이터가 사라진다.
영속화가 필요하면 이 파일을 SQLite 구현으로 교체한다(도메인·유스케이스 불변).
"""

from __future__ import annotations

from mvp_mcp.domain.spec.model import SpecDraft


class InMemorySpecRepository:
    """프로세스 메모리에 명세 초안을 저장하는 리포지토리."""

    def __init__(self) -> None:
        self._items: dict[str, SpecDraft] = {}
        self._seq = 0

    def save(self, draft: SpecDraft) -> str:
        spec_id = draft.id
        if spec_id is None:
            self._seq += 1
            spec_id = f"spec-{self._seq}"
        self._items[spec_id] = draft.model_copy(update={"id": spec_id})
        return spec_id

    def find_by_id(self, spec_id: str) -> SpecDraft | None:
        return self._items.get(spec_id)
