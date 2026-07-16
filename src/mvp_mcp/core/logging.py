"""로깅 설정 (stdio MCP 서버의 필수 규칙).

**중요:** stdio 전송에서 stdout 은 JSON-RPC 프로토콜 전용 채널이다. 로그를 stdout 으로
보내면 프로토콜이 오염되어 클라이언트 연결이 깨진다. 따라서 모든 로그는 **stderr** 로만
내보낸다. 각 모듈은 ``logging.getLogger(__name__)`` 로 로거를 얻어 쓴다.
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """루트 로거를 stderr 핸들러로 1회 구성한다(중복 호출은 무시)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)  # ← 반드시 stderr (stdout 금지)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _CONFIGURED = True
