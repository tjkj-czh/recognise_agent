@echo off
cd /d "%~dp0"

echo ========================================
echo   Landuse Agent Launcher
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python and add it to system PATH.
    pause
    exit /b 1
)

python launcher.py start
if errorlevel 1 (
    echo [ERROR] Failed to start agent.
    pause
    exit /b 1
)

echo.
echo Press any key to close this window...
pause >nul
