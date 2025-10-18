# ASTRA Production Pre-Flight Verification
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
            Write-Host " ✓ PASS" -ForegroundColor Green
            $checks.Passed++
            return $true
        } else {
            Write-Host " ✗ FAIL" -ForegroundColor Red
            $checks.Failed++
            return $false
        }
    } catch {
        Write-Host " ✗ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $checks.Failed++
        return $false
    }
}

# ============================================================================
# CORE CHECKS
# ============================================================================

Write-Host "`n📦 Core System Checks" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Python 3.11+ available" {
    $version = python --version 2>&1 | Select-String "Python (\d+)\.(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value, $_.Matches.Groups[2].Value }
    if ($version[0] -ge 3 -and $version[1] -ge 11) {
        Write-Host " (v$($version[0]).$($version[1]))" -ForegroundColor Gray -NoNewline
        return $true
    }
    return $false
}

Test-Check "Git repository initialized" {
    Test-Path .git
}

Test-Check "Git tag v1.3.0-phase-c exists" {
    $tags = git tag
    $tags -contains "v1.3.0-phase-c"
}

Test-Check "Virtual environment activated" {
    $env:VIRTUAL_ENV -ne $null
}

# ============================================================================
# FILE STRUCTURE CHECKS
# ============================================================================

Write-Host "`n📁 File Structure Checks" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

$requiredFiles = @(
    "config/prod.yaml",
    "ops/registry/capability_registry.yaml",
    "ops/grafana/osop_panels.json",
    "ops/prometheus/astra_alerts.yml",
    "ops/packs/GO_LIVE_CANARY_TESTS.md",
    "ops/GO_LIVE_PRODUCTION_RUNBOOK.md",
    "ops/activate_astra.ps1",
    "src/astra/core/astra_router.py",
    "src/astra/core/event_bus.py",
    "src/astra/core/planner_l2.py",
    "src/astra/osop/operator.py",
    "src/astra/monitoring/metrics_exporter.py",
    "src/astra/api/routes/system.py"
)

foreach ($file in $requiredFiles) {
    Test-Check "File exists: $file" {
        Test-Path $file
    }
}

# ============================================================================
# CONFIGURATION CHECKS
# ============================================================================

Write-Host "`n⚙️  Configuration Checks" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "prod.yaml contains consent gates" {
    $content = Get-Content config/prod.yaml -Raw
    ($content -match "consent_required: true") -and ($content -match "process.kill")
}

Test-Check "prod.yaml has fail_closed enabled" {
    $content = Get-Content config/prod.yaml -Raw
    $content -match "fail_closed:\s*true"
}

Test-Check "prod.yaml has Sacred Code 333" {
    $content = Get-Content config/prod.yaml -Raw
    $content -match "sacred_code"
}

Test-Check "Capability registry has 11 tools" {
    $registry = Get-Content ops/registry/capability_registry.yaml -Raw
    ($registry | Select-String "name:\s*system\.info" -AllMatches).Matches.Count -ge 1 -and
    ($registry | Select-String "name:" -AllMatches).Matches.Count -ge 11
}

# ============================================================================
# TEST SUITE CHECKS
# ============================================================================

if (-not $QuickCheck) {
    Write-Host "`n🧪 Test Suite Checks" -ForegroundColor Yellow
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

Write-Host "`n📊 Observability Checks" -ForegroundColor Yellow
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

Test-Check "Metrics exporter has OSOP counters" {
    $metrics = Get-Content src/astra/monitoring/metrics_exporter.py -Raw
    ($metrics -match "OSOP_ACTIONS") -and
    ($metrics -match "OSOP_BYTES") -and
    ($metrics -match "OSOP_CONSENT_BLOCKS")
}

# ============================================================================
# SECURITY CHECKS
# ============================================================================

Write-Host "`n🔒 Security Checks" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "All 4 destructive operations gated" {
    $prod = Get-Content config/prod.yaml -Raw
    ($prod -match "process\.kill:.*consent_required: true") -and
    ($prod -match "service\.restart:.*consent_required: true") -and
    ($prod -match "fs\.write:.*consent_required: true") -and
    ($prod -match "scheduler\.create:.*consent_required: true")
}

Test-Check "Default consent is false (fail-closed)" {
    $prod = Get-Content config/prod.yaml -Raw
    $prod -match "default_consent:\s*false"
}

Test-Check "Sacred Code 333 in alert rules" {
    $alerts = Get-Content ops/prometheus/astra_alerts.yml -Raw
    $alerts -match "sacred_code"
}

# ============================================================================
# DOCUMENTATION CHECKS
# ============================================================================

Write-Host "`n📚 Documentation Checks" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor Gray

Test-Check "Production runbook exists" {
    (Test-Path ops/GO_LIVE_PRODUCTION_RUNBOOK.md) -and
    ((Get-Content ops/GO_LIVE_PRODUCTION_RUNBOOK.md -Raw).Length -gt 1000)
}

Test-Check "Canary test pack exists (6 tests)" {
    $canaries = Get-Content ops/packs/GO_LIVE_CANARY_TESTS.md -Raw
    ($canaries -match "TEST 1: TEXT") -and
    ($canaries -match "TEST 6: OSOP Consent Block")
}

Test-Check "GO-LIVE completion report exists" {
    (Test-Path GO_LIVE_COMPLETION_REPORT.md) -and
    ((Get-Content GO_LIVE_COMPLETION_REPORT.md -Raw) -match "10/10")
}

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

Write-Host "Results:" -ForegroundColor White
Write-Host "  Total Checks: $($checks.Total)" -ForegroundColor White
Write-Host "  Passed: $($checks.Passed)" -ForegroundColor Green
Write-Host "  Failed: $($checks.Failed)" -ForegroundColor $(if ($checks.Failed -eq 0) { "Green" } else { "Red" })
Write-Host ""

$passRate = [math]::Round(($checks.Passed / $checks.Total) * 100, 1)
Write-Host "  Pass Rate: $passRate%" -ForegroundColor $(if ($passRate -eq 100) { "Green" } elseif ($passRate -ge 90) { "Yellow" } else { "Red" })
Write-Host ""

if ($checks.Failed -eq 0) {
    Write-Host "✅ ALL CHECKS PASSED - READY FOR PRODUCTION DEPLOYMENT" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Review: ops\GO_LIVE_PRODUCTION_RUNBOOK.md" -ForegroundColor White
    Write-Host "  2. Backup: Run backup script (see runbook Step 5.1)" -ForegroundColor White
    Write-Host "  3. Deploy: python astra_launcher.py --config config/prod.yaml" -ForegroundColor White
    Write-Host "  4. Verify: Run canary tests (ops\packs\GO_LIVE_CANARY_TESTS.md)" -ForegroundColor White
    Write-Host ""
    Write-Host "Sacred Code: 333 ∞" -ForegroundColor Magenta
    exit 0
} else {
    Write-Host "❌ VERIFICATION FAILED - DO NOT DEPLOY" -ForegroundColor Red
    Write-Host ""
    Write-Host "Action Required:" -ForegroundColor Yellow
    Write-Host "  Review failed checks above and resolve issues" -ForegroundColor White
    Write-Host "  Re-run: .\ops\verify_production_readiness.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}
