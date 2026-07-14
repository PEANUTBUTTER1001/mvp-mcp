"""어댑터 공용 에러 처리(``@safe_tool``) 테스트.

모든 Tool 이 동일하게 따라야 하는 실패 표현 규칙을 고정한다. 새 어댑터도 이 세 갈래
동작을 그대로 물려받는다(개별 try/except 를 작성하지 않는다).
"""

from __future__ import annotations

from mcp_server.core.exceptions import PipelineError
from mcp_server.domain.note.model import NoteRequest
from mcp_server.presentation._safe import safe_tool


def test_happy_path_passes_through() -> None:
    @safe_tool
    def ok() -> str:
        return "성공"

    assert ok() == "성공"


def test_validation_error_becomes_input_message() -> None:
    @safe_tool
    def bad_input() -> str:
        NoteRequest(title="")  # min_length=1 위반 → ValidationError
        return "도달 불가"

    assert "입력이 올바르지 않습니다" in bad_input()


def test_pipeline_error_shows_stage_and_hint() -> None:
    @safe_tool
    def fails() -> str:
        raise PipelineError("persist", "디스크 부족", "공간을 확보하세요")

    out = fails()
    assert "[persist]" in out
    assert "힌트" in out


def test_unexpected_error_is_absorbed_safely() -> None:
    @safe_tool
    def boom() -> str:
        raise RuntimeError("예상 못한 오류")

    assert "내부 오류" in boom()
