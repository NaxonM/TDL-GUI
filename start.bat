@echo off
chcp 65001 > nul

ECHO =================================
ECHO  TDL GUI Startup Script
ECHO =================================
ECHO.

REM --- Check 1: Use existing virtual environment if it exists ---
if exist "venv\Scripts\activate.bat" (
    ECHO Found local environment. Activating and launching...
    call "venv\Scripts\activate.bat"
    python src\main.py
    ECHO.
    ECHO Application closed.
    pause
    exit /b
)

ECHO Local environment not found. Checking system for dependencies...
ECHO.

REM --- Check 2: Check for system-wide Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    ECHO ERROR: Python is not installed or not found in your system's PATH.
    ECHO Please install Python 3.8+ from python.org and ensure it's added to your PATH.
    ECHO.
    pause
    exit /b 1
)

REM --- Check 3: Check for system-wide PyQt6 ---
ECHO Checking for system-wide PyQt6 library...
python -c "from PyQt6.QtWidgets import QApplication" >nul 2>&1
if %errorlevel% equ 0 (
    ECHO Found system-wide PyQt6.
    ECHO Launching application directly...
    ECHO.
    python src\main.py
    ECHO.
    ECHO Application closed.
    pause
    exit /b
)

REM --- Step 4: Prompt for setup if dependencies are missing ---
ECHO WARNING: System-wide PyQt6 library not found.
ECHO.
set /p setup_choice="Would you like to create a local environment and install it now? (y/n): "
if /i "%setup_choice%"=="y" (
    ECHO.
    ECHO Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        ECHO ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )

    ECHO Installing dependencies from requirements.txt...
    call "venv\Scripts\activate.bat"
    pip install -r requirements.txt
    if %errorlevel% equ 0 (
        ECHO.
        ECHO Setup complete! Launching application...
        ECHO.
        python src\main.py
        ECHO.
        ECHO Application closed.
    ) else (
        ECHO ERROR: Failed to install dependencies. Please check your internet connection and try again.
    )
) else (
    ECHO.
    ECHO Setup cancelled.
    ECHO To run the application, please install PyQt6 manually by running: pip install PyQt6
)

ECHO.
pause
