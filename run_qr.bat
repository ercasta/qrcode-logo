@echo off
REM Launcher for qrcode_plain.py using the project's virtualenv Python
SET SCRIPT_DIR=%~dp0
if /I "%~1"=="sheet" (
	shift
	"%SCRIPT_DIR%cqr_env\Scripts\python.exe" "%SCRIPT_DIR%generate_qr_sheet.py" %*
	exit /b %ERRORLEVEL%
)

"%SCRIPT_DIR%cqr_env\Scripts\python.exe" "%SCRIPT_DIR%qrcode_plain.py" %*
exit /b %ERRORLEVEL%
