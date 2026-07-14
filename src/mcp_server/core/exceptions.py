"""프로젝트 공통 예외.

실패를 조용히 넘기지 않고 명시적 예외로 중단한다. ``PipelineError`` 는 어느 단계에서
왜 실패했고 사용자가 무엇을 하면 되는지를 구조화해, MCP 클라이언트(예: Claude)에게
설명 가능한 실패로 되돌려주는 데 쓴다.
"""

from __future__ import annotations


class MCPServerError(Exception):
    """도메인 공통 베이스 예외."""


class PipelineError(MCPServerError):
    """유스케이스 파이프라인의 특정 단계에서 실패했을 때 발생.

    어떤 단계(stage)에서, 왜 실패했고(reason), 사용자가 무엇을 하면 되는지(hint)를
    구조화해 담는다. Presentation 어댑터는 이 정보를 그대로 메시지로 변환해 반환한다.
    """

    def __init__(self, stage: str, reason: str, hint: str = "") -> None:
        self.stage = stage
        self.reason = reason
        self.hint = hint
        super().__init__(f"[{stage}] {reason}")
