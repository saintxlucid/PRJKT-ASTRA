# ASTRA Tier-0 Voice Monitoring
# Monitors microphone for wake words and sends commands to API

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$Tier0Dir = Split-Path -Parent $ProjectRoot

# Load environment
$EnvFile = "$Tier0Dir\.env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[ERR] .env file not found. Run install_tier0.ps1 first." -ForegroundColor Red
    exit 1
}

# Parse .env file
$env:PYTHONPATH = "$Tier0Dir\src"
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^([^=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

# Activate venv if present
$VenvPath = "$Tier0Dir\.venv"
if (Test-Path "$VenvPath\Scripts\Activate.ps1") {
    & "$VenvPath\Scripts\Activate.ps1"
}

# Create monitor script
$MonitorScript = @"
import os
import time
import requests
from tier0.src.voice_engine.wake_service import WakeService

print("[ASTRA] Voice monitoring started")
print("[*] Press Ctrl+C to stop")
print()

# Initialize and start voice service
with WakeService(model_size="small") as voice:
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
        print("[ASTRA] Voice monitoring stopped")
"@

# Run monitor
Write-Host "[ASTRA] Starting voice monitor..." -ForegroundColor Cyan
Write-Host "[*] Wake words: astra, hey astra, astra listen, activate" -ForegroundColor Yellow
Write-Host "[*] Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

python -c $MonitorScript
