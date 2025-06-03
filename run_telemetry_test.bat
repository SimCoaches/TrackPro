@echo off
echo ==========================================
echo       TrackPro Telemetry Flow Test
echo ==========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

echo Running telemetry flow test...
echo.

REM Run the test script
python test_telemetry_flow.py

echo.
echo ==========================================
echo Test completed. Check telemetry_test.log for detailed results.
echo ==========================================
pause 