# ================================================
# SSH Connect to LeadMaps VPS (PowerShell)
# ================================================
# Usage: Right-click > Run with PowerShell
#    or: .\connect_vps.ps1

$PEM_FILE = "C:\Users\dewan\Downloads\dewhush.pem"
$USERNAME = "ubuntu"
$VPS_IP = "3.25.177.97"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Connecting to LeadMaps VPS" -ForegroundColor Cyan
Write-Host "  IP: $VPS_IP" -ForegroundColor Yellow
Write-Host "  User: $USERNAME" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Connect via SSH
ssh -i $PEM_FILE "$USERNAME@$VPS_IP"
