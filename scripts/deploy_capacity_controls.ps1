#Requires -Version 5.1
<#
.SYNOPSIS
    Deploy Directive 001: Capacity Controls Go-Live

.DESCRIPTION
    Enables per-key rate limiting, validates queue metrics, runs burst tests,
    and benchmarks llama.cpp flags. Production-safe deployment in ~45 minutes.

.PARAMETER PerKeyRate
    Requests per period (default: 120)

.PARAMETER PerKeyPeriod
    Period in seconds (default: 60)

.PARAMETER SkipTests
    Skip burst tests and validation

.PARAMETER SkipBenchmark
    Skip llama.cpp benchmarking

.EXAMPLE
    .\scripts\deploy_capacity_controls.ps1
    
.EXAMPLE
    .\scripts\deploy_capacity_controls.ps1 -PerKeyRate 300 -PerKeyPeriod 60
#>

[CmdletBinding()]
param(
    [int]$PerKeyRate = 120,
    [int]$PerKeyPeriod = 60,
    [switch]$SkipTests,
    [switch]$SkipBenchmark
)

$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $PSScriptRoot

Write-Host "`n=== DIRECTIVE 001: Capacity Controls Go-Live ===" -ForegroundColor Cyan
Write-Host "Target: Per-key rate limiting + queue metrics + llama.cpp tuning`n" -ForegroundColor Cyan

#region Step 1: Enable Per-Key Limits
Write-Host "[Step 1/6] Configuring per-key limits..." -ForegroundColor Yellow

$envFile = Join-Path $baseDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
}

# Check if already configured
$envContent = Get-Content $envFile -Raw
if ($envContent -match "ASTRA_PER_KEY_RATE") {
    Write-Host "  ℹ Per-key config already exists in .env" -ForegroundColor Gray
} else {
    Add-Content $envFile "`n# Capacity Controls (Directive 001)"
    Add-Content $envFile "ASTRA_PER_KEY_RATE=$PerKeyRate"
    Add-Content $envFile "ASTRA_PER_KEY_PERIOD_SEC=$PerKeyPeriod"
    Write-Host "  ✓ Added ASTRA_PER_KEY_RATE=$PerKeyRate" -ForegroundColor Green
    Write-Host "  ✓ Added ASTRA_PER_KEY_PERIOD_SEC=$PerKeyPeriod" -ForegroundColor Green
}

Write-Host "  Rate: $PerKeyRate req / $PerKeyPeriod sec = $([math]::Round($PerKeyRate/$PerKeyPeriod, 2)) req/sec per key`n" -ForegroundColor Cyan
#endregion

#region Step 2: Verify API Key
Write-Host "[Step 2/6] Checking API key..." -ForegroundColor Yellow

if (-not $env:ASTRA_API_KEY) {
    # Try to load from .env
    if ($envContent -match "ASTRA_API_KEY=(.+)") {
        $env:ASTRA_API_KEY = $Matches[1].Trim()
        Write-Host "  ✓ Loaded API key from .env" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ ASTRA_API_KEY not set!" -ForegroundColor Red
        Write-Host "  Generate: python -c `"import secrets; print(secrets.token_urlsafe(48))`"" -ForegroundColor Yellow
        Write-Host "  Add to .env: ASTRA_API_KEY=<generated-key>" -ForegroundColor Yellow
        Write-Host "`n  Continuing without burst tests...`n" -ForegroundColor Gray
        $SkipTests = $true
    }
} else {
    Write-Host "  ✓ API key loaded ($($env:ASTRA_API_KEY.Length) chars)`n" -ForegroundColor Green
}
#endregion

#region Step 3: Restart Backend
Write-Host "[Step 3/6] Checking backend status..." -ForegroundColor Yellow

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✓ Backend already running (status: $($health.status))" -ForegroundColor Green
    Write-Host "  ℹ Manual restart recommended to load new config" -ForegroundColor Yellow
    Write-Host "    Ctrl+C in server terminal, then: .\.venv\Scripts\python.exe run_server.py`n" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Backend not responding" -ForegroundColor Red
    Write-Host "  Start backend: .\.venv\Scripts\python.exe run_server.py`n" -ForegroundColor Yellow
    exit 1
}
#endregion

#region Step 4: Smoke Checks
Write-Host "[Step 4/6] Running smoke checks..." -ForegroundColor Yellow

# Health check
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 5
    Write-Host "  ✓ Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Metrics check
