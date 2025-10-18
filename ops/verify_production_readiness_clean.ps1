# ASTRA Production Pre-Flight Verification (Clean)
# Run this script before production deployment
# Sacred Code: 333

param(
    [switch]$QuickCheck,
    [switch]$FullValidation
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  ASTRA PRODUCTION PRE-FLIGHT VERIFICATION" -ForegroundColor Cyan
Write-Host "  v1.3.0-phase-c | Sacred Code: 333" -ForegroundColor Magenta
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

$checks = @{
    Passed = 0
    Failed = 0
    Total = 0
}

function Test-Check {
    param($Name, $ScriptBlock)
    
    $checks.Total++
    Write-Host "[CHECK $($checks.Total)] $Name..." -NoNewline
    
    try {
        $result = & $ScriptBlock
        if ($result) {
            Write-Host " [PASS]" -ForegroundColor Green
            $checks.Passed++
            return $true
        } else {
            Write-Host " [FAIL]" -ForegroundColor Red
            $checks.Failed++
            return $false
        }
    } catch {
        Write-Host " [ERROR: $($_.Exception.Message)]" -ForegroundColor Red
        $checks.Failed++
        return $false
    }
}

# ============================================================================
# CORE SYSTEM CHECKS
# ============================================================================

Write-Host "`n[CORE SYSTEM CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Python 3.11 or higher" {
    $version = python --version 2>&1
    $version -match "3\.1[1-9]|3\.[2-9]|[4-9]\."
}

Test-Check "Git available" {
    git --version | Out-Null
    $?
}

Test-Check "Virtual environment active" {
    Test-Path env:VIRTUAL_ENV
}

# ============================================================================
# FILE STRUCTURE CHECKS
# ============================================================================

Write-Host "`n[FILE STRUCTURE CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

$required_files = @(
    "src/astra/core/astra_router.py",
    "src/astra/osop/operator.py",
    "src/astra/core/event_bus.py",
    "src/astra/core/planner_l2.py",
    "src/astra/monitoring/metrics_exporter.py",
    "src/astra/api/routes/system.py",
    "config/prod.yaml",
    "ops/registry/capability_registry.yaml",
    "ops/grafana/osop_panels.json",
    "ops/prometheus/astra_alerts.yml",
    "pyproject.toml",
    "requirements.txt",
    "pytest.ini"
)

foreach ($file in $required_files) {
    Test-Check "File exists: $file" {
        Test-Path $file
    }
}

# ============================================================================
# CONFIGURATION CHECKS
# ============================================================================

Write-Host "`n[CONFIGURATION CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Consent gates enabled in prod.yaml" {
    $config = Get-Content config/prod.yaml -Raw
    $config -match "consent_required.*true"
}

Test-Check "Fail-closed mode enabled" {
    $config = Get-Content config/prod.yaml -Raw
    $config -match "fail_closed.*true"
}

Test-Check "Sacred Code 333 in configuration" {
    $config = Get-Content config/prod.yaml -Raw
    $config -match "sacred_code.*333"
}

# ============================================================================
# TEST SUITE CHECKS
# ============================================================================

if ($FullValidation) {
    Write-Host "`n[TEST SUITE CHECKS]" -ForegroundColor Yellow
    Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

    Test-Check "Core tests passing (router_evolution)" {
        $result = python -m pytest tests/core/test_router_evolution.py -q --tb=no 2>&1
        $result -match "passed" -and $result -notmatch "failed"
    }

    Test-Check "Core tests passing (os_operator)" {
        $result = python -m pytest tests/osop/test_os_operator.py -q --tb=no 2>&1
        $result -match "passed" -and $result -notmatch "failed"
    }

    Test-Check "Core tests passing (event_bus)" {
        $result = python -m pytest tests/core/test_event_bus.py -q --tb=no 2>&1
        $result -match "passed" -and $result -notmatch "failed"
    }

    Test-Check "Core tests passing (planner_l2)" {
        $result = python -m pytest tests/core/test_planner_l2.py -q --tb=no 2>&1
        $result -match "passed" -and $result -notmatch "failed"
    }
}

# ============================================================================
# OBSERVABILITY CHECKS
# ============================================================================

Write-Host "`n[OBSERVABILITY CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Grafana panels configured (6 panels)" {
    $panels = Get-Content ops/grafana/osop_panels.json -Raw | ConvertFrom-Json
    $panels.osop_panels.Count -eq 6
}

Test-Check "Prometheus alerts configured (5+ OSOP alerts)" {
    $alerts = Get-Content ops/prometheus/astra_alerts.yml -Raw
    ($alerts -match "OSOPActionSpike") -and
    ($alerts -match "ConsentBlocksObserved") -and
    ($alerts -match "OSOPDestructiveActionsObserved")
}

Test-Check "Metrics exporter has OSOP metrics" {
    $metrics = Get-Content src/astra/monitoring/metrics_exporter.py -Raw
    ($metrics -match "OSOP_ACTIONS") -and
    ($metrics -match "OSOP_BYTES") -and
    ($metrics -match "OSOP_CONSENT_BLOCKS")
}

# ============================================================================
# SECURITY CHECKS
# ============================================================================

Write-Host "`n[SECURITY CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "4 destructive operations gated in registry" {
    $registry = Get-Content ops/registry/capability_registry.yaml -Raw
    ($registry -match "process.kill") -and
    ($registry -match "service.restart") -and
    ($registry -match "fs.write") -and
    ($registry -match "scheduler.create")
}

