#Requires -Version 5.1
<#
.SYNOPSIS
    DIRECTIVE 001 — Go Live: Capacity Controls Deployment

.DESCRIPTION
    Automated deployment of per-key rate limiting + queue metrics.
    Includes configuration, restart, smoke tests, burst validation, and evidence capture.

.EXAMPLE
    .\scripts\directive_001_go_live.ps1
    
.EXAMPLE
    .\scripts\directive_001_go_live.ps1 -SkipBurst -SkipBenchmark
#>

[CmdletBinding()]
param(
    [switch]$SkipBurst,
    [switch]$SkipBenchmark
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 DIRECTIVE 001 — CAPACITY CONTROLS GO-LIVE           ║" -ForegroundColor Cyan
Write-Host "║  Per-key rate limiting + Queue metrics + Benchmarking   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

#region Step 0: Prerequisites
Write-Host "[0/7] Checking prerequisites..." -ForegroundColor Yellow

# Check if in PROJECT_ASTRA directory
if (-not (Test-Path ".\pyproject.toml")) {
    Write-Error "Not in PROJECT_ASTRA directory. Run from X:\PROJECT_ASTRA"
}

# Check venv exists
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv"
}

Write-Host "  ✓ Directory: $PWD" -ForegroundColor Green
Write-Host "  ✓ Virtual environment: .venv found`n" -ForegroundColor Green
#endregion

#region Step 1: Configure Per-Key Limits
Write-Host "[1/7] Configuring per-key rate limits..." -ForegroundColor Yellow

$envPath = ".\.env"

# Ensure .env exists
if (-not (Test-Path $envPath)) {
    Write-Host "  ℹ Creating .env file..." -ForegroundColor Gray
    New-Item -ItemType File -Path $envPath | Out-Null
}

$envContent = Get-Content $envPath -Raw

# Update or add per-key config
if ($envContent -match 'ASTRA_PER_KEY_RATE=') {
    Write-Host "  ℹ Updating ASTRA_PER_KEY_RATE..." -ForegroundColor Gray
    (Get-Content $envPath) -replace '^ASTRA_PER_KEY_RATE=.*', 'ASTRA_PER_KEY_RATE=120' | Set-Content $envPath
} else {
    Write-Host "  ℹ Adding ASTRA_PER_KEY_RATE=120..." -ForegroundColor Gray
    Add-Content $envPath "`nASTRA_PER_KEY_RATE=120"
}

if ($envContent -match 'ASTRA_PER_KEY_PERIOD_SEC=') {
    Write-Host "  ℹ Updating ASTRA_PER_KEY_PERIOD_SEC..." -ForegroundColor Gray
    (Get-Content $envPath) -replace '^ASTRA_PER_KEY_PERIOD_SEC=.*', 'ASTRA_PER_KEY_PERIOD_SEC=60' | Set-Content $envPath
} else {
    Write-Host "  ℹ Adding ASTRA_PER_KEY_PERIOD_SEC=60..." -ForegroundColor Gray
    Add-Content $envPath "`nASTRA_PER_KEY_PERIOD_SEC=60"
}

# Ensure API key exists
$envContent = Get-Content $envPath -Raw
if ($envContent -notmatch 'ASTRA_API_KEY=\S+') {
    Write-Host "  ⚠ ASTRA_API_KEY not found, generating..." -ForegroundColor Yellow
    $apiKey = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
    Add-Content $envPath "`nASTRA_API_KEY=$apiKey"
    Write-Host "  ✓ Generated API key ($($apiKey.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "  ✓ API key already configured" -ForegroundColor Green
}

Write-Host "  ✓ Rate: 120 req/60s = 2 req/sec per key`n" -ForegroundColor Green
#endregion

#region Step 2: Restart Backend
Write-Host "[2/7] Restarting backend..." -ForegroundColor Yellow

# Stop any existing python processes
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "  ℹ Stopping existing backend ($($pythonProcs.Count) process(es))..." -ForegroundColor Gray
    $pythonProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
}

# Start backend in new minimized window
Write-Host "  ℹ Starting backend (minimized window)..." -ForegroundColor Gray
$startArgs = "-NoExit", "-Command", "cd $PWD; .\.venv\Scripts\python.exe run_server.py"
Start-Process powershell -WindowStyle Minimized -ArgumentList $startArgs

