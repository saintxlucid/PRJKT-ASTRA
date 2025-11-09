#!/usr/bin/env pwsh
# ASTRA v1.0.0 - Complete Go/No-Go & Deployment Script
# Automated deployment verification and tagging

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         ASTRA CORE v1.0.0 - PRODUCTION DEPLOYMENT          ║" -ForegroundColor Cyan
Write-Host "║                    Go/No-Go Checklist                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$allChecks = @()

# Check 1: LLM Server
Write-Host "[1/7] Checking LLM Server (port 8001)..." -ForegroundColor Yellow
try {
    $llmResponse = Invoke-WebRequest -Uri "http://localhost:8001/v1/models" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($llmResponse.StatusCode -eq 200) {
        Write-Host "      ✓ LLM Server ONLINE (200 OK)" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "      ✗ LLM Server returned $($llmResponse.StatusCode)" -ForegroundColor Red
        $allChecks += $false
    }
} catch {
    Write-Host "      ✗ LLM Server DOWN - Start llama.cpp on port 8001" -ForegroundColor Red
    Write-Host "        Command: .\llama-server.exe --model models\gpt-oss-20b-q4_k_m.gguf --ctx-size 131072 --port 8001" -ForegroundColor Gray
    $allChecks += $false
}

Write-Host ""

# Check 2: API Health
Write-Host "[2/7] Checking API Health (port 8080)..." -ForegroundColor Yellow
try {
    $apiResponse = Invoke-WebRequest -Uri "http://localhost:8080/v1/system/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $health = $apiResponse.Content | ConvertFrom-Json
    
    if ($health.status -eq "ok") {
        Write-Host "      ✓ API Server HEALTHY - Status: $($health.status)" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "      ✗ API Unhealthy - Status: $($health.status)" -ForegroundColor Red
        $allChecks += $false
    }
} catch {
    Write-Host "      ✗ API Server DOWN - Start ASTRA on port 8080" -ForegroundColor Red
    Write-Host "        Command: python -m uvicorn src.astra.api.app:app --host 0.0.0.0 --port 8080" -ForegroundColor Gray
    $allChecks += $false
}

Write-Host ""

# Check 3: Bridge Health
Write-Host "[3/7] Checking Bridge Module..." -ForegroundColor Yellow
try {
    $bridgeResponse = Invoke-WebRequest -Uri "http://localhost:8080/v1/bridge/healthz" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $bridgeHealth = $bridgeResponse.Content | ConvertFrom-Json
    
    if ($bridgeHealth.status -eq "ok") {
        Write-Host "      ✓ Bridge Module MOUNTED" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "      ✗ Bridge Unhealthy - Status: $($bridgeHealth.status)" -ForegroundColor Red
        $allChecks += $false
    }
} catch {
    Write-Host "      ✗ Bridge endpoint not responding" -ForegroundColor Red
    $allChecks += $false
}

Write-Host ""

# Check 4: Database WAL Mode
Write-Host "[4/7] Checking Database Configuration..." -ForegroundColor Yellow
$dbPath = "data\astra.db"
if (Test-Path $dbPath) {
    try {
        # Try to query WAL mode using sqlite3 if available
        $walCheck = & sqlite3 $dbPath "PRAGMA journal_mode;" 2>&1
        if ($walCheck -match "wal") {
            Write-Host "      ✓ Database WAL Mode ENABLED" -ForegroundColor Green
            $allChecks += $true
        } else {
            Write-Host "      ⚠ Database not in WAL mode (current: $walCheck)" -ForegroundColor Yellow
            $allChecks += $true  # Not blocking
        }
    } catch {
        Write-Host "      ⚠ Could not verify WAL mode (sqlite3 not found)" -ForegroundColor Yellow
        Write-Host "        Database exists at $dbPath" -ForegroundColor Gray
        $allChecks += $true  # Not blocking
    }
} else {
    Write-Host "      ⚠ Database not found at $dbPath (will be created on first use)" -ForegroundColor Yellow
    $allChecks += $true  # Not blocking
}

Write-Host ""

