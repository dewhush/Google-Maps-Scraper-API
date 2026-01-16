@echo off
title Google Maps Scraper API
color 0A

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║       GOOGLE MAPS SCRAPER API                     ║
echo  ║       Business Lead Extraction Service            ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo [SETUP] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Install Playwright browsers (for scraping)
echo [SETUP] Installing Playwright browsers...
playwright install chromium --with-deps >nul 2>&1
echo [OK] Browser installed

REM Check if .env exists
if not exist ".env" (
    echo.
    echo  ╔═══════════════════════════════════════════════════╗
    echo  ║  [WARNING] .env file not found!                   ║
    echo  ║                                                   ║
    echo  ║  1. Copy .env.example to .env                     ║
    echo  ║  2. Fill in your API credentials                  ║
    echo  ║  3. Run this script again                         ║
    echo  ╚═══════════════════════════════════════════════════╝
    echo.
    copy .env.example .env >nul 2>&1
    echo [INFO] Created .env from template. Please edit it with your credentials.
    notepad .env
    pause
    exit /b 1
)

echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║  Starting API Server...                           ║
echo  ║                                                   ║
echo  ║  Local:   http://localhost:8000                   ║
echo  ║  Docs:    http://localhost:8000/docs              ║
echo  ║  ReDoc:   http://localhost:8000/redoc             ║
echo  ║                                                   ║
echo  ║  Press Ctrl+C to stop the server                  ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

uvicorn server:app --host 0.0.0.0 --port 8000 --reload

pause
