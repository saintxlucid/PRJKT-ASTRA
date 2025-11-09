# ASTRA 3.1 - Local LLM Setup Script (PowerShell)
# Launches llama.cpp server with GPT-OSS 20B model

param(
    [string]$ModelPath = "X:\MODELS\gpt-oss-20b\gpt-oss-20b.Q4_K_M.gguf",
    [int]$Port = 9010,
    [int]$ContextLength = 131072,
    [int]$GpuLayers = 20,
    [int]$Threads = 16
)

Write-Host "🌌 ASTRA 3.1 - Local LLM Server Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if model file exists
if (-not (Test-Path $ModelPath)) {
    Write-Host "❌ Model file not found: $ModelPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please update the ModelPath parameter or ensure the model is downloaded." -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Model found: $ModelPath" -ForegroundColor Green
Write-Host "✓ Port: $Port" -ForegroundColor Green
Write-Host "✓ Context length: $ContextLength tokens" -ForegroundColor Green
Write-Host "✓ GPU layers: $GpuLayers" -ForegroundColor Green
Write-Host "✓ Threads: $Threads" -ForegroundColor Green
Write-Host ""

# Find llama.cpp server executable
$ServerExe = Join-Path (Split-Path $ModelPath) "server.exe"

if (-not (Test-Path $ServerExe)) {
    # Try alternate locations
    $AlternatePaths = @(
        "C:\llama.cpp\server.exe",
        ".\server.exe",
        ".\llama.cpp\server.exe"
    )
    
    foreach ($AltPath in $AlternatePaths) {
        if (Test-Path $AltPath) {
            $ServerExe = $AltPath
            break
        }
    }
    
    if (-not (Test-Path $ServerExe)) {
        Write-Host "❌ llama.cpp server.exe not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Tried locations:" -ForegroundColor Yellow
        Write-Host "  - $ServerExe" -ForegroundColor Yellow
        foreach ($AltPath in $AlternatePaths) {
            Write-Host "  - $AltPath" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "Please download llama.cpp from: https://github.com/ggerganov/llama.cpp/releases" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "✓ Server executable: $ServerExe" -ForegroundColor Green
Write-Host ""

# Set environment variables for ASTRA
$env:ASTRA_LLM_PROVIDER = "openai_compatible"
$env:ASTRA_LLM_BASE_URL = "http://localhost:$Port/v1"
$env:ASTRA_LLM_MODEL_NAME = "gpt-oss-20b"
$env:ASTRA_LLM_MAX_TOKENS = "2048"
$env:ASTRA_LLM_TEMPERATURE = "0.2"
$env:OPENAI_API_KEY = "dummy"

Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  ASTRA_LLM_PROVIDER = openai_compatible" -ForegroundColor Gray
Write-Host "  ASTRA_LLM_BASE_URL = http://localhost:$Port/v1" -ForegroundColor Gray
Write-Host "  ASTRA_LLM_MODEL_NAME = gpt-oss-20b" -ForegroundColor Gray
Write-Host ""

Write-Host "🚀 Starting llama.cpp server..." -ForegroundColor Cyan
Write-Host ""

# Build command
$ServerArgs = @(
    "-m", $ModelPath,
    "-c", $ContextLength,
    "-ngl", $GpuLayers,
    "-t", $Threads,
    "--host", "0.0.0.0",
    "--port", $Port,
    "--chat-template", "openai"
)

# Launch server
Write-Host "Command: $ServerExe $($ServerArgs -join ' ')" -ForegroundColor Gray
Write-Host ""
Write-Host "Server starting... Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

try {
    & $ServerExe @ServerArgs
}
catch {
    Write-Host ""
    Write-Host "❌ Server crashed: $_" -ForegroundColor Red
    exit 1
}
finally {
    Write-Host ""
    Write-Host "🛑 Server stopped" -ForegroundColor Yellow
}
