@echo off
REM Run Docker helper using existing image (no build). Force template mode by default.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_in_docker.ps1" --no-build --template /app/template_pure.svg %*
