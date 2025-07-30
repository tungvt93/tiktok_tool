@echo off
title TikTok Video Processing Tool - GUI
echo Starting TikTok Video Processing Tool GUI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

REM Run the launcher script
python run_gui.py

REM Pause if there was an error
if errorlevel 1 (
    echo.
    echo An error occurred. Please check the messages above.
    pause
) 