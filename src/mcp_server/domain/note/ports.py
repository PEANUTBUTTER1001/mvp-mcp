"""도메인이 의존하는 외부 협력자(Port) 인터페이스.

Domain 은 파일시스템/시계/네트워크를 직접 알지 못한다. UseCase 는 여기 정의된
``Protocol`` 에만 의존하고, 실제 구현체는 ``data`` 레이어에 두며 ``main.py``
(Composition Root)에서 주입한다.

새 협력자(렌더러·HTTP 클라이언트·외부 API 등)가 필요하면 여기에 ``Protocol`` 을
추가하고 ``data`` 에 구현체를 만든 뒤 ``main.py`` 에서 주입한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """현재 시각을 제공하는 시계(비결정성 격리·테스트 고정용 Port)."""

    def now(self) -> datetime:
        """현재 시각을 반환한다."""
        ...
