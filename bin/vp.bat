@echo off
REM Virtual Environment Python Runner
REM Usage: vp.bat <python_command>
REM Example: vp.bat -m pytest tests/test_data_freshness.py
REM          vp.bat bin/run_leg_scheduler.py

set VENV_PYTHON=venv\Scripts\python.exe

if not exist %VENV_PYTHON% (
    echo ERROR: Virtual environment not found at %VENV_PYTHON%
    echo Please create it first: python -m venv venv
    exit /b 1
)

%VENV_PYTHON% %*
