@echo off
chcp 65001 >nul
title 航班数据抓取系统

REM 激活虚拟环境
call "%~dp0venv\Scripts\activate.bat"

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
    python main_scheduler.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 🚀 启动交互模式...
    echo.
    python main_scheduler.py --interactive
    pause
) else if "%choice%"=="3" (
    echo.
    echo 👋 退出系统
    call deactivate
    exit
) else (
    echo.
    echo ❌ 无效选择，请重新运行脚本
    pause
)

REM 退出时停用虚拟环境
call deactivate
