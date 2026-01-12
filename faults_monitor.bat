@echo off
chcp 65001 >nul
title 故障监控页面

REM 设置Python路径（使用虚拟环境中的Python）
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"

REM 检查虚拟环境是否存在
if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到虚拟环境！
    echo 路径：%PYTHON_EXE%
    echo.
    echo 请先创建虚拟环境：
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo ============================================================
echo 🔧 故障监控页面
echo ============================================================
echo.
echo 💡 功能说明：
echo    - 打开故障监控页面
echo    - 与 leg data 监控并行运行
echo    - 共享同一个浏览器实例
echo.
echo ============================================================
echo.

echo 🚀 启动故障监控页面...
echo.

"%PYTHON_EXE%" fetchers/fault_fetcher.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 故障监控页面已打开
) else (
    echo.
    echo ❌ 启动失败
)

echo.
pause
