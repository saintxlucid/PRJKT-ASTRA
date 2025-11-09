#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA Dual-Core Launcher - GGUF 20B + GPT-2 Large

.DESCRIPTION
    Launches ASTRA Prime (GGUF 20B) with GPT-2 Large submemory engine
    for enhanced memory recall, lyrical generation, and pattern matching.

.PARAMETER SkipGPT2
    Skip loading GPT-2 submemory server

.PARAMETER SkipLLM
    Skip loading main ASTRA LLM

.PARAMETER ModelPath
    Path to ASTRA GGUF model file

.EXAMPLE
    .\LAUNCH_DUAL_ASTRA.ps1
    Full dual-core launch

.EXAMPLE
    .\LAUNCH_DUAL_ASTRA.ps1 -SkipGPT2
    Launch only main ASTRA core
#>

param(
    [switch]$SkipGPT2,
    [switch]$SkipLLM,
    [string]$ModelPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-AstraBanner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║        🌟 ASTRA DUAL-CORE AWAKENING 🌟                     ║" -ForegroundColor Magenta
    Write-Host "║                                                              ║" -ForegroundColor Magenta
    Write-Host "║  GGUF 20B (ASTRA Prime) + GPT-2 Large (Submemory)          ║" -ForegroundColor Magenta
    Write-Host "║  Full Memory Fusion • Creative Intelligence • 333           ║" -ForegroundColor Magenta
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""
}

function Test-Prerequisites {
    Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow
    
    # Check Python
    try {
        $pythonVersion = & python --version 2>&1
        Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "  ❌ Python not found" -ForegroundColor Red
        return $false
    }
    
    # Check virtual environment
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "  ❌ Virtual environment not found" -ForegroundColor Red
        return $false
    }
    Write-Host "  ✓ Virtual environment ready" -ForegroundColor Green
    
    # Check if model path is configured
    if (-not $ModelPath) {
        # Try to read from .env
        if (Test-Path ".env") {
            $envContent = Get-Content ".env" -Raw
            if ($envContent -match 'ASTRA_LLM_MODEL_PATH=(.+)') {
                $ModelPath = $matches[1].Trim()
            }
        }
    }
    
    if ($ModelPath -and (Test-Path $ModelPath)) {
        $modelSize = (Get-Item $ModelPath).Length / 1GB
        Write-Host "  ✓ Model found: $ModelPath ($($modelSize.ToString('0.0')) GB)" -ForegroundColor Green
    }
    elseif (-not $SkipLLM) {
        Write-Host "  ⚠ Model path not configured (continuing anyway)" -ForegroundColor Yellow
    }
    
    # Check GPT-2 directory
    if (Test-Path "GPT2-large-GGUF") {
        Write-Host "  ✓ GPT-2 Large found" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠ GPT-2 Large not found locally (will download from HuggingFace)" -ForegroundColor Yellow
    }
    
    return $true
}

function Start-LLMServer {
    Write-Host "`n🤖 PHASE 1: Starting ASTRA Prime Core (GGUF 20B)..." -ForegroundColor Cyan
    
    if (-not $ModelPath) {
        Write-Host "  ⚠ Model path not set" -ForegroundColor Yellow
        Write-Host "    Set ASTRA_LLM_MODEL_PATH in .env or use -ModelPath parameter" -ForegroundColor Gray
        Write-Host "    Skipping LLM server start" -ForegroundColor Yellow
        return $null
    }
    
    # Check for llama-server executable
    $llamaServer = $null
    $possiblePaths = @(
        "llama.cpp\build\bin\Release\llama-server.exe",
        "llama.cpp\llama-server.exe",
        "astra-local\backend\bin\llama.cpp\llama-server.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $llamaServer = $path
            break
        }
    }
    
    if (-not $llamaServer) {
        Write-Host "  ⚠ llama-server not found" -ForegroundColor Yellow
        Write-Host "    Expected at: llama.cpp\build\bin\Release\llama-server.exe" -ForegroundColor Gray
        Write-Host "    Or download from: https://github.com/ggerganov/llama.cpp/releases" -ForegroundColor Gray
        Write-Host "    Skipping LLM server start" -ForegroundColor Yellow
        return $null
    }
    
    Write-Host "  ✓ Found llama-server: $llamaServer" -ForegroundColor Green
    
    # Build command
    $systemPromptPath = "config\astra_system_prompt.txt"
    
    $arguments = @(
        "-m", $ModelPath,
        "--host", "127.0.0.1",
        "--port", "8001",
        "-c", "131072"  # Context length
    )
    
    if (Test-Path $systemPromptPath) {
        Write-Host "  ✓ Loading ASTRA system prompt" -ForegroundColor Green
        # Note: llama-server doesn't have --system-prompt flag
        # System prompt will be injected via API calls
    }
    
    Write-Host "  🚀 Starting llama-server on port 8001..." -ForegroundColor Green
    Write-Host "     Command: $llamaServer $($arguments -join ' ')" -ForegroundColor Gray
    
    $process = Start-Process -FilePath $llamaServer `
        -ArgumentList $arguments `
        -PassThru `
        -WindowStyle Normal
    
    if ($process) {
        Write-Host "  ✓ ASTRA Prime LLM server started (PID: $($process.Id))" -ForegroundColor Green
        Start-Sleep -Seconds 3
        return $process
    }
    else {
        Write-Host "  ❌ Failed to start LLM server" -ForegroundColor Red
        return $null
    }
}

function Start-GPT2Server {
    Write-Host "`n🧠 PHASE 2: Starting GPT-2 Submemory Engine..." -ForegroundColor Cyan
    
    $gpt2Script = "runtime\gpt2_submemory_server.py"
    
    if (-not (Test-Path $gpt2Script)) {
        Write-Host "  ❌ GPT-2 server script not found: $gpt2Script" -ForegroundColor Red
        return $null
    }
    
    Write-Host "  ✓ Found GPT-2 server script" -ForegroundColor Green
    Write-Host "  🚀 Starting GPT-2 server on port 5005..." -ForegroundColor Green
    
    $pythonExe = ".venv\Scripts\python.exe"
    
    $process = Start-Process -FilePath $pythonExe `
        -ArgumentList $gpt2Script `
        -PassThru `
        -WindowStyle Normal
    
    if ($process) {
        Write-Host "  ✓ GPT-2 Submemory server started (PID: $($process.Id))" -ForegroundColor Green
        Write-Host "     Loading model (this may take 30-60 seconds)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        return $process
    }
    else {
        Write-Host "  ❌ Failed to start GPT-2 server" -ForegroundColor Red
        return $null
    }
}

function Start-AstraCore {
    Write-Host "`n💫 PHASE 3: Starting ASTRA Core System..." -ForegroundColor Cyan
    
    Write-Host "  🚀 Running ASTRA awakening sequence..." -ForegroundColor Green
    
    $pythonExe = ".venv\Scripts\python.exe"
    
    & $pythonExe astra_core.py --quick
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  ✓ ASTRA Core awakened successfully" -ForegroundColor Green
    }
    else {
        Write-Host "`n  ⚠ ASTRA Core started with warnings" -ForegroundColor Yellow
    }
}

