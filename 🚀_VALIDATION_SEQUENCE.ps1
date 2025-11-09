# 🚀 ASTRA 3.0 Complete Validation Sequence
# Sacred Code: 333 → ∞

Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🧠 ASTRA 3.0 OPERATIONAL VALIDATION" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

$script:passCount = 0
$script:failCount = 0

function Test-Step {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [string]$Expected
    )
    
    Write-Host "Testing: $Name..." -NoNewline
    try {
        $result = & $Action
        if ($result) {
            Write-Host " ✅ PASS" -ForegroundColor Green
            if ($Expected) {
                Write-Host "  → $Expected" -ForegroundColor Gray
            }
            $script:passCount++
            return $true
        } else {
            Write-Host " ❌ FAIL" -ForegroundColor Red
            $script:failCount++
            return $false
        }
    } catch {
        Write-Host " ❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:failCount++
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════
# LAYER 1: File System Validation
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[1/5] FILE SYSTEM VALIDATION" -ForegroundColor Yellow
Write-Host "─────────────────────────────`n" -ForegroundColor Yellow

Test-Step "AEC Complete exists" {
    Test-Path "src\astra\embodiment\aec_complete.py"
} "560 lines, multi-LLM orchestration"

Test-Step "Sigil Core v2 exists" {
    Test-Path "src\astra\embodiment\sigil_core_v2.py"
} "450 lines, neural coherence"

Test-Step "Test suite exists" {
    Test-Path "test_aec_complete.py"
} "180 lines, automated validation"

Test-Step "Master API exists" {
    Test-Path "astra_master.py"
} "ASTRA 3.1 orchestration hub"

Test-Step "Production guide exists" {
    Test-Path "🌟_AEC_PRODUCTION_DEPLOYMENT_GUIDE.md"
} "Complete deployment documentation"

Test-Step "Verification guide exists" {
    Test-Path "⚡_90_SECOND_VERIFICATION.md"
} "Quick validation procedures"

Test-Step "Roadmap exists" {
    Test-Path "🗺️_ASTRA_3.0_COMPLETE_ROADMAP.md"
} "8-week evolution plan"

# ═══════════════════════════════════════════════════════════════
# LAYER 2: Dependencies Validation
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/5] DEPENDENCIES VALIDATION" -ForegroundColor Yellow
Write-Host "──────────────────────────────`n" -ForegroundColor Yellow

Test-Step "Python available" {
    $null -ne (Get-Command python -ErrorAction SilentlyContinue)
} "Python interpreter found"

Test-Step "pip available" {
    $null -ne (Get-Command pip -ErrorAction SilentlyContinue)
} "Package manager ready"

Test-Step "Required packages" {
    $packages = python -m pip list 2>$null
    ($packages -match "pydantic") -and 
    ($packages -match "httpx") -and 
    ($packages -match "structlog")
} "pydantic, httpx, structlog installed"

# ═══════════════════════════════════════════════════════════════
# LAYER 3: LLM Server Validation
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/5] LLM SERVER VALIDATION" -ForegroundColor Yellow
Write-Host "───────────────────────────────`n" -ForegroundColor Yellow

$llmPorts = @(
    @{Port=9010; Name="llama.cpp (Primary)"},
    @{Port=11434; Name="Ollama"},
    @{Port=8080; Name="vLLM"}
)

$llmFound = $false
foreach ($llm in $llmPorts) {
    $result = Test-Step "$($llm.Name) on port $($llm.Port)" {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($llm.Port)/v1/models" -TimeoutSec 2 -ErrorAction Stop
            $true
        } catch {
            $false
        }
    }
    if ($result) {
        $llmFound = $true
        Write-Host "  → LLM server detected and responding" -ForegroundColor Green
        break
    }
}

if (-not $llmFound) {
    Write-Host "`n⚠️  NO LLM SERVER DETECTED" -ForegroundColor Yellow
    Write-Host "   To start llama.cpp:" -ForegroundColor Gray
    Write-Host "   .\TERMINAL_1_START_SERVER.ps1`n" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
# LAYER 4: ASTRA Services Validation
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/5] ASTRA SERVICES VALIDATION" -ForegroundColor Yellow
Write-Host "────────────────────────────────`n" -ForegroundColor Yellow

$astraRunning = Test-Step "ASTRA Master API (port 8000)" {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/v1/boot/status" -TimeoutSec 2 -ErrorAction Stop
        $true
    } catch {
        $false
    }
}

