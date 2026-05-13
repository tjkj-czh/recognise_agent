@echo off
setlocal

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%run_on_upload_event.py" %*
exit /b %ERRORLEVEL%
