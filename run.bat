@echo off
chcp 65001 >nul
cd /d D:\Code\flight_data_daily_get
call venv\Scripts\activate

echo.
echo ========================================
echo   Flight Data Auto Fetch System
echo ========================================
echo.

REM Get first missing date
for /f "delims=" %%D in ('python flight_data_update.py --get-missing 2^>nul') do set MISSING_DATE=%%D

if "%MISSING_DATE%"=="" (
    echo [Normal Mode] No missing data, fetching today's data...
    echo ----------------------------------------

    echo [Step 1/2] Auto login...
    python automation_login.py
    if errorlevel 1 (
        echo.
        echo ERROR: Auto login failed
        pause
        exit /b 1
    )

    echo.
    echo [Step 2/2] Fetching today's flight data...
    timeout /t 3 /nobreak >nul
    python flight_data_get.py
    if errorlevel 1 (
        echo.
        echo ERROR: Data fetch failed
        pause
        exit /b 1
    )

    echo.
    echo Updating main data file...
    python flight_data_update.py
    set UPDATE_RESULT=%errorlevel%

    if "%UPDATE_RESULT%"=="0" (
        echo.
        echo ========================================
        echo   Task completed successfully!
        echo ========================================
        pause
        exit /b 0
    ) else (
        echo.
        echo ========================================
        echo   Task completed with warnings
        echo ========================================
        pause
        exit /b 0
    )
)

REM Data Fill Mode - Missing data detected
echo [Data Fill Mode] Missing data detected
echo ----------------------------------------
echo.
echo Showing all missing dates...
python flight_data_update.py
echo.

echo First missing date: %MISSING_DATE%
echo Starting fill process...
echo.

REM Verify browser login first
echo [Pre-check] Verifying browser session...
python automation_login.py
if errorlevel 1 (
    echo.
    echo ERROR: Browser login failed
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul

:fill_loop
REM Clear the variable first
set CURRENT_MISSING=

REM Get current first missing date
for /f "delims=" %%D in ('python flight_data_update.py --get-missing 2^>nul') do set CURRENT_MISSING=%%D

if "%CURRENT_MISSING%"=="" (
    echo.
    echo ========================================
    echo   All data filled successfully!
    echo ========================================
    pause
    exit /b 0
)

echo.
echo [%CURRENT_MISSING%] Fetching data...
echo ----------------------------------------
python flight_data_get.py %CURRENT_MISSING%
if errorlevel 1 (
    echo.
    echo ERROR: Failed to fetch data for %CURRENT_MISSING%
    pause
    exit /b 1
)

echo [%CURRENT_MISSING%] Updating main data file...
python flight_data_update.py >nul 2>&1

REM Check if current date's data was added successfully
REM Exit code 1 means "still missing other dates", but current date was added
REM Exit code 0 means "all dates filled"
REM Both cases are OK for continuing the loop

echo [%CURRENT_MISSING%] Successfully added

REM Continue with next missing date
goto fill_loop
