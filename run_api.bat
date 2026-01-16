@echo off
title Google Maps Scraper API
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║       GOOGLE MAPS SCRAPER API                     ║
echo  ║       Lightweight Scraping Service                ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [SETUP] Installing dependencies...
pip install fastapi uvicorn python-dotenv playwright pydantic beautifulsoup4 -q

REM Install Playwright browsers
echo [SETUP] Installing browser...
playwright install chromium >nul 2>&1

REM Check if .env exists
if not exist ".env" (
    echo [INFO] Creating .env from template...
    copy .env.example .env >nul 2>&1
)

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║  Starting Scraper API...                          ║
echo  ║                                                   ║
echo  ║  Local:   http://localhost:8000                   ║
echo  ║  Docs:    http://localhost:8000/docs              ║
echo  ║                                                   ║
echo  ║  Press Ctrl+C to stop                             ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

python api.py

pause
