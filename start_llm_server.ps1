# 🚀 Quick Start - llama.cpp with GPT-OSS 20B
# Run this script to start your local LLM server and ASTRA

Write-Host "🧠 Starting llama.cpp server with GPT-OSS 20B..." -ForegroundColor Cyan
Write-Host ""

# Configuration
$ModelPath = "X:\MODELS\gpt-oss-20b\gpt-oss-20b.Q4_K_M.gguf"
$ServerExe = "X:\MODELS\gpt-oss-20b\server.exe"
$Port = 9010
$ContextLength = 131072

# Check if model exists
if (-not (Test-Path $ModelPath)) {
    Write-Host "❌ Model not found at: $ModelPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please update the model path in this script or provide it:" -ForegroundColor Yellow
    $ModelPath = Read-Host "Enter full path to your .gguf model"
    
    if (-not (Test-Path $ModelPath)) {
        Write-Host "❌ Model still not found. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Check if server.exe exists
if (-not (Test-Path $ServerExe)) {
    Write-Host "⚠️  server.exe not found at: $ServerExe" -ForegroundColor Yellow
    Write-Host "Searching for server.exe in common locations..." -ForegroundColor Yellow
    
    # Try common locations
    $PossiblePaths = @(
        ".\server.exe",
        "X:\MODELS\llama.cpp\build\bin\Release\server.exe",
        "X:\MODELS\llama.cpp\server.exe",
        "C:\Program Files\llama.cpp\server.exe",
        "$env:USERPROFILE\llama.cpp\server.exe"
    )
    
    $ServerExe = $null
    foreach ($path in $PossiblePaths) {
        if (Test-Path $path) {
            $ServerExe = $path
            Write-Host "✅ Found server.exe at: $ServerExe" -ForegroundColor Green
            break
        }
    }
    
    if (-not $ServerExe) {
        Write-Host "❌ Could not find server.exe" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please provide the path:" -ForegroundColor Yellow
        $ServerExe = Read-Host "Enter full path to server.exe"
        
        if (-not (Test-Path $ServerExe)) {
            Write-Host "❌ server.exe not found. Exiting." -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "📋 Configuration:" -ForegroundColor Green
Write-Host "  Server: $ServerExe" -ForegroundColor Gray
Write-Host "  Model:  $ModelPath" -ForegroundColor Gray
Write-Host "  Port:   $Port" -ForegroundColor Gray
Write-Host "  Context: $ContextLength tokens" -ForegroundColor Gray
Write-Host ""

Write-Host "🔄 Starting llama.cpp server..." -ForegroundColor Yellow
Write-Host "   This will take 30-60 seconds to load the model" -ForegroundColor Gray
Write-Host "   DO NOT CLOSE THIS WINDOW" -ForegroundColor Red
Write-Host ""

# Start server in background with visible output
$ServerArgs = @(
    "-m", $ModelPath,
    "-c", $ContextLength,
    "--host", "0.0.0.0",
    "--port", $Port,
    "--chat-template", "openai"
)

Write-Host "Command: $ServerExe $($ServerArgs -join ' ')" -ForegroundColor Gray
Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "              llama.cpp SERVER OUTPUT" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Start server (this will block and show output)
& $ServerExe @ServerArgs
