@echo off
chcp 65001 >nul
title 航班调度系统 - 验证和测试

echo ============================================================
echo 🛫 航班智能调度系统 - 验证和测试
echo ============================================================
echo.

REM 设置Python路径
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"

REM 检查虚拟环境
if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到虚拟环境！
    echo 请先创建虚拟环境：
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo 📋 可用的测试选项:
echo.
echo [1] 运行单元测试 - 验证所有功能
echo [2] 运行交互式模拟 - 查看完整运行过程
echo [3] 运行真实调度模式 - 连接真实网站
echo [4] 运行交互模式 - 手动选择任务
echo [5] 退出
echo.

set /p choice="请选择测试选项 (1-5): "

if "%choice%"=="1" (
    echo.
    echo 🧪 运行单元测试...
    echo.
    "%PYTHON_EXE%" test_scheduler.py
    echo.
    echo ✅ 测试完成！
    pause
) else if "%choice%"=="2" (
    echo.
    echo 🎮 启动交互式模拟...
    echo.
    "%PYTHON_EXE%" simulate_scheduler.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo 🚀 启动真实调度模式...
    echo.
    "%PYTHON_EXE%" main_scheduler.py
    pause
) else if "%choice%"=="4" (
    echo.
    echo 🎯 启动交互模式...
    echo.
    "%PYTHON_EXE%" main_scheduler.py --interactive
    pause
) else if "%choice%"=="5" (
    echo.
    echo 👋 退出测试
    exit /b 0
) else (
    echo.
    echo ❌ 无效选择，请重新运行脚本
    pause
)
