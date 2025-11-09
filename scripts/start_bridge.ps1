# scripts/start_bridge.ps1
# Start ASTRA Tool Bridge service

param(
    [string]$ApiKey = $env:BRIDGE_API_KEY,
    [int]$Port = 8765,
    [switch]$Docker
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== ASTRA Tool Bridge Startup ===" -ForegroundColor Cyan

# Check API key
if (-not $ApiKey) {
    Write-Host "[!] Warning: BRIDGE_API_KEY not set, using default 'changeme'" -ForegroundColor Yellow
    $ApiKey = "changeme"
}

# Set environment
$env:BRIDGE_API_KEY = $ApiKey
$env:BRIDGE_AUDIT_LOG = "data/bridge_audit.log"
$env:LLAMA_URL = "http://127.0.0.1:8001/v1/chat/completions"
$env:BRIDGE_SAFE_ROOT = "data/safe"
$env:BRIDGE_PORT = $Port

# Create directories
New-Item -ItemType Directory -Path "data/safe" -Force | Out-Null
New-Item -ItemType Directory -Path "data" -Force | Out-Null

if ($Docker) {
    Write-Host "[*] Starting Bridge in Docker..." -ForegroundColor Cyan
    
    Push-Location "src/astra/bridge"
    docker-compose -f docker-compose.bridge.yml up -d
    Pop-Location
    
    Write-Host "[✓] Bridge started in Docker" -ForegroundColor Green
    Write-Host "    Health: http://localhost:8765/health" -ForegroundColor Gray
    Write-Host "    Metrics: http://localhost:8765/metrics" -ForegroundColor Gray
    Write-Host "    Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Gray
} else {
    Write-Host "[*] Starting Bridge locally on port $Port..." -ForegroundColor Cyan
    
    # Check if port is available
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Write-Host "[X] Port $Port is already in use" -ForegroundColor Red
        exit 1
    }
    
    # Install dependencies if needed
    Write-Host "[*] Checking dependencies..." -ForegroundColor Gray
    pip install -q -r src/astra/bridge/requirements.bridge.txt
    
    # Start bridge
    Write-Host "[*] Bridge URL: http://127.0.0.1:$Port" -ForegroundColor Green
    Write-Host "[*] API Key: $ApiKey" -ForegroundColor Gray
    Write-Host "[*] Audit Log: $env:BRIDGE_AUDIT_LOG" -ForegroundColor Gray
    Write-Host ""
    
    python -m uvicorn src.astra.bridge.tool_bridge_service:app --host 127.0.0.1 --port $Port --log-level info
}
