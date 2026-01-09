@echo off
chcp 65001 >nul
title 航班数据抓取系统

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
echo 🛫 航班数据抓取系统
echo ============================================================
echo.
echo 请选择运行模式:
echo.
echo [1] 调度模式 - 自动定时抓取数据 (06:30-21:00)
echo [2] 交互模式 - 手动选择抓取任务
echo [3] 退出
echo.
echo ============================================================

set /p choice="请输入选择 (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 启动调度模式...
    echo.
    "%PYTHON_EXE%" main_scheduler.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 🚀 启动交互模式...
    echo.
    "%PYTHON_EXE%" main_scheduler.py --interactive
    pause
) else if "%choice%"=="3" (
    echo.
    echo 👋 退出系统
    exit /b 0
) else (
    echo.
    echo ❌ 无效选择，请重新运行脚本
    pause
)
