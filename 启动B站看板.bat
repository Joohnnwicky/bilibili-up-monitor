@echo off
chcp 65001 >nul
title 前线观察大队 - B站数据看板
echo ========================================
echo    前线观察大队 - B站数据看板
echo ========================================
echo.
echo 正在启动程序...
echo.

python "%~dp0bilibili_dashboard.py"

if errorlevel 1 (
    echo.
    echo [错误] 程序启动失败！
    echo.
    echo 可能的原因：
    echo 1. 未安装 Python
    echo 2. 缺少必要的库（PIL/Pillow）
    echo.
    echo 请尝试运行以下命令安装依赖：
    echo    pip install pillow requests
    echo.
    pause
)
