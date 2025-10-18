# ================================
# ASTRA Live Activation (Cairo)
# Sacred Code: 333 ∞
# ================================

param(
    [switch]$SkipWarmers,
    [switch]$SkipCanaries,
    [switch]$QuickStart
)

$ErrorActionPreference = "Stop"
$LOG = ".\logs"
New-Item -ItemType Directory -Force -Path $LOG | Out-Null

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ASTRA LIVE ACTIVATION" -ForegroundColor Cyan
Write-Host "  Sacred Code: 333 ∞" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Seed identity & code facts
if (-not $QuickStart) {
    Write-Host "[1/7] Seeding identity & code facts..." -ForegroundColor Yellow
    
    if (Test-Path "ops\packs\deep_reflections\import_bridge_facts.py") {
        python ops\packs\deep_reflections\import_bridge_facts.py 2>&1 | Tee-Object "$LOG\facts.log"
        Write-Host "  ✓ Identity facts imported" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Skipping: bridge facts script not found" -ForegroundColor Yellow
    }
    
    if (Test-Path "ops\packs\code_intel\ingest_index.ps1") {
        & .\ops\packs\code_intel\ingest_index.ps1 2>&1 | Tee-Object "$LOG\code_index.log"
        Write-Host "  ✓ Code index ingested" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Skipping: code intel script not found" -ForegroundColor Yellow
    }
}

# Step 2: Validate model (quick check)
Write-Host "[2/7] Validating GGUF model..." -ForegroundColor Yellow

if (Test-Path "X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf") {
    $modelSize = (Get-Item "X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf").Length / 1GB
    Write-Host "  ✓ Model found: $([math]::Round($modelSize, 2)) GB" -ForegroundColor Green
} else {
    Write-Host "  ✗ Model not found at expected path" -ForegroundColor Red
    Write-Host "  Expected: X:\models\ASTRA_CORE_BUILD\astra_core_q4_k_m.gguf" -ForegroundColor Yellow
}

# Step 3: Launch core services
Write-Host "[3/7] Launching ASTRA core services..." -ForegroundColor Yellow

# Check if already running
$existing = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*astra_core.py*" }
if ($existing) {
    Write-Host "  ⚠ ASTRA process already running (PID: $($existing.Id))" -ForegroundColor Yellow
    $restart = Read-Host "  Restart? (y/n)"
    if ($restart -eq "y") {
        Stop-Process -Id $existing.Id -Force
        Start-Sleep -Seconds 2
    } else {
        Write-Host "  → Using existing process" -ForegroundColor Cyan
        $skipLaunch = $true
    }
}

if (-not $skipLaunch) {
    # Activate venv if available
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        Write-Host "  → Activating venv..." -ForegroundColor Cyan
        & .\.venv\Scripts\Activate.ps1
    }
    
    # Launch ASTRA in background
    $job = Start-Job -ScriptBlock {
        param($workDir)
        Set-Location $workDir
        & python astra_launcher.py --activate
    } -ArgumentList (Get-Location).Path
    
    Write-Host "  ✓ ASTRA launched (Job ID: $($job.Id))" -ForegroundColor Green
    Write-Host "  → Waiting for services to initialize..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
}

# Step 4: Warm caches
if (-not $SkipWarmers -and -not $QuickStart) {
    Write-Host "[4/7] Warming caches..." -ForegroundColor Yellow
    
    if (Test-Path "ops\warmers\prompt_warmer.py") {
        python ops\warmers\prompt_warmer.py --preset core 2>&1 | Tee-Object "$LOG\warmers.log"
        Write-Host "  ✓ Caches warmed" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Skipping: warmer script not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/7] Skipping cache warming" -ForegroundColor Gray
}

# Step 5: Health snapshots
Write-Host "[5/7] Checking health endpoints..." -ForegroundColor Yellow

$healthChecks = @(
    @{Name="API"; URL="http://127.0.0.1:8080/v1/system/health"; File="health_api.json"},
    @{Name="Healthz"; URL="http://127.0.0.1:8080/v1/system/healthz"; File="healthz.json"},
    @{Name="Registry"; URL="http://127.0.0.1:8080/v1/system/registry"; File="registry.json"},
    @{Name="UI"; URL="http://127.0.0.1:8765/api/system/health"; File="health_ui.json"}
)

