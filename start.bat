@echo off
chcp 65001 > nul

ECHO =================================
ECHO  TDL GUI Startup Script
ECHO =================================
ECHO.

REM --- Check for a system-wide Python installation first ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    ECHO ERROR: Python is not installed or not found in your system's PATH.
    ECHO Please install Python 3.8+ from python.org and ensure it's added to your PATH.
    ECHO.
    pause
    exit /b 1
)

REM --- Step 1: Ensure a virtual environment exists ---
if not exist "venv\Scripts\activate.bat" (
    ECHO Local environment not found. Creating one now...
    python -m venv venv
    if %errorlevel% neq 0 (
        ECHO ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    ECHO Virtual environment created successfully.
    ECHO.
)

REM --- Step 2: Activate the virtual environment and install/update dependencies ---
ECHO Activating local environment...
call "venv\Scripts\activate.bat"

ECHO.
ECHO Ensuring all dependencies are installed and up to date...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    ECHO ERROR: Failed to install dependencies from requirements.txt.
    ECHO Please check your internet connection and try again.
    pause
    exit /b 1
)
ECHO Dependencies are up to date.
ECHO.

REM --- Step 3: Launch the application ---
ECHO Launching application...
ECHO.
python src\main.py
ECHO.
ECHO Application closed.
pause
exit /b
