"""어댑터 공용 에러 처리 (모든 Tool 이 동일 규칙을 따르도록 한 곳에 모음).

Tool 마다 try/except 를 제각각 작성하면 규칙이 갈라져 유지보수 시 빠뜨리기 쉽다.
``@safe_tool`` 하나로 실패 표현을 일원화한다: ``PipelineError`` 는 단계·원인·힌트를
사람이 읽을 메시지로 바꾸고, 예상치 못한 예외는 stderr 로그로 남긴 뒤 안전한 문구를
반환한다(스택트레이스가 프로토콜 응답으로 새지 않게).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar, cast

from pydantic import ValidationError

from mvp_mcp.core.exceptions import PipelineError

_logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., str])
_A = TypeVar("_A", bound=Callable[..., Awaitable[str]])


def _failure_message(tool_name: str, exc: Exception) -> str:
    """모든 Tool 형태가 공유하는 안전한 실패 문자열을 만든다."""
    if isinstance(exc, ValidationError):
        reasons = "; ".join(e["msg"] for e in exc.errors())
        return f"입력이 올바르지 않습니다: {reasons}"
    if isinstance(exc, PipelineError):
        return f"실패 [{exc.stage}] {exc.reason}\n힌트: {exc.hint}"
    _logger.exception("도구 실행 중 예상치 못한 오류: %s", tool_name)
    return "내부 오류로 요청을 처리하지 못했습니다. 서버 로그를 확인하세요."


def safe_tool(fn: _F) -> _F:
    """Tool 함수를 감싸 실패를 일관된 문자열 응답으로 변환한다.

    세 갈래로 나눈다:
    - ``ValidationError``: 사용자 입력이 잘못됨 → 무엇이 문제인지 그대로 안내.
    - ``PipelineError``: 도메인 파이프라인 단계 실패 → 단계·원인·힌트 안내.
    - 그 외 예외: 예상치 못한 오류 → stderr 로그로 남기고 안전한 문구만 반환
      (스택트레이스가 프로토콜 응답으로 새지 않게).
    """

    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> str:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - Tool 경계에서 안전하게 흡수
            return _failure_message(fn.__name__, exc)

    return wrapper  # type: ignore[return-value]


def safe_async_tool(fn: _A) -> _A:
    """비동기 Tool에도 ``safe_tool``과 같은 오류 계약을 적용한다."""

    @wraps(fn)
    async def wrapper(*args: object, **kwargs: object) -> str:
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - Tool 경계에서 안전하게 흡수
            return _failure_message(fn.__name__, exc)

    return cast(_A, wrapper)
