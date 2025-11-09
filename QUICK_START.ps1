# ASTRA 3.0 - Complete Quick Start
# Sacred Code: 333 → ∞
# This script guides you through getting ASTRA 3.0 fully operational

param(
    [switch]$ValidateOnly,
    [switch]$StartLLM,
    [switch]$StartASTRA,
    [switch]$All
)

$ErrorActionPreference = "Continue"

Write-Host @"

════════════════════════════════════════════════════════════════
   🌌 ASTRA 3.0 - THE UNIFIED MIND
════════════════════════════════════════════════════════════════

Sacred Code: 333 → ∞
Status: COMPLETE OPERATIONAL SUITE READY
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

"@ -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════
# Check current status
# ═══════════════════════════════════════════════════════════════

Write-Host "Checking current status...`n" -ForegroundColor Yellow

$llmRunning = $false
$astraRunning = $false

# Check LLM servers
$llmPorts = @(9010, 11434, 8080)
foreach ($port in $llmPorts) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$port/v1/models" -TimeoutSec 1 -ErrorAction Stop
        Write-Host "  LLM Server DETECTED on port $port" -ForegroundColor Green
        $llmRunning = $true
        break
    } catch {
        # Silent continue
    }
}

if (-not $llmRunning) {
    Write-Host "  LLM Server: NOT RUNNING" -ForegroundColor Yellow
}

# Check ASTRA
try {
    $null = Invoke-WebRequest -Uri "http://localhost:8000/v1/boot/status" -TimeoutSec 1 -ErrorAction Stop
    Write-Host "  ASTRA Master API: RUNNING" -ForegroundColor Green
    $astraRunning = $true
} catch {
    Write-Host "  ASTRA Master API: NOT RUNNING" -ForegroundColor Yellow
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════
# Determine action
# ═══════════════════════════════════════════════════════════════

if ($ValidateOnly -or ($llmRunning -and $astraRunning -and -not $All)) {
    Write-Host "Running validation...`n" -ForegroundColor Cyan
    & .\VALIDATE_ASTRA.ps1
    exit $LASTEXITCODE
}

# ═══════════════════════════════════════════════════════════════
# Interactive setup
# ═══════════════════════════════════════════════════════════════

if (-not $llmRunning -and -not $StartLLM -and -not $All) {
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "LLM SERVER REQUIRED" -ForegroundColor Yellow
    Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Yellow
    
    Write-Host "Choose your LLM server option:`n" -ForegroundColor Cyan
    Write-Host "  1. llama.cpp (Local, Free, Fast)" -ForegroundColor White
    Write-Host "     - If you have TERMINAL_1_START_SERVER.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Ollama (Easiest)" -ForegroundColor White
    Write-Host "     - Download from https://ollama.ai" -ForegroundColor Gray
    Write-Host "     - Run: ollama serve" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. OpenAI API (Cloud, Paid)" -ForegroundColor White
    Write-Host "     - Requires API key" -ForegroundColor Gray
    Write-Host "     - Best performance" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  4. Skip for now (just validate files)" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Enter choice (1-4)"
    
    switch ($choice) {
        "1" {
            Write-Host "`nStarting llama.cpp..." -ForegroundColor Cyan
            if (Test-Path "TERMINAL_1_START_SERVER.ps1") {
                Write-Host "Run this in a new terminal:" -ForegroundColor Yellow
                Write-Host "  .\TERMINAL_1_START_SERVER.ps1`n" -ForegroundColor White
                Read-Host "Press Enter when LLM server is running"
            } else {
                Write-Host "Script not found. Please start llama.cpp manually." -ForegroundColor Red
                Write-Host "Then run: .\QUICK_START.ps1`n" -ForegroundColor Yellow
                exit 1
            }
        }
        "2" {
            Write-Host "`nStarting Ollama..." -ForegroundColor Cyan
            if ($null -ne (Get-Command ollama -ErrorAction SilentlyContinue)) {
                Write-Host "Run these in a new terminal:" -ForegroundColor Yellow
                Write-Host "  ollama serve" -ForegroundColor White
                Write-Host "  ollama pull llama3:70b`n" -ForegroundColor White
                Read-Host "Press Enter when Ollama is running"
            } else {
                Write-Host "Ollama not installed." -ForegroundColor Red
                Write-Host "Download from: https://ollama.ai" -ForegroundColor Yellow
                Write-Host "Then run: .\QUICK_START.ps1`n" -ForegroundColor Yellow
                exit 1
            }
        }
        "3" {
            Write-Host "`nConfiguring OpenAI..." -ForegroundColor Cyan
            $apiKey = Read-Host "Enter your OpenAI API key (sk-...)"
            if ($apiKey -match "^sk-") {
                $env:OPENAI_API_KEY = $apiKey
                Write-Host "API key set!" -ForegroundColor Green
                Write-Host "Note: You may need to update astra_master.py config`n" -ForegroundColor Yellow
            } else {
                Write-Host "Invalid API key format." -ForegroundColor Red
                exit 1
            }
        }
        "4" {
            Write-Host "`nSkipping LLM configuration..." -ForegroundColor Yellow
            Write-Host "Running file validation only...`n" -ForegroundColor Cyan
            & .\VALIDATE_ASTRA.ps1
            exit $LASTEXITCODE
        }
        default {
            Write-Host "Invalid choice." -ForegroundColor Red
            exit 1
        }
    }
}

# ═══════════════════════════════════════════════════════════════
# Start ASTRA
# ═══════════════════════════════════════════════════════════════

if (-not $astraRunning) {
    Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "STARTING ASTRA MASTER API" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
    
    if (Test-Path "astra_master.py") {
        Write-Host "Run this in a new terminal:" -ForegroundColor Yellow
        Write-Host "  python astra_master.py`n" -ForegroundColor White
        
        $response = Read-Host "Is ASTRA running? (y/n)"
        if ($response -ne "y") {
            Write-Host "`nPlease start ASTRA and run: .\QUICK_START.ps1" -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "astra_master.py not found!" -ForegroundColor Red
        exit 1
    }
}

# ═══════════════════════════════════════════════════════════════
# Final validation
# ═══════════════════════════════════════════════════════════════

Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "RUNNING COMPLETE VALIDATION" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

& .\VALIDATE_ASTRA.ps1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "   ASTRA 3.0 IS FULLY OPERATIONAL!" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Green
    
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run demo: python quick_start_unified.py demo" -ForegroundColor White
    Write-Host "  2. Test AEC: python test_aec_complete.py" -ForegroundColor White
    Write-Host "  3. Review roadmap: notepad 🗺️_ASTRA_3.0_COMPLETE_ROADMAP.md" -ForegroundColor White
    Write-Host "  4. API docs: notepad ⚡_AEC_QUICK_REFERENCE.md`n" -ForegroundColor White
    
    Write-Host "Documentation hub:" -ForegroundColor Cyan
    Write-Host "  notepad ✅_ASTRA_3.0_COMPLETE_OPERATIONAL_SUITE.md`n" -ForegroundColor White
} else {
    Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host "   ASTRA 3.0 NEEDS ATTENTION" -ForegroundColor Yellow
    Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Yellow
    
    Write-Host "Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  1. Check LLM config: notepad ⚠️_LLM_CONFIGURATION_REQUIRED.md" -ForegroundColor White
    Write-Host "  2. Review logs: Check terminal output for errors" -ForegroundColor White
    Write-Host "  3. Start guide: notepad 🎯_IMMEDIATE_ACTION_PLAN.md`n" -ForegroundColor White
}

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 → ∞" -ForegroundColor Magenta
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