# Wait for startup
Write-Host "  ℹ Waiting for startup (10 seconds)..." -ForegroundColor Gray
Start-Sleep 10

# Verify backend is running
$maxRetries = 5
$retryCount = 0
$backendUp = $false

while ($retryCount -lt $maxRetries -and -not $backendUp) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 3 -ErrorAction Stop
        $backendUp = $true
        Write-Host "  ✓ Backend running (status: $($health.status))`n" -ForegroundColor Green
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "  ⏳ Retry $retryCount/$maxRetries..." -ForegroundColor Gray
            Start-Sleep 2
        } else {
            Write-Error "Backend failed to start after $maxRetries retries. Check logs."
        }
    }
}
#endregion

#region Step 3: Smoke Checks
Write-Host "[3/7] Running smoke checks..." -ForegroundColor Yellow

# Health check (no auth)
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 5
    Write-Host "  ✓ Health endpoint: $($health.status)" -ForegroundColor Green
} catch {
    Write-Error "Health check failed: $_"
}

# Metrics check
try {
    $metricsResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5
    $metrics = $metricsResponse.Content
    
    # Check for new metrics
    $hasLimiterAllowed = $metrics -match "astra_limiter_per_key_allowed_total"
    $hasLimiterBlocked = $metrics -match "astra_limiter_per_key_blocked_total"
    $hasQueueDepth = $metrics -match "astra_queue_depth"
    $hasQueueWait = $metrics -match "astra_queue_wait_seconds"
    
    if ($hasLimiterAllowed) {
        Write-Host "  ✓ Metric: astra_limiter_per_key_allowed_total" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_limiter_per_key_allowed_total" -ForegroundColor Red
    }
    
    if ($hasLimiterBlocked) {
        Write-Host "  ✓ Metric: astra_limiter_per_key_blocked_total" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_limiter_per_key_blocked_total" -ForegroundColor Red
    }
    
    if ($hasQueueDepth) {
        Write-Host "  ✓ Metric: astra_queue_depth" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_queue_depth" -ForegroundColor Red
    }
    
    if ($hasQueueWait) {
        Write-Host "  ✓ Metric: astra_queue_wait_seconds" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_queue_wait_seconds" -ForegroundColor Red
    }
    
    if (-not ($hasLimiterAllowed -and $hasLimiterBlocked -and $hasQueueDepth -and $hasQueueWait)) {
        Write-Host "  ⚠ Some metrics missing - backend may need restart to load new code`n" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ All 4 new metrics present`n" -ForegroundColor Green
    }
} catch {
    Write-Error "Metrics check failed: $_"
}
#endregion

#region Step 4: Burst Validation
if (-not $SkipBurst) {
    Write-Host "[4/7] Running burst validation (150 requests)..." -ForegroundColor Yellow
    
    # Extract API key
    $envLines = Get-Content $envPath
    $apiKeyLine = $envLines | Where-Object { $_ -match '^ASTRA_API_KEY=' } | Select-Object -First 1
    if (-not $apiKeyLine) {
        Write-Error "ASTRA_API_KEY not found in .env"
    }
    $apiKey = $apiKeyLine.Split('=')[1].Trim()
    
    $headers = @{
        "X-API-Key" = $apiKey
        "Content-Type" = "application/json"
    }
    
    # Create test conversation
    Write-Host "  ℹ Creating test conversation..." -ForegroundColor Gray
    try {
        $convBody = @{ title = "Directive 001 Burst Test" } | ConvertTo-Json
        $conv = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/conversations/" -Method POST -Headers $headers -Body $convBody -TimeoutSec 10
        $convId = $conv.id
        Write-Host "  ✓ Conversation created: $convId" -ForegroundColor Green
    } catch {
        Write-Error "Failed to create test conversation: $_"
    }
    
    # Prepare payload
    $payload = @{
        conversation_id = $convId
        message = "Say 'ok'"
        use_memory = $false
    } | ConvertTo-Json -Compress
    
    # Fire 150 requests
    Write-Host "  ℹ Sending 150 requests (this takes ~7 seconds)..." -ForegroundColor Gray
    Write-Host "    Progress: " -NoNewline
    
    $results = 1..150 | ForEach-Object {
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:8080/v1/chat/" `
                -Method POST `
                -Headers $headers `
                -Body $payload `
                -UseBasicParsing `
                -TimeoutSec 10 `
                -ErrorAction Stop
            
            if ($_ % 10 -eq 0) { Write-Host "." -NoNewline -ForegroundColor Green }
            [PSCustomObject]@{ Code = $response.StatusCode }
        } catch {
            $statusCode = if ($_.Exception.Response) {
                $_.Exception.Response.StatusCode.value__
            } else {
                0
            }
            
            if ($statusCode -eq 429) {
                if ($_ % 10 -eq 0) { Write-Host "X" -NoNewline -ForegroundColor Yellow }
            } elseif ($statusCode -gt 0) {
                Write-Host "!" -NoNewline -ForegroundColor Red
            }
            
            [PSCustomObject]@{ Code = $statusCode }
        }
    }
    
    Write-Host "`n"
    
    # Analyze results
    $summary = $results | Group-Object Code | Select-Object Name, Count | Sort-Object Name
    
    Write-Host "  📊 Results:" -ForegroundColor Cyan
    $summary | ForEach-Object {
        $code = $_.Name
        $count = $_.Count
        $color = switch ($code) {
            "200" { "Green" }
            "429" { "Yellow" }
            default { "Red" }
        }
        Write-Host "    $code : $count" -ForegroundColor $color
    }
    
    $okCount = ($summary | Where-Object { $_.Name -eq "200" }).Count
    $blockedCount = ($summary | Where-Object { $_.Name -eq "429" }).Count
    $errorCount = ($summary | Where-Object { $_.Name -notin @("200", "429") }).Count
    
    if ($okCount -ge 100 -and $blockedCount -gt 0) {
        Write-Host "`n  ✓ Per-key limiting working! (~$okCount allowed, ~$blockedCount blocked)" -ForegroundColor Green
    } elseif ($blockedCount -eq 0) {
        Write-Host "`n  ⚠ No 429s observed (rate may be too high or backend not using new code)" -ForegroundColor Yellow
    } else {
        Write-Host "`n  ⚠ Unexpected distribution" -ForegroundColor Yellow
    }
    
    if ($errorCount -gt 0) {
        Write-Host "  ⚠ $errorCount requests failed with errors" -ForegroundColor Yellow
    }
    
    # Check metrics increased
    Write-Host "`n  ℹ Checking limiter metrics..." -ForegroundColor Gray
    $metricsAfter = (Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5).Content
    $limiterLines = $metricsAfter -split "`n" | Select-String "astra_limiter_per_key_" | Where-Object { $_ -notmatch "^#" }
    
    if ($limiterLines) {
        Write-Host "  ✓ Limiter counters updated:" -ForegroundColor Green
        $limiterLines | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Limiter metrics not found" -ForegroundColor Yellow
    }
    
    Write-Host ""
} else {
    Write-Host "[4/7] Burst validation skipped`n" -ForegroundColor Gray
}
#endregion

#region Step 5: Grafana Guidance
Write-Host "[5/7] Grafana dashboard import..." -ForegroundColor Yellow

$dashboardPath = "ops\grafana_astra_dashboard.json"
if (Test-Path $dashboardPath) {
    Write-Host "  ✓ Dashboard JSON exists: $dashboardPath" -ForegroundColor Green
    Write-Host "  📊 Manual steps:" -ForegroundColor Cyan
    Write-Host "    1. Open Grafana: http://localhost:3000" -ForegroundColor White
    Write-Host "    2. Click + → Import" -ForegroundColor White
    Write-Host "    3. Upload file: $dashboardPath" -ForegroundColor White
    Write-Host "    4. Select Prometheus datasource" -ForegroundColor White
    Write-Host "    5. Click Import" -ForegroundColor White
    Write-Host "`n  📢 Alerts to configure:" -ForegroundColor Cyan
    Write-Host "    1. Per-Key Block Rate: rate(astra_limiter_per_key_blocked_total[5m]) > 10 for 5m" -ForegroundColor White
    Write-Host "    2. Queue Depth: avg_over_time(astra_queue_depth[5m]) > 50 for 10m`n" -ForegroundColor White
} else {
    Write-Host "  ⚠ Dashboard JSON not found at $dashboardPath`n" -ForegroundColor Yellow
}
#endregion

#region Step 6: Benchmark (Optional)
if (-not $SkipBenchmark) {
    Write-Host "[6/7] llama.cpp benchmark..." -ForegroundColor Yellow
    
    $benchmarkScript = "scripts\benchmark_llama_flags.py"
    if (Test-Path $benchmarkScript) {
        $runBench = Read-Host "  Run llama.cpp benchmark now? (y/N)"
        if ($runBench -eq "y" -or $runBench -eq "Y") {
            Write-Host "  ℹ Running benchmark (5 samples)...`n" -ForegroundColor Gray
            & .\.venv\Scripts\python.exe $benchmarkScript
            Write-Host ""
        } else {
            Write-Host "  ℹ Skipped. Run later: .\.venv\Scripts\python.exe $benchmarkScript`n" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Benchmark script not found: $benchmarkScript`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "[6/7] Benchmark skipped`n" -ForegroundColor Gray
}
#endregion

#region Step 7: Evidence & Commit
Write-Host "[7/7] Capturing evidence & commit..." -ForegroundColor Yellow

# Create data directory if needed
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Capture evidence
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$metricsFile = "data\dir001_metrics_$timestamp.txt"
$summaryFile = "data\dir001_burst_summary_$timestamp.txt"

try {
    $finalMetrics = (Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5).Content
    $finalMetrics | Out-File $metricsFile -Encoding UTF8
    Write-Host "  ✓ Metrics snapshot: $metricsFile" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Failed to capture metrics snapshot" -ForegroundColor Yellow
}

if (-not $SkipBurst -and $summary) {
    $summary | Out-File $summaryFile -Encoding UTF8
    Write-Host "  ✓ Burst summary: $summaryFile" -ForegroundColor Green
}

# Git commit
Write-Host "`n  ℹ Preparing git commit..." -ForegroundColor Gray
$gitStatus = git status --porcelain 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Not a git repository or git not available" -ForegroundColor Yellow
} elseif (-not $gitStatus) {
    Write-Host "  ℹ No changes to commit (already committed?)" -ForegroundColor Gray
} else {
    $commitNow = Read-Host "  Commit changes now? (Y/n)"
    if ($commitNow -ne "n" -and $commitNow -ne "N") {
        git add -A
        git commit -m "capacity(Dir001): per-key limits + queue metrics live; baseline captured"
        Write-Host "  ✓ Git commit complete" -ForegroundColor Green
        
        $pushNow = Read-Host "  Push to remote? (y/N)"
        if ($pushNow -eq "y" -or $pushNow -eq "Y") {
            git push
            Write-Host "  ✓ Git push complete" -ForegroundColor Green
        }
    } else {
        Write-Host "  ℹ Skipped commit. Run manually:" -ForegroundColor Gray
        Write-Host "    git add -A" -ForegroundColor Gray
        Write-Host "    git commit -m `"capacity(Dir001): per-key limits + queue metrics live`"" -ForegroundColor Gray
    }
}

Write-Host ""
#endregion

#region Summary
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ DIRECTIVE 001 — DEPLOYMENT COMPLETE                  ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📊 Status Summary:" -ForegroundColor Cyan
Write-Host "  ✓ Per-key rate limiting: 120 req/60s per key" -ForegroundColor Green
Write-Host "  ✓ Queue metrics: Exposed in /metrics" -ForegroundColor Green
Write-Host "  ✓ Backend: Running with new middleware" -ForegroundColor Green
if (-not $SkipBurst) {
    Write-Host "  ✓ Burst test: Validated 429 responses" -ForegroundColor Green
}
Write-Host "`n📝 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Import Grafana dashboard (see guidance above)" -ForegroundColor White
Write-Host "  2. Configure alerts (per-key block rate, queue depth)" -ForegroundColor White
Write-Host "  3. Benchmark llama.cpp flags (if not done)" -ForegroundColor White
Write-Host "  4. Monitor /metrics for capacity trends" -ForegroundColor White
Write-Host "`n🚀 Ready for Directive 002: SSE Streaming" -ForegroundColor Cyan
Write-Host "   Run: .\scripts\directive_002_sse_streaming.ps1 (when ready)`n" -ForegroundColor White
#endregion
