"""경로 관련 보안·입력 정책.

파일 시스템 세부 구현은 data 계층에 두되, 여러 UseCase가 공유하는 경로 입력 검증은
core에 둬 domain이 플랫폼별 경로 API를 직접 해석하지 않게 한다.
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath


def is_absolute_path(value: str) -> bool:
    """POSIX 또는 Windows 문법의 절대 경로인지 OS 독립적으로 확인한다."""
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
