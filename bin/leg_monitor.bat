@echo off
chcp 65001 >nul
title 航段数据监控 (端口 9222)

REM 设置Python路径（使用虚拟环境中的Python）
set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"

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

echo ========================================================================
echo 航段数据独立监控 (端口 9222)
echo ========================================================================
echo.
echo 💡 使用前准备：
echo    1. 双击原来的 Chrome 快捷方式启动浏览器（端口 9222）
echo    2. 确保浏览器已打开并登录系统
echo    3. 运行本脚本开始监控
echo.
echo ⚙️  功能说明：
echo    - 连接到主浏览器（端口 9222）
echo    - 每分钟自动刷新航段数据
echo    - 与 Fault 数据完全隔离，互不干扰
echo.
echo 🛑 停止监控：按 Ctrl+C
echo ========================================================================
echo.

echo 🚀 启动航段数据独立监控...
echo.

"%PYTHON_EXE%" run_leg_scheduler.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 监控已正常退出
) else (
    echo.
    echo ❌ 监控异常退出
)

echo.
pause
