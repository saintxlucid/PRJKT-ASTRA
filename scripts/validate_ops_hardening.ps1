# ASTRA Ops Hardening - Quick Validation Script
# Tests all new features: backups, request ID, API key auth

param(
    [string]$ApiKey = $env:ASTRA_API_KEY
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ASTRA Ops Hardening Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# Test 1: Backup script exists
Write-Host "[1/8] Checking backup script..." -ForegroundColor Yellow
if (Test-Path "scripts\backup_production.ps1") {
    Write-Host "      ✓ PASS: Backup script exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "      ✗ FAIL: Backup script not found" -ForegroundColor Red
    $failed++
}

# Test 2: QUICKSTART.md exists
Write-Host "[2/8] Checking QUICKSTART.md..." -ForegroundColor Yellow
if (Test-Path "QUICKSTART.md") {
    Write-Host "      ✓ PASS: QUICKSTART.md exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "      ✗ FAIL: QUICKSTART.md not found" -ForegroundColor Red
    $failed++
}

# Test 3: RUNBOOK.md exists
Write-Host "[3/8] Checking RUNBOOK.md..." -ForegroundColor Yellow
if (Test-Path "docs\RUNBOOK.md") {
    Write-Host "      ✓ PASS: docs\RUNBOOK.md exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "      ✗ FAIL: docs\RUNBOOK.md not found" -ForegroundColor Red
    $failed++
}

# Test 4: Grafana dashboard exists
Write-Host "[4/8] Checking Grafana dashboard..." -ForegroundColor Yellow
if (Test-Path "ops\grafana_astra_dashboard.json") {
    Write-Host "      ✓ PASS: Grafana dashboard JSON exists" -ForegroundColor Green
    $passed++
} else {
    Write-Host "      ✗ FAIL: Grafana dashboard not found" -ForegroundColor Red
    $failed++
}

# Test 5: Backend responding
Write-Host "[5/8] Checking backend health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "      ✓ PASS: Backend is responding" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "      ✗ FAIL: Backend returned status $($response.StatusCode)" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "      ✗ FAIL: Backend not responding (is it running?)" -ForegroundColor Red
    Write-Host "      Hint: Start with 'python run_server.py'" -ForegroundColor Yellow
    $failed++
}

# Test 6: Request ID in response
Write-Host "[6/8] Checking request ID tracing..." -ForegroundColor Yellow
try {
    $headers = @{}
    if ($ApiKey) {
        $headers["X-API-Key"] = $ApiKey
    }
    $response = Invoke-WebRequest -Uri "http://localhost:8080/v1/system/health" -Headers $headers -UseBasicParsing -TimeoutSec 5
    if ($response.Headers.ContainsKey("x-request-id")) {
        Write-Host "      ✓ PASS: Request ID present ($($response.Headers['x-request-id']))" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "      ✗ FAIL: No request ID header found" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "      ✗ FAIL: Could not test request ID" -ForegroundColor Red
    $failed++
}

# Test 7: API key auth (if enabled)
Write-Host "[7/8] Checking API key authentication..." -ForegroundColor Yellow
if ($ApiKey) {
    try {
        # Test with API key (should work)
        $response1 = Invoke-WebRequest -Uri "http://localhost:8080/v1/system/version" -Headers @{"X-API-Key" = $ApiKey} -UseBasicParsing -TimeoutSec 5
        
        # Test without API key on protected endpoint (should fail with 401)
        $response2Status = 200
        try {
            $response2 = Invoke-WebRequest -Uri "http://localhost:8080/v1/conversations/" -UseBasicParsing -TimeoutSec 5
            $response2Status = $response2.StatusCode
        } catch {
            $response2Status = $_.Exception.Response.StatusCode.Value__
        }
        
        if ($response1.StatusCode -eq 200 -and $response2Status -eq 401) {
            Write-Host "      ✓ PASS: API key auth working correctly" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "      ✗ FAIL: Auth not working (with key: $($response1.StatusCode), without: $response2Status)" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "      ✗ FAIL: Could not test API key auth" -ForegroundColor Red
        $failed++
    }
} else {
    Write-Host "      ⊘ SKIP: No API key configured (ASTRA_API_KEY not set)" -ForegroundColor Gray
}

# Test 8: Metrics accessible
Write-Host "[8/8] Checking metrics endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/metrics" -UseBasicParsing -TimeoutSec 5
    $content = $response.Content
    if ($content -match "astra_http_requests_total") {
        Write-Host "      ✓ PASS: Metrics endpoint accessible" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "      ✗ FAIL: Metrics endpoint not returning expected data" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "      ✗ FAIL: Could not access metrics endpoint" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Validation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✓ ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "Your operational hardening is complete and working!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Run backup manually: .\scripts\backup_production.ps1" -ForegroundColor White
    Write-Host "2. Schedule backup in Task Scheduler (see OPS_HARDENING_COMPLETE.md)" -ForegroundColor White
    Write-Host "3. Review docs\RUNBOOK.md for operational procedures" -ForegroundColor White
    exit 0
} else {
    Write-Host "⚠ SOME TESTS FAILED" -ForegroundColor Yellow
    Write-Host "Review the errors above and check:" -ForegroundColor Yellow
    Write-Host "- Is the backend running? (python run_server.py)" -ForegroundColor White
    Write-Host "- Is ASTRA_API_KEY set if you want auth?" -ForegroundColor White
    Write-Host "- Check backend logs for errors" -ForegroundColor White
    exit 1
}
