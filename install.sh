#!/usr/bin/env sh
# mvp-mcp 설치(macOS·Linux·Git Bash): ./install.sh [--dry-run] [--host claude]
set -e
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv가 없습니다. https://docs.astral.sh/uv/ 에서 설치한 뒤 다시 실행하세요." >&2
  exit 1
fi
export PYTHONIOENCODING=utf-8
exec uv run scripts/install.py "$@"