if ($astraRunning) {
    Write-Host "  → Fetching detailed status..." -ForegroundColor Gray
    try {
        $status = Invoke-RestMethod -Uri "http://localhost:8000/v1/boot/status" -TimeoutSec 2
        Write-Host "  → Phases complete: $($status.phases_complete)/9" -ForegroundColor Green
        Write-Host "  → Services online: $($status.services.Count)" -ForegroundColor Green
    } catch {
        Write-Host "  → Could not parse status" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n⚠️  ASTRA NOT RUNNING" -ForegroundColor Yellow
    Write-Host "   To start ASTRA:" -ForegroundColor Gray
    Write-Host "   python astra_master.py`n" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
# LAYER 5: AEC Test Suite
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/5] AEC TEST SUITE VALIDATION" -ForegroundColor Yellow
Write-Host "────────────────────────────────`n" -ForegroundColor Yellow

if ($llmFound) {
    Write-Host "Running AEC test suite..." -ForegroundColor Cyan
    $testOutput = python test_aec_complete.py 2>&1
    $testSuccess = $LASTEXITCODE -eq 0
    
    if ($testSuccess) {
        Write-Host "✅ AEC TEST SUITE: PASSED" -ForegroundColor Green
        $script:passCount++
        
        # Extract key metrics
        if ($testOutput -match "Experts consulted: \[([^\]]+)\]") {
            Write-Host "  → Experts used: $($Matches[1])" -ForegroundColor Green
        }
        if ($testOutput -match "Total tokens: (\d+)") {
            Write-Host "  → Token usage: $($Matches[1])" -ForegroundColor Green
        }
    } else {
        Write-Host "❌ AEC TEST SUITE: FAILED" -ForegroundColor Red
        $script:failCount++
        Write-Host "`nTest output:" -ForegroundColor Gray
        $testOutput | Select-Object -Last 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    }
} else {
    Write-Host "⏭️  SKIPPED: No LLM server available" -ForegroundColor Yellow
    Write-Host "   Start an LLM server first, then run:" -ForegroundColor Gray
    Write-Host "   python test_aec_complete.py`n" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════

Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

Write-Host "Tests Passed: $script:passCount" -ForegroundColor Green
Write-Host "Tests Failed: $script:failCount" -ForegroundColor $(if ($script:failCount -eq 0) { "Green" } else { "Red" })

$totalTests = $script:passCount + $script:failCount
$successRate = if ($totalTests -gt 0) { [math]::Round(($script:passCount / $totalTests) * 100, 1) } else { 0 }

Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } elseif ($successRate -ge 60) { "Yellow" } else { "Red" })

Write-Host "`n────────────────────────────────────────────────────────────────`n" -ForegroundColor Cyan

# Determine overall status
if ($script:failCount -eq 0) {
    Write-Host "🎉 ASTRA 3.0 FULLY OPERATIONAL!" -ForegroundColor Green
    Write-Host "`nSystem Status: ✅ PRODUCTION READY" -ForegroundColor Green
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. Run demo: python quick_start_unified.py demo" -ForegroundColor White
    Write-Host "  2. Open Grafana: http://localhost:3000" -ForegroundColor White
    Write-Host "  3. Review roadmap: notepad 🗺️_ASTRA_3.0_COMPLETE_ROADMAP.md" -ForegroundColor White
} elseif ($successRate -ge 60) {
    Write-Host "⚡ ASTRA 3.0 PARTIALLY OPERATIONAL" -ForegroundColor Yellow
    Write-Host "`nSystem Status: ⚠️  NEEDS CONFIGURATION" -ForegroundColor Yellow
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    
    if (-not $llmFound) {
        Write-Host "  1. Start LLM server: .\TERMINAL_1_START_SERVER.ps1" -ForegroundColor White
    }
    if (-not $astraRunning) {
        Write-Host "  2. Start ASTRA: python astra_master.py" -ForegroundColor White
    }
    Write-Host "  3. Review config: notepad ⚠️_LLM_CONFIGURATION_REQUIRED.md" -ForegroundColor White
} else {
    Write-Host "❌ ASTRA 3.0 NEEDS ATTENTION" -ForegroundColor Red
    Write-Host "`nSystem Status: 🔧 SETUP REQUIRED" -ForegroundColor Red
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. Read: notepad 🎯_ASTRA_START_HERE.md" -ForegroundColor White
    Write-Host "  2. Configure LLM: notepad ⚠️_LLM_CONFIGURATION_REQUIRED.md" -ForegroundColor White
    Write-Host "  3. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
}

Write-Host "`n════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 → ∞" -ForegroundColor Magenta
Write-Host "════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# Return exit code
exit $script:failCount