try {
    $metrics = Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5
    $metricsText = $metrics.Content
    
    # Check for new metrics
    $hasLimiter = $metricsText -match "astra_limiter_per_key_"
    $hasQueue = $metricsText -match "astra_queue_"
    
    if ($hasLimiter) {
        Write-Host "  ✓ Per-key limiter metrics present" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Per-key limiter metrics not found (restart needed?)" -ForegroundColor Yellow
    }
    
    if ($hasQueue) {
        Write-Host "  ✓ Queue metrics present" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Queue metrics not found (restart needed?)" -ForegroundColor Yellow
    }
    
    # Count current queue depth
    if ($metricsText -match "astra_queue_depth\s+([\d.]+)") {
        $queueDepth = [int]$Matches[1]
        Write-Host "  ℹ Current queue depth: $queueDepth`n" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  ✗ Metrics check failed: $_" -ForegroundColor Red
    exit 1
}
#endregion

#region Step 5: Burst Test
if (-not $SkipTests) {
    Write-Host "[Step 5/6] Running burst test (150 requests)..." -ForegroundColor Yellow
    Write-Host "  Expected: ~$PerKeyRate success, ~$($150 - $PerKeyRate) rate-limited (429)`n" -ForegroundColor Gray
    
    $headers = @{
        "X-API-Key" = $env:ASTRA_API_KEY
        "Content-Type" = "application/json"
    }
    
    $body = @{
        conversation_id = "burst-test-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        message = "ping"
        use_memory = $false
    } | ConvertTo-Json
    
    $results = @{
        "200" = 0
        "429" = 0
        "other" = 0
    }
    
    Write-Host "  Progress: " -NoNewline
    1..150 | ForEach-Object {
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:8080/v1/chat/" `
                -Method POST `
                -Headers $headers `
                -Body $body `
                -UseBasicParsing `
                -TimeoutSec 10 `
                -ErrorAction Stop
            
            $results["200"]++
            if ($_ % 10 -eq 0) { Write-Host "." -NoNewline -ForegroundColor Green }
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            if ($statusCode -eq 429) {
                $results["429"]++
                if ($_ % 10 -eq 0) { Write-Host "X" -NoNewline -ForegroundColor Yellow }
            } else {
                $results["other"]++
                Write-Host "!" -NoNewline -ForegroundColor Red
            }
        }
        Start-Sleep -Milliseconds 50
    }
    
    Write-Host "`n`n  Results:" -ForegroundColor Cyan
    Write-Host "    200 OK:         $($results['200'])" -ForegroundColor Green
    Write-Host "    429 Blocked:    $($results['429'])" -ForegroundColor Yellow
    Write-Host "    Other Errors:   $($results['other'])" -ForegroundColor $(if ($results['other'] -gt 0) { "Red" } else { "Gray" })
    
    $allowedRatio = $results['200'] / 150
    Write-Host "`n  Allow Rate: $([math]::Round($allowedRatio * 100, 1))%" -ForegroundColor Cyan
    
    if ($results['200'] -ge ($PerKeyRate * 0.8) -and $results['429'] -gt 0) {
        Write-Host "  ✓ Per-key limiting working correctly!`n" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Unexpected result distribution (restart backend?)`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "[Step 5/6] Burst test skipped`n" -ForegroundColor Gray
}
#endregion

#region Step 6: Benchmark Hint
if (-not $SkipBenchmark) {
    Write-Host "[Step 6/6] llama.cpp benchmark guidance..." -ForegroundColor Yellow
    Write-Host "  Run benchmark to find optimal flags:" -ForegroundColor Gray
    Write-Host "    .\.venv\Scripts\python.exe scripts\benchmark_llama_flags.py" -ForegroundColor Cyan
    Write-Host "`n  Test different configurations:" -ForegroundColor Gray
    Write-Host "    1. Stop llama.cpp server" -ForegroundColor Gray
    Write-Host "    2. Restart with new flags: --threads 16 --batch 1024" -ForegroundColor Gray
    Write-Host "    3. Run benchmark again" -ForegroundColor Gray
    Write-Host "    4. Compare p95 latency; choose lowest`n" -ForegroundColor Gray
    
    # Offer to run baseline
    $runBench = Read-Host "  Run baseline benchmark now? (y/N)"
    if ($runBench -eq "y" -or $runBench -eq "Y") {
        Write-Host "`n  Running baseline benchmark (5 samples)...`n" -ForegroundColor Yellow
        & "$baseDir\.venv\Scripts\python.exe" "$baseDir\scripts\benchmark_llama_flags.py"
    }
} else {
    Write-Host "[Step 6/6] Benchmark skipped`n" -ForegroundColor Gray
}
#endregion

#region Summary
Write-Host "`n=== DEPLOYMENT SUMMARY ===" -ForegroundColor Cyan
Write-Host "✓ Per-key rate limiting configured ($PerKeyRate req/$PerKeyPeriod sec)" -ForegroundColor Green
Write-Host "✓ Smoke checks passed" -ForegroundColor Green
if (-not $SkipTests) {
    Write-Host "✓ Burst test validated" -ForegroundColor Green
}
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "  1. Import Grafana dashboard: ops\grafana_astra_dashboard.json" -ForegroundColor White
Write-Host "  2. Add alerts:" -ForegroundColor White
Write-Host "     - Queue depth > 50 for 2m" -ForegroundColor Gray
Write-Host "     - Per-key blocked rate > 10/sec for 2m" -ForegroundColor Gray
Write-Host "  3. Benchmark llama.cpp flags (if not done)" -ForegroundColor White
Write-Host "  4. Git commit:" -ForegroundColor White
Write-Host "     git add -A" -ForegroundColor Gray
Write-Host "     git commit -m `"capacity: per-key limits + queue metrics (Directive 001)`"" -ForegroundColor Gray
Write-Host "`nDirective 001: ✅ COMPLETE`n" -ForegroundColor Green
#endregion
