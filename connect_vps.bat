@echo off
REM ================================================
REM SSH Connect to LeadMaps VPS
REM ================================================
REM Usage: Double-click this file or run from terminal

set PEM_FILE=C:\Users\dewan\Downloads\dewhush.pem
set USERNAME=ubuntu
set VPS_IP=3.25.177.97

echo ================================================
echo   DEPLOYMENT COMMANDS (COPY THESE):
echo ================================================
echo   cd ~/Back-End-Lead-Maps
echo   git pull origin main
echo   source venv/bin/activate
echo   pip install playwright
echo   playwright install chromium
echo   playwright install-deps chromium
echo   sudo systemctl restart leadmaps
echo ================================================
echo.

echo   Connecting to LeadMaps VPS...
ssh -i "%PEM_FILE%" %USERNAME%@%VPS_IP%

pause
