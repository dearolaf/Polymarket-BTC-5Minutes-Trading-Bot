@echo off
title Polymarket BTC Bot - Install
cd /d "%~dp0"

echo ============================================================
echo   Polymarket BTC 5-Min Bot - Install
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    echo Download Python 3.14+ from https://www.python.org/downloads/
    echo During install, check "Add Python to PATH".
    pause
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed.
    echo Download Git from https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if not exist venv python -m venv venv

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing packages (this may take several minutes)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo [4/4] Creating .env from template...
if not exist .env copy .env.example .env >nul

echo.
echo ============================================================
echo   Install complete!
echo   Next: double-click Start.bat
echo ============================================================
pause
