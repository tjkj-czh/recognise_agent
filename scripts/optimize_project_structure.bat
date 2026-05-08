@echo off
setlocal
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."

echo [INFO] 正在执行项目结构优化...
echo [INFO] Root: %ROOT_DIR%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%optimize_project_structure.ps1" -Root "%ROOT_DIR%"
set "ERR=%ERRORLEVEL%"

echo.
if not "%ERR%"=="0" (
  echo [ERROR] 结构优化执行失败，错误码: %ERR%
) else (
  echo [OK] 结构优化执行成功
)

echo.
echo 按任意键退出...
pause >nul
exit /b %ERR%
