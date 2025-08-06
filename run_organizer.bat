@echo off
REM STL Auto Organizer - Windows Batch Script
REM This script provides easy execution of the file organizer

echo ========================================
echo     STL Auto Organizer for Manyfold
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo Python found. Starting organizer...
echo.

REM Default to dry-run mode for safety
if "%1"=="" (
    echo Running in DRY-RUN mode (no changes will be made)
    echo To apply changes, run: run_organizer.bat --live
    echo.
    python file_organizer.py --dry-run
) else if "%1"=="--live" (
    echo Running in LIVE mode (changes will be applied)
    echo.
    python file_organizer.py
) else if "%1"=="--help" (
    python file_organizer.py --help
) else (
    echo Running with custom arguments: %*
    python file_organizer.py %*
)

echo.
echo Operation completed.
pause