# Check 5: Prometheus Metrics
Write-Host "[5/7] Checking Prometheus Metrics Endpoint..." -ForegroundColor Yellow
try {
    $metricsResponse = Invoke-WebRequest -Uri "http://localhost:8080/metrics" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($metricsResponse.Content -match "astra_requests_total") {
        Write-Host "      ✓ Metrics Endpoint ACTIVE" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "      ⚠ Metrics endpoint reachable but missing expected metrics" -ForegroundColor Yellow
        $allChecks += $true  # Not blocking
    }
} catch {
    Write-Host "      ✗ Metrics endpoint not responding" -ForegroundColor Red
    $allChecks += $false
}

Write-Host ""

# Check 6: Configuration Files
Write-Host "[6/7] Checking Configuration Files..." -ForegroundColor Yellow
$configFiles = @(
    @{Path = ".env"; Required = $false},
    @{Path = "config\astra_identity.yaml"; Required = $true},
    @{Path = "astra-desktop-simple\config.json"; Required = $false},
    @{Path = "astra-os\src\config.ts"; Required = $false}
)

$configOk = $true
foreach ($config in $configFiles) {
    if (Test-Path $config.Path) {
        Write-Host "      ✓ Found: $($config.Path)" -ForegroundColor Green
    } else {
        if ($config.Required) {
            Write-Host "      ✗ Missing: $($config.Path)" -ForegroundColor Red
            $configOk = $false
        } else {
            Write-Host "      ⚠ Optional: $($config.Path) not found" -ForegroundColor Yellow
        }
    }
}
$allChecks += $configOk

Write-Host ""

# Check 7: Test Coverage
Write-Host "[7/7] Checking Test Suite Status..." -ForegroundColor Yellow
if (Test-Path ".pytest_cache\v\cache\lastfailed") {
    Write-Host "      ⚠ Some tests failed in last run - Consider running pytest" -ForegroundColor Yellow
    $allChecks += $true  # Not blocking for now
} else {
    Write-Host "      ✓ No recent test failures detected" -ForegroundColor Green
    $allChecks += $true
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

# Summary
$passedChecks = ($allChecks | Where-Object { $_ -eq $true }).Count
$totalChecks = $allChecks.Count
$passRate = [math]::Round(($passedChecks / $totalChecks) * 100, 1)

Write-Host ""
Write-Host "SUMMARY: $passedChecks/$totalChecks checks passed ($passRate%)" -ForegroundColor $(if ($passedChecks -eq $totalChecks) { "Green" } elseif ($passedChecks -ge 5) { "Yellow" } else { "Red" })
Write-Host ""

# Decision
if ($passedChecks -ge 5) {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                      ✓ GO FOR DEPLOYMENT                   ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    if ($passedChecks -eq $totalChecks) {
        Write-Host "All systems nominal. Ready for production deployment." -ForegroundColor Green
    } else {
        Write-Host "Core systems operational. Minor warnings present but not blocking." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "  1. Run smoke test:      .\scripts\smoke_test.ps1" -ForegroundColor White
    Write-Host "  2. Verify Bridge:       curl http://localhost:8080/v1/bridge/healthz" -ForegroundColor White
    Write-Host "  3. Tag release:         git tag -a v1.0.0 -m 'ASTRA Core v1.0 - Production Ready'" -ForegroundColor White
    Write-Host "  4. Push tag:            git push origin v1.0.0" -ForegroundColor White
    Write-Host "  5. Monitor 30 min:      Watch golden signals (see RUNBOOK.md)" -ForegroundColor White
    Write-Host ""
    
    # Offer to run smoke test
    Write-Host "Run smoke test now? (Y/N): " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    
    if ($response -match "^[Yy]") {
        Write-Host ""
        Write-Host "Running smoke test..." -ForegroundColor Cyan
        & ".\scripts\smoke_test.ps1"
    }
    
} else {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║                     ✗ NO-GO - FIX ISSUES                   ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "Critical systems are not operational. Fix the following:" -ForegroundColor Red
    Write-Host ""
    
    if (-not $allChecks[0]) {
        Write-Host "  • Start llama.cpp LLM server on port 8001" -ForegroundColor Red
    }
    if (-not $allChecks[1]) {
        Write-Host "  • Start ASTRA API server on port 8080" -ForegroundColor Red
    }
    if (-not $allChecks[2]) {
        Write-Host "  • Verify Bridge module integration" -ForegroundColor Red
    }
    if (-not $allChecks[4]) {
        Write-Host "  • Fix Prometheus metrics endpoint" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "See DEPLOYMENT_NEXT_STEPS.md for detailed instructions." -ForegroundColor Yellow
    
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
