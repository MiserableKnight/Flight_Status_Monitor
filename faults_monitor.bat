@echo off
chcp 65001 >nul
title 故障数据独立监控 (端口 9333)

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

echo ========================================================================
echo 故障数据独立监控 (端口 9333)
echo ========================================================================
echo.
echo 💡 使用前准备：
echo    1. 双击桌面上的"故障监控"快捷方式启动专用浏览器
echo    2. 确保浏览器已打开并登录系统
echo    3. 运行本脚本开始监控
echo.
echo ⚙️  功能说明：
echo    - 连接到独立浏览器（端口 9333）
echo    - 每 5 分钟自动刷新故障数据
echo    - 与 Leg 数据完全隔离，互不干扰
echo.
echo 🛑 停止监控：按 Ctrl+C
echo ========================================================================
echo.

echo 🚀 启动故障数据独立监控...
echo.

"%PYTHON_EXE%" run_fault_scheduler.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 监控已正常退出
) else (
    echo.
    echo ❌ 监控异常退出
)

echo.
pause
