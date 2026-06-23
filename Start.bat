@echo off
title Polymarket BTC Bot - Dashboard
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo Run Install.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Opening dashboard in your browser...
echo Keep this window open while the bot is running.
echo.

python -m streamlit run easy_app\main.py --server.headless true

pause
