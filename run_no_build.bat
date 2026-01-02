@echo off
REM Run Docker helper using existing image (no build). For PowerShell execution policy bypass.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_in_docker.ps1" --no-build %*
