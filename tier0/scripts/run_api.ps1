# ASTRA Tier-0 API Server
# Runs FastAPI server on port 8000

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

# Start API
Write-Host "[ASTRA] Starting Tier-0 API..." -ForegroundColor Cyan
Write-Host "[*] Server running on http://127.0.0.1:$($env:ASTRA_API_PORT)" -ForegroundColor Yellow
Write-Host "[*] Docs: http://127.0.0.1:$($env:ASTRA_API_PORT)/docs" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn `
    "src.api.main:app" `
    --host "127.0.0.1" `
    --port $($env:ASTRA_API_PORT) `
    --reload `
    --log-level info
