# ASTRA Server Startup Script (PowerShell)
# This script starts the ASTRA server with proper environment setup
# Usage: .\scripts\start_astra.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   ASTRA Server Startup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Set the project root
$ProjectRoot = "X:\PROJECT_ASTRA"
Set-Location $ProjectRoot

# Activate environment
Write-Host "[1/4] Activating environment..." -ForegroundColor Yellow
& "$ProjectRoot\scripts\activate_astra.ps1"

# Check if llama.cpp server is running
Write-Host "[2/4] Checking llama.cpp server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "   ✓ llama.cpp server is running on port 8001" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ Warning: llama.cpp server not detected on port 8001" -ForegroundColor Yellow
    Write-Host "   Please start llama.cpp server manually if needed" -ForegroundColor Yellow
}

# Initialize database if not exists
Write-Host "[3/4] Checking database..." -ForegroundColor Yellow
if (-not (Test-Path "$ProjectRoot\data\database\astra.db")) {
    Write-Host "   Database not found. Initializing..." -ForegroundColor Yellow
    & "$ProjectRoot\.venv\Scripts\python.exe" "$ProjectRoot\scripts\init_database.py"
    Write-Host "   ✓ Database initialized" -ForegroundColor Green
} else {
    Write-Host "   ✓ Database exists" -ForegroundColor Green
}

# Start ASTRA server
Write-Host "[4/4] Starting ASTRA server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   Server starting on http://localhost:8080" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

& "$ProjectRoot\.venv\Scripts\python.exe" "$ProjectRoot\run_server.py"