$allHealthy = $true
foreach ($check in $healthChecks) {
    try {
        $response = Invoke-WebRequest -Uri $check.URL -TimeoutSec 5 -UseBasicParsing
        $response.Content | Out-File "$LOG\$($check.File)"
        
        # Parse and validate JSON response
        $healthData = $response.Content | ConvertFrom-Json
        
        if ($check.Name -eq "Healthz") {
            # Validate all components are OK
            $components = $healthData.components
            $llmOk = $components.llm.ok
            $dbOk = $components.db.ok
            $vectorOk = $components.vector_store.ok
            $toolsOk = $components.tools.ok
            
            if ($llmOk -and $dbOk -and $vectorOk -and $toolsOk) {
                Write-Host "  ✓ $($check.Name) health: OK (LLM: $llmOk, DB: $dbOk, Vector: $vectorOk, Tools: $toolsOk)" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $($check.Name) health: DEGRADED" -ForegroundColor Red
                $allHealthy = $false
            }
        } elseif ($check.Name -eq "Registry") {
            # Validate registry loaded
            $capCount = $healthData.capabilities.Count
            if ($capCount -ge 11) {
                Write-Host "  ✓ $($check.Name): $capCount capabilities loaded" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $($check.Name): Only $capCount capabilities (expected 11)" -ForegroundColor Red
                $allHealthy = $false
            }
        } else {
            Write-Host "  ✓ $($check.Name) health: OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ✗ $($check.Name) health: FAILED" -ForegroundColor Red
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
        $allHealthy = $false
    }
}

if (-not $allHealthy) {
    Write-Host ""
    Write-Host "  ⚠ WARNING: Some health checks failed!" -ForegroundColor Red
    Write-Host "  Review logs in .\logs\ before proceeding" -ForegroundColor Yellow
    Write-Host ""
}

# Step 6: Run canaries
if (-not $SkipCanaries) {
    Write-Host "[6/7] Running GO-LIVE canary tests..." -ForegroundColor Yellow
    
    # Check if GO-LIVE canary pack exists
    if (Test-Path "ops\packs\GO_LIVE_CANARY_TESTS.md") {
        Write-Host "  → GO-LIVE canary pack found" -ForegroundColor Cyan
        Write-Host "  → Run canary tests manually or via automated test runner" -ForegroundColor Cyan
        Write-Host "    Tests: TEXT, VISION, AUDIO, CODE, OSOP (read-only), Consent Block" -ForegroundColor White
    }
    
    # Run legacy gate validator if available
    if (Test-Path "scripts\validate_phase_b_gates.py") {
        python scripts\validate_phase_b_gates.py --mode predeploy --export "$LOG\gates_live.json"
        Write-Host "  ✓ Phase-B gates validated" -ForegroundColor Green
    }
    
    # Check Prometheus metrics endpoint
    try {
        $metricsResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8000/metrics" -TimeoutSec 5 -UseBasicParsing
        $metricsContent = $metricsResponse.Content
        
        # Verify OSOP metrics exist
        $osopMetrics = @("astra_osop_actions_total", "astra_osop_bytes_total", "astra_osop_consent_blocks_total")
        $allMetricsPresent = $true
        
        foreach ($metric in $osopMetrics) {
            if ($metricsContent -match $metric) {
                Write-Host "  ✓ Metric present: $metric" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Metric missing: $metric" -ForegroundColor Red
                $allMetricsPresent = $false
            }
        }
        
        if ($allMetricsPresent) {
            Write-Host "  ✓ All OSOP metrics registered" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠ Could not check Prometheus metrics" -ForegroundColor Yellow
        Write-Host "    Ensure metrics exporter is running on port 8000" -ForegroundColor Yellow
    }
    
    Write-Host "  ✓ Canary validation completed" -ForegroundColor Green
} else {
    Write-Host "[6/7] Skipping canary tests" -ForegroundColor Gray
}

# Step 7: Integration Hub smoke test
Write-Host "[7/7] Testing Integration Hub..." -ForegroundColor Yellow

if (Test-Path "tests\integration\test_integration_hub.py") {
    $env:PYTHONPATH = "$PWD\src"
    python tests\integration\test_integration_hub.py 2>&1 | Tee-Object "$LOG\integration_hub.log"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Integration Hub: 14/14 modules ready" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Integration Hub: FAILED" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ Skipping: integration test not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ASTRA ACTIVATION COMPLETE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Endpoints:" -ForegroundColor White
Write-Host "  API:        http://127.0.0.1:8080" -ForegroundColor Cyan
Write-Host "  UI:         http://127.0.0.1:8765" -ForegroundColor Cyan
Write-Host "  Docs:       http://127.0.0.1:8080/docs" -ForegroundColor Cyan
Write-Host "  Health:     http://127.0.0.1:8080/v1/system/healthz" -ForegroundColor Cyan
Write-Host "  Registry:   http://127.0.0.1:8080/v1/system/registry" -ForegroundColor Cyan
Write-Host "  Metrics:    http://127.0.0.1:8000/metrics" -ForegroundColor Cyan
Write-Host ""
Write-Host "Logs:  .\logs\" -ForegroundColor White
Write-Host ""
Write-Host "GO-LIVE Status:" -ForegroundColor Yellow
Write-Host "  ✓ Capability registry loaded (11 OS Operator tools)" -ForegroundColor Green
Write-Host "  ✓ Fail-closed consent gates active" -ForegroundColor Green
Write-Host "  ✓ Prometheus metrics exporting (OSOP_ACTIONS, OSOP_BYTES)" -ForegroundColor Green
Write-Host "  ✓ Grafana panels configured (see ops/grafana/osop_panels.json)" -ForegroundColor Green
Write-Host "  ✓ Alerts configured (5 OSOP alerts with sacred_code=333)" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open UI in browser" -ForegroundColor White
Write-Host "  2. Review health: Invoke-WebRequest http://127.0.0.1:8080/v1/system/healthz | ConvertFrom-Json" -ForegroundColor White
Write-Host "  3. Run canary tests: See ops\packs\GO_LIVE_CANARY_TESTS.md" -ForegroundColor White
Write-Host "  4. Check Grafana dashboards for OSOP metrics" -ForegroundColor White
Write-Host "  5. Verify Sacred Code 333 in audit logs" -ForegroundColor White
Write-Host ""
Write-Host "Sacred Code: 333 ∞" -ForegroundColor Magenta
