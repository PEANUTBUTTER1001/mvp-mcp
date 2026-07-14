"""애플리케이션 설정 (Composition Root 주입용).

경로·옵션을 코드에 하드코딩하지 않고 환경변수(``MCPSERVER_*``)에서 주입한다.
기본값은 패키지 위치 기준 프로젝트 루트로 해석한다. ``.env`` 파일도 지원한다.

새 도메인에 필요한 설정(DB 경로·템플릿 경로 등)은 아래 필드에 추가하면 되고,
접두사는 ``env_prefix`` 한 곳만 바꾸면 전체 환경변수 이름이 함께 바뀐다.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트: <root>/src/mcp_server/core/config.py → parents[3] == <root>
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """환경변수 기반 설정. 접두사 ``MCPSERVER_`` 로 오버라이드 가능."""

    model_config = SettingsConfigDict(env_prefix="MCPSERVER_", env_file=".env", extra="ignore")

    output_dir: str = Field(default=str(_PROJECT_ROOT / "output"))
    project_root: str = Field(default=str(_PROJECT_ROOT))

    @model_validator(mode="after")
    def _fail_fast(self) -> Settings:
        """부팅 시점에 설정을 검증한다(첫 도구 호출 대신 여기서 명확히 실패시킨다).

        출력 디렉터리를 미리 생성해 쓰기 가능 여부를 확인한다. 새 필드(DB 경로·템플릿
        경로 등)를 추가하면 여기에 검증을 함께 넣어 조기 실패를 유지한다.
        """
        try:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"출력 디렉터리를 만들 수 없습니다: {self.output_dir} ({exc})"
            raise ValueError(msg) from exc
        return self
