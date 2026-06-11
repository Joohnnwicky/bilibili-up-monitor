@echo off
chcp 65001 >nul
echo ========================================
echo   B站粉丝追踪器 - 每日定时任务
echo ========================================
echo.

cd /d "%~dp0"

python bilibili_fans_tracker.py

echo.
echo 运行完毕，%date% %time%
