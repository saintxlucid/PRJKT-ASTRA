# 🚀 Run ASTRA Demo with Local LLM
# Run this in a SECOND terminal AFTER server is loaded

Write-Host "🌌 Starting ASTRA 3.1 Demo with Local LLM..." -ForegroundColor Cyan
Write-Host ""

# Check if llama.cpp server is running
Write-Host "🔍 Checking if LLM server is running..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:9010/v1/models" -TimeoutSec 5
    Write-Host "✅ LLM server is running" -ForegroundColor Green
    Write-Host "   Model: $($response.data[0].id)" -ForegroundColor Gray
} catch {
    Write-Host "❌ LLM server not responding" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start the server first:" -ForegroundColor Yellow
    Write-Host "  .\start_llm_server.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Wait for the server to load (you'll see 'llama_new_context_with_model')" -ForegroundColor Yellow
    Write-Host "Then run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "⚙️  Configuring ASTRA environment..." -ForegroundColor Yellow

# Set environment variables for ASTRA
$env:ASTRA_LLM_BASE_URL = "http://localhost:9010/v1"
$env:ASTRA_LLM_MODEL_NAME = "gpt-oss-20b"
$env:ASTRA_LLM_API_KEY = "dummy"

Write-Host "✅ Environment configured:" -ForegroundColor Green
Write-Host "   LLM_BASE_URL:  $env:ASTRA_LLM_BASE_URL" -ForegroundColor Gray
Write-Host "   LLM_MODEL:     $env:ASTRA_LLM_MODEL_NAME" -ForegroundColor Gray
Write-Host ""

Write-Host "🚀 Starting ASTRA demo..." -ForegroundColor Cyan
Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                  ASTRA 3.1 DEMO" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Change to project directory and run demo
Set-Location "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python quick_start_unified.py demo
