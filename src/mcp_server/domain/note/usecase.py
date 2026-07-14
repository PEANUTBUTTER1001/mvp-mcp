"""노트 생성 유스케이스.

단일 책임 원칙에 따라 '콘텐츠 해시 → 시각 결정 → 저장'의 오케스트레이션만 담당한다.
모든 협력자는 생성자에서 인터페이스(Port)로 주입받으며 구현체는 알지 못한다.

각 단계는 ``_run_stage`` 로 감싸 실패 시 ``PipelineError(stage, reason, hint)`` 로
변환한다. 이 패턴은 도메인이 무엇이든 그대로 재사용할 수 있다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from mcp_server.core.exceptions import MCPServerError, PipelineError

from .hashing import compute_content_hash
from .model import Note, NoteRequest
from .ports import Clock
from .repository import NoteRepository

_T = TypeVar("_T")


class CreateNoteUseCase:
    """노트 1건을 생성해 저장한다."""

    def __init__(self, repository: NoteRepository, clock: Clock) -> None:
        self._repo = repository
        self._clock = clock

    def __call__(self, request: NoteRequest) -> Note:
        content_hash = self._run_stage(
            "hash",
            lambda: compute_content_hash(request),
            "요청 필드가 직렬화 가능한지 확인하세요.",
        )
        created_at = self._clock.now()
        note = Note(
            title=request.title,
            body=request.body,
            created_at=created_at,
            content_hash=content_hash,
        )
        new_id = self._run_stage(
            "persist",
            lambda: self._repo.save(note),
            "저장소 연결/쓰기 권한을 확인하세요.",
        )
        return note.model_copy(update={"id": new_id})

    @staticmethod
    def _run_stage(stage: str, action: Callable[[], _T], hint: str) -> _T:
        """단계를 실행하고, 실패 시 단계 정보를 담은 ``PipelineError`` 로 재던진다."""
        try:
            return action()
        except PipelineError:
            raise  # 이미 구조화된 실패는 그대로 전파.
        except MCPServerError as exc:
            raise PipelineError(stage, str(exc), hint) from exc
        except Exception as exc:
            # 어떤 예외든 stage/reason/hint 로 구조화해 전달.
            raise PipelineError(stage, f"{type(exc).__name__}: {exc}", hint) from exc
