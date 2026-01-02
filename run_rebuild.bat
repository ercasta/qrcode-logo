@echo off
REM Force rebuild of Docker image and run helper. Force template mode by default.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_in_docker.ps1" --rebuild --template /app/template_pure.svg %*