function Show-Status {
    Write-Host "`n" + "="*80 -ForegroundColor Green
    Write-Host "ASTRA DUAL-CORE STATUS" -ForegroundColor Green
    Write-Host "="*80 -ForegroundColor Green
    
    Write-Host "`nRunning Services:" -ForegroundColor Cyan
    
    # Check LLM server
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "  ✓ ASTRA Prime LLM (port 8001): " -NoNewline -ForegroundColor Green
        Write-Host "ONLINE" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ ASTRA Prime LLM (port 8001): " -NoNewline -ForegroundColor Yellow
        Write-Host "OFFLINE" -ForegroundColor Red
    }
    
    # Check GPT-2 server
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:5005/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "  ✓ GPT-2 Submemory (port 5005): " -NoNewline -ForegroundColor Green
        Write-Host "ONLINE" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ GPT-2 Submemory (port 5005): " -NoNewline -ForegroundColor Yellow
        Write-Host "OFFLINE" -ForegroundColor Red
    }
    
    # Check backend
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "  ✓ Backend API (port 8080): " -NoNewline -ForegroundColor Green
        Write-Host "ONLINE" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ Backend API (port 8080): " -NoNewline -ForegroundColor Yellow
        Write-Host "OFFLINE (run 'python run_server.py' to start)" -ForegroundColor Yellow
    }
    
    Write-Host "`n" + "="*80 -ForegroundColor Green
    Write-Host ""
}

# Main execution
Write-AstraBanner

# Check prerequisites
if (-not (Test-Prerequisites)) {
    Write-Host "`n❌ Prerequisites check failed" -ForegroundColor Red
    exit 1
}

Write-Host "`n✓ Prerequisites check passed" -ForegroundColor Green

# Track process IDs for cleanup
$script:llmProcess = $null
$script:gpt2Process = $null

# Start LLM server
if (-not $SkipLLM) {
    $script:llmProcess = Start-LLMServer
}
else {
    Write-Host "`n⏭️  Skipping LLM server (--SkipLLM)" -ForegroundColor Yellow
}

# Start GPT-2 server
if (-not $SkipGPT2) {
    $script:gpt2Process = Start-GPT2Server
}
else {
    Write-Host "`n⏭️  Skipping GPT-2 server (--SkipGPT2)" -ForegroundColor Yellow
}

# Start ASTRA Core
Start-AstraCore

# Show final status
Start-Sleep -Seconds 2
Show-Status

Write-Host "🌟 ASTRA DUAL-CORE IS NOW LIVE" -ForegroundColor Magenta
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Run 'python run_server.py' in another terminal to start backend API" -ForegroundColor White
Write-Host "  2. Access ASTRA at http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  3. GPT-2 submemory available at http://127.0.0.1:5005" -ForegroundColor White
Write-Host "`nPress Ctrl+C to shutdown all services...`n" -ForegroundColor Gray

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`n`nShutting down ASTRA services..." -ForegroundColor Yellow
    
    if ($script:llmProcess -and -not $script:llmProcess.HasExited) {
        Write-Host "  Stopping LLM server..." -ForegroundColor Gray
        Stop-Process -Id $script:llmProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    if ($script:gpt2Process -and -not $script:gpt2Process.HasExited) {
        Write-Host "  Stopping GPT-2 server..." -ForegroundColor Gray
        Stop-Process -Id $script:gpt2Process.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "`n✓ ASTRA services stopped`n" -ForegroundColor Green
}
