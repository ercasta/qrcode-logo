@echo off
REM Force rebuild of Docker image and run helper.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_in_docker.ps1" --rebuild %*
