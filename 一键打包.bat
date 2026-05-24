@echo off
chcp 65001 >nul
title B站数据看板 - 一键打包工具
echo.
echo ========================================
echo    B站数据看板 v1.0.0 - 一键打包
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 检查依赖...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo         安装PyInstaller...
    pip install pyinstaller pillow requests -q
)

echo [2/4] 清理旧文件...
if exist build\build rmdir /s /q build\build 2>nul
if exist build\dist rmdir /s /q build\dist 2>nul
if exist dist rmdir /s /q dist 2>nul

echo [3/4] 开始打包...
cd build
python build_exe.py
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo [4/4] 打包完成！
echo.
echo ========================================
echo ✅ 打包成功！
echo 📁 输出位置: dist\
echo ========================================
echo.
echo 按任意键打开输出目录...
pause >nul

if exist ..\dist explorer ..\dist
