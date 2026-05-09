@echo off
chcp 65001 >nul
echo ==========================================
echo   用地合规提示Agent - 打包脚本
echo ==========================================
echo.

echo [1/3] 安装依赖...
pip install pyinstaller flask -q
if errorlevel 1 (
    echo 依赖安装失败，请检查网络连接。
    pause
    exit /b 1
)

echo.
echo [2/3] 开始打包（可能需要 2~5 分钟，请耐心等待）...
pyinstaller --noconfirm --onedir --name "用地合规Agent" ^
  --add-data "compliance_agent;compliance_agent" ^
  --hidden-import=config ^
  --hidden-import=rules.compliance_rules ^
  --hidden-import=web.report_builder ^
  --clean ^
  launch.py

if errorlevel 1 (
    echo 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo [3/3] 打包完成！
echo.
echo 输出目录: dist\用地合规Agent\
echo.
echo 使用方式:
echo   1. 将 dist\用地合规Agent 文件夹整体压缩发送
echo   2. 对方解压后，双击 "用地合规Agent.exe" 即可运行
echo   3. 程序会自动打开浏览器访问 http://127.0.0.1:5000
echo   4. 运行时请勿关闭黑色命令行窗口
echo.
pause
