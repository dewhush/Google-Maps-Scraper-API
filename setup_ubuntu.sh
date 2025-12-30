#!/bin/bash

# Auto Setup Script for LeadMaps Backend on Ubuntu
# Usage: ./setup_ubuntu.sh

set -e

echo "=================================================="
echo "   LeadMaps Backend Auto Setup for Ubuntu"
echo "=================================================="

# 1. Update System
echo "[1/8] Updating system packages..."
sudo apt-get update
# Non-interactive upgrade to avoid prompts
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-full python3-pip python3-venv wget curl unzip git build-essential libssl-dev libffi-dev

# 2. Setup Project Directory
APP_DIR=$(pwd)
VENV_DIR="$APP_DIR/venv"

echo "Project Directory: $APP_DIR"

# 3. Create Virtual Environment
echo "[2/8] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Activate venv for installation
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

# 4. Install Dependencies
echo "[3/8] Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Error: requirements.txt not found!"
    exit 1
fi

# 5. Install Playwright and browser
echo "[4/8] Installing Playwright browser..."
pip install playwright
playwright install chromium
playwright install-deps chromium

# 6. Environment Variables
echo "[5/8] Checking environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example. IMPORTANT: Please edit .env with your actual configurations."
    else
        echo "Warning: No .env or .env.example found. Please create one manually."
    fi
fi

# 7. Setup Systemd Service
echo "[6/8] Configuring systemd service..."
SERVICE_NAME="leadmaps"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
USER_NAME=$(whoami)

# Create service file
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=LeadMaps Backend API
After=network.target

[Service]
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# 8. Start Service
echo "[7/8] Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "=================================================="
echo "   Setup Complete!"
echo "=================================================="
echo "Service is running."
echo "Check status: sudo systemctl status $SERVICE_NAME"
echo "View logs:    journalctl -u $SERVICE_NAME -f"
echo "Stop server:  sudo systemctl stop $SERVICE_NAME"
echo ""
echo "NOTE: Make sure to update your .env file with correct credentials!"