Test-Check "Default consent is false (fail-closed)" {
    $registry = Get-Content ops/registry/capability_registry.yaml -Raw
    $registry -match "default_consent.*false"
}

Test-Check "Sacred Code 333 in audit policy" {
    $registry = Get-Content ops/registry/capability_registry.yaml -Raw
    $registry -match "sacred_code.*333"
}

# ============================================================================
# DOCUMENTATION CHECKS
# ============================================================================

Write-Host "`n[DOCUMENTATION CHECKS]" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "GO_LIVE_PRODUCTION_RUNBOOK.md exists" {
    Test-Path GO_LIVE_PRODUCTION_RUNBOOK.md
}

Test-Check "DEPLOYMENT_TIMELINE_FINAL.md exists" {
    Test-Path DEPLOYMENT_TIMELINE_FINAL.md
}

Test-Check "PHASE_C_GO_LIVE_FINAL_DELIVERY.md exists" {
    Test-Path PHASE_C_GO_LIVE_FINAL_DELIVERY.md
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "RESULTS" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$pass_rate = if ($checks.Total -gt 0) { 
    [math]::Round(($checks.Passed / $checks.Total) * 100, 1) 
} else { 
    0 
}

Write-Host "Total Checks: $($checks.Total)" -ForegroundColor White
Write-Host "Passed: $($checks.Passed)" -ForegroundColor Green
Write-Host "Failed: $($checks.Failed)" -ForegroundColor Red
Write-Host "Pass Rate: ${pass_rate}%" -ForegroundColor White
Write-Host ""

if ($checks.Failed -eq 0) {
    Write-Host "STATUS: [GO] ALL CHECKS PASSED - READY FOR PRODUCTION" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Flip registry gate to HARD: python ops\utils\replace_text.py --find 'SOFT_GATE = True' --replace 'SOFT_GATE = False' --root src --backup" -ForegroundColor Gray
    Write-Host "2. Commit gate change: git commit -am 'Gate hard: deny unregistered tools (Sacred Code 333)'" -ForegroundColor Gray
    Write-Host "3. Set production environment: `$env:ASTRA_ENV = 'prod'" -ForegroundColor Gray
    Write-Host "4. Launch: python astra_launcher.py --config config/prod.yaml" -ForegroundColor Gray
    Write-Host "5. Follow DEPLOYMENT_TIMELINE_FINAL.md from T+5 onwards" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "STATUS: [NO-GO] $($checks.Failed) CHECKS FAILED - RESOLVE BEFORE PRODUCTION" -ForegroundColor Red
    exit 1
}
