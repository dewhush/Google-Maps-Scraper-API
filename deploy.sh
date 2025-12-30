#!/bin/bash
set -e

# Load user environment variables if needed
# source ~/.bashrc

echo "=========================================="
echo "   Auto-Deploying Lead Maps Backend"
echo "=========================================="
date

# 1. Pull latest code
echo "[1/3] Pulling latest code..."
git reset --hard
git pull origin main

# 2. Update dependencies
echo "[2/3] Updating dependencies..."
# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Warning: No venv found, skipping pip install"
fi

# 3. Restart Service
echo "[3/3] Restarting systemd service..."
# Try to restart without sudo password first
if sudo -n systemctl restart leadmaps 2>/dev/null; then
    echo "Service restarted successfully."
else
    echo "Sudo password required. Trying standard sudo..."
    sudo systemctl restart leadmaps
fi

echo "=========================================="
echo "   Deployment Complete!"
echo "=========================================="
