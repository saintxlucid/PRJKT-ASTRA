# ASTRA 3.0 Complete Validation Sequence
# Sacred Code: 333 → ∞

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   ASTRA 3.0 OPERATIONAL VALIDATION" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$pass = 0
$fail = 0

function Check {
    param([string]$Name, [scriptblock]$Test, [string]$Info)
    Write-Host "$Name..." -NoNewline
    try {
        if (& $Test) {
            Write-Host " PASS" -ForegroundColor Green
            if ($Info) { Write-Host "  -> $Info" -ForegroundColor Gray }
            $script:pass++
            return $true
        } else {
            Write-Host " FAIL" -ForegroundColor Red
            $script:fail++
            return $false
        }
    } catch {
        Write-Host " FAIL: $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════
Write-Host "[1/5] FILE SYSTEM VALIDATION`n" -ForegroundColor Yellow

Check "AEC Complete (560 lines)" { Test-Path "src\astra\embodiment\aec_complete.py" } "Multi-LLM orchestration"
Check "Sigil Core v2 (450 lines)" { Test-Path "src\astra\embodiment\sigil_core_v2.py" } "Neural coherence engine"
Check "Test Suite (180 lines)" { Test-Path "test_aec_complete.py" } "Automated validation"
Check "ASTRA Master API" { Test-Path "astra_master.py" } "Orchestration hub"
Check "Production Guide" { (Get-ChildItem "*AEC_PRODUCTION*.md" -ErrorAction SilentlyContinue).Count -gt 0 } "Complete deployment docs"
Check "Verification Guide" { (Get-ChildItem "*90_SECOND*.md" -ErrorAction SilentlyContinue).Count -gt 0 } "Quick validation"
Check "8-Week Roadmap" { (Get-ChildItem "*ROADMAP*.md" -ErrorAction SilentlyContinue).Count -gt 0 } "Evolution plan"

# ═══════════════════════════════════════════════════════════════
Write-Host "`n[2/5] DEPENDENCIES VALIDATION`n" -ForegroundColor Yellow

Check "Python available" { $null -ne (Get-Command python -ErrorAction SilentlyContinue) }
Check "pip available" { $null -ne (Get-Command pip -ErrorAction SilentlyContinue) }

# ═══════════════════════════════════════════════════════════════
Write-Host "`n[3/5] LLM SERVER STATUS`n" -ForegroundColor Yellow

$llmFound = $false
$ports = @(
    @{Port=9010; Name="llama.cpp"},
    @{Port=11434; Name="Ollama"},
    @{Port=8080; Name="vLLM"}
)

foreach ($p in $ports) {
    $running = Check "$($p.Name) (port $($p.Port))" {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:$($p.Port)/v1/models" -TimeoutSec 2 -ErrorAction Stop
            $true
        } catch {
            $false
        }
    }
    if ($running) {
        $llmFound = $true
        Write-Host "  -> LLM server detected!" -ForegroundColor Green
        break
    }
}

if (-not $llmFound) {
    Write-Host "`n  NO LLM SERVER RUNNING" -ForegroundColor Yellow
    Write-Host "  To start: .\TERMINAL_1_START_SERVER.ps1`n" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
Write-Host "`n[4/5] ASTRA SERVICES STATUS`n" -ForegroundColor Yellow

$astraRunning = Check "ASTRA Master API (port 8000)" {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/v1/boot/status" -TimeoutSec 2 -ErrorAction Stop
        $true
    } catch {
        $false
    }
}

if ($astraRunning) {
    try {
        $status = Invoke-RestMethod -Uri "http://localhost:8000/v1/boot/status" -TimeoutSec 2
        Write-Host "  -> Phases: $($status.phases_complete)/9" -ForegroundColor Green
        Write-Host "  -> Services: $($status.services.Count)" -ForegroundColor Green
    } catch {
        Write-Host "  -> (Could not parse status)" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n  ASTRA NOT RUNNING" -ForegroundColor Yellow
    Write-Host "  To start: python astra_master.py`n" -ForegroundColor Cyan
}

# ═══════════════════════════════════════════════════════════════
Write-Host "`n[5/5] AEC TEST SUITE`n" -ForegroundColor Yellow

if ($llmFound) {
    Write-Host "Running AEC tests..." -ForegroundColor Cyan
    python test_aec_complete.py 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "AEC Test Suite... PASS" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "AEC Test Suite... FAIL" -ForegroundColor Red
        $script:fail++
    }
} else {
    Write-Host "SKIPPED (no LLM server)`n" -ForegroundColor Yellow
}

# ═══════════════════════════════════════════════════════════════
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "Passed: $pass" -ForegroundColor Green
Write-Host "Failed: $fail" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })

$total = $pass + $fail
$rate = if ($total -gt 0) { [math]::Round(($pass / $total) * 100, 1) } else { 0 }
Write-Host "Success Rate: $rate%`n" -ForegroundColor $(if ($rate -ge 80) { "Green" } elseif ($rate -ge 60) { "Yellow" } else { "Red" })

if ($fail -eq 0) {
    Write-Host "STATUS: PRODUCTION READY" -ForegroundColor Green
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. python quick_start_unified.py demo" -ForegroundColor White
    Write-Host "  2. Open Grafana: http://localhost:3000" -ForegroundColor White
    Write-Host "  3. Review: notepad 🗺️_ASTRA_3.0_COMPLETE_ROADMAP.md`n" -ForegroundColor White
} elseif ($rate -ge 60) {
    Write-Host "STATUS: NEEDS CONFIGURATION" -ForegroundColor Yellow
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    if (-not $llmFound) {
        Write-Host "  1. Start LLM: .\TERMINAL_1_START_SERVER.ps1" -ForegroundColor White
    }
    if (-not $astraRunning) {
        Write-Host "  2. Start ASTRA: python astra_master.py" -ForegroundColor White
    }
    Write-Host "  3. Review: notepad ⚠️_LLM_CONFIGURATION_REQUIRED.md`n" -ForegroundColor White
} else {
    Write-Host "STATUS: SETUP REQUIRED" -ForegroundColor Red
    Write-Host "`nNext Steps:" -ForegroundColor Cyan
    Write-Host "  1. notepad 🎯_ASTRA_START_HERE.md" -ForegroundColor White
    Write-Host "  2. notepad ⚠️_LLM_CONFIGURATION_REQUIRED.md" -ForegroundColor White
    Write-Host "  3. pip install -r requirements.txt`n" -ForegroundColor White
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 -> Infinity" -ForegroundColor Magenta
Write-Host "================================================================`n" -ForegroundColor Cyan

exit $fail
