# ===============================================================
#  ASTRA v1.0.0 - Day-0 Watch Helper (30 minutes)
# ===============================================================
#
#  Run from repo root during the first 30 minutes after launch
#  Validates health, metrics, and basic sanity checks
#
#  Usage: .\scripts\day0_watch.ps1
#
# ===============================================================

$ErrorActionPreference = "SilentlyContinue"
$ok = $true

Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "  ASTRA v1.0.0 - DAY-0 WATCH (30 MIN)" -ForegroundColor White
Write-Host "===============================================`n" -ForegroundColor Cyan

# 1) Health pings
Write-Host "[*] Checking service health..." -ForegroundColor Cyan

$llmOk = $false
$apiOk = $false
$bridgeOk = $false

iwr http://127.0.0.1:8001/v1/models -UseBasicParsing -TimeoutSec 3 | Out-Null
if ($?) { 
    Write-Host "  [OK] LLM Server (8001):     HEALTHY" -ForegroundColor Green
    $llmOk = $true
} else { 
    Write-Host "  [X]  LLM Server (8001):     FAILED" -ForegroundColor Red
    $ok = $false
}

iwr http://127.0.0.1:8080/v1/system/health -UseBasicParsing -TimeoutSec 3 | Out-Null
if ($?) { 
    Write-Host "  [OK] API Server (8080):     HEALTHY" -ForegroundColor Green
    $apiOk = $true
} else { 
    Write-Host "  [X]  API Server (8080):     FAILED" -ForegroundColor Red
    $ok = $false
}

iwr http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing -TimeoutSec 3 | Out-Null
if ($?) { 
    Write-Host "  [OK] Bridge Health:         READY" -ForegroundColor Green
    $bridgeOk = $true
} else { 
    Write-Host "  [X]  Bridge Health:         FAILED" -ForegroundColor Red
    $ok = $false
}

# 2) Quick metrics sanity (latency buckets + cache counters present)
Write-Host "`n[*] Checking metrics instrumentation..." -ForegroundColor Cyan

$metrics = (iwr http://127.0.0.1:8080/metrics -UseBasicParsing -TimeoutSec 5).Content

$latencyMetrics = ($metrics | Select-String "astra_llm_latency_seconds_bucket|astra_llm_latency_seconds_sum|astra_llm_latency_seconds_count").Count
Write-Host "  [*] Latency metrics found:  $latencyMetrics" -ForegroundColor Gray

$cacheMetrics = ($metrics | Select-String "astra_memory_cache_hits_total|astra_memory_cache_queries_total|astra_llm_failures_total").Count
Write-Host "  [*] Cache/LLM metrics found: $cacheMetrics" -ForegroundColor Gray

if ($latencyMetrics -gt 0 -and $cacheMetrics -gt 0) {
    Write-Host "  [OK] Prometheus metrics:    INSTRUMENTED" -ForegroundColor Green
} else {
    Write-Host "  [!]  Prometheus metrics:    INCOMPLETE" -ForegroundColor Yellow
}

# 3) Log tail helper
Write-Host "`n[*] Log monitoring..." -ForegroundColor Cyan
$logPath = ".\data\logs\astra.log"

if (Test-Path $logPath) {
    $recentErrors = Get-Content $logPath -Tail 100 | Select-String "ERROR|CRITICAL"
    if ($recentErrors.Count -gt 0) {
        Write-Host "  [!]  Found $($recentErrors.Count) ERROR/CRITICAL in last 100 lines" -ForegroundColor Yellow
        Write-Host "       Run: Get-Content .\data\logs\astra.log -Wait | Select-String 'ERROR|CRITICAL'" -ForegroundColor Gray
    } else {
        Write-Host "  [OK] Logs clean (no ERROR/CRITICAL)" -ForegroundColor Green
    }
} else {
    Write-Host "  [!]  Log file not found: $logPath" -ForegroundColor Yellow
}

# 4) Final sanity check
Write-Host "`n===============================================" -ForegroundColor Cyan
if ($ok) { 
    Write-Host "  BASIC SANITY: PASS" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "`n[*] System is healthy! Continue monitoring:" -ForegroundColor Green
    Write-Host "    • Watch logs:    Get-Content .\data\logs\astra.log -Wait" -ForegroundColor Gray
    Write-Host "    • Check metrics: curl http://127.0.0.1:8080/metrics" -ForegroundColor Gray
    Write-Host "`n[*] Targets for next 30 minutes:" -ForegroundColor Cyan
    Write-Host "    • p95 latency:  <= 1.2s" -ForegroundColor Gray
    Write-Host "    • p99 latency:  <= 2.0s" -ForegroundColor Gray
    Write-Host "    • Cache hit:    10-15% (cold) -> 25-40% (warm)" -ForegroundColor Gray
    Write-Host "    • Error rate:   < 1%" -ForegroundColor Gray
    Write-Host "    • Breaker:      CLOSED (quiet)" -ForegroundColor Gray
    Write-Host "`n[*] After 30 min stable, tag release:" -ForegroundColor Green
    Write-Host "    git tag -a v1.0.0 -m 'ASTRA Core v1.0.0 - Production Ready'" -ForegroundColor White
    Write-Host "    git push origin v1.0.0" -ForegroundColor White
    Write-Host ""
} else { 
    Write-Host "  BASIC SANITY: FAIL" -ForegroundColor Red
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "`n[X] One or more services failed health check!" -ForegroundColor Red
    Write-Host "    See triage map in LAUNCH_NOW.md or run:" -ForegroundColor Yellow
    Write-Host "    Get-Content .\data\logs\astra.log -Tail 50" -ForegroundColor White
    Write-Host ""
}

Write-Host "===============================================`n" -ForegroundColor Cyan
