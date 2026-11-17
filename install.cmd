@echo off
rem mvp-mcp installer for Windows: double-click or run "install.cmd [--dry-run] [--host claude]".
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is not installed. Install it from https://docs.astral.sh/uv/ and run this file again.
  pause
  exit /b 1
)
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
uv run scripts/install.py %*
set "CODE=%ERRORLEVEL%"
pause
exit /b %CODE%
