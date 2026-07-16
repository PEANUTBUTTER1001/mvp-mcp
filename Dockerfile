# [선택사항] Clean Architecture MCP 서버 템플릿 — 최소 실행 이미지.
#
# 이 Dockerfile 은 필수가 아니다. 서버는 Docker 없이 `uv run mvp-mcp` 로 바로 실행된다.
# 컨테이너 배포·환경 일관성이 필요할 때만 사용하고, 필요 없으면 이 파일을 삭제해도
# 앱 동작에 영향이 없다. 네이티브 의존성(PDF 렌더링 등)을 도입하면 여기에 apt 설치
# 단계를 추가한다.
FROM python:3.11-slim

# uv 설치(빠른 의존성 해석·설치).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 메타데이터 먼저 복사해 레이어 캐시 활용.
COPY pyproject.toml README.md ./
COPY src ./src

# 런타임 의존성만 설치(dev 도구 ruff/mypy/pytest 제외 → 이미지 슬림).
RUN uv sync --no-dev

# 콘솔 스크립트를 직접 실행(런타임에 uv 재동기화를 거치지 않아 빠르고 가볍다).
ENTRYPOINT ["/app/.venv/bin/mvp-mcp"]
