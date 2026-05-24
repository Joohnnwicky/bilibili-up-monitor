@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   🔑 前线观察大队 - B站Cookie获取工具
echo ==========================================
echo.
echo 正在启动...
echo.
python "%~dp0获取B站Cookie.py"

if errorlevel 1 (
    echo.
    echo [错误] 无法启动！请确保已安装Python
    pause
)
