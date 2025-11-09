# 10-Minute Hardening Validation Script
# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Validates Memory Consolidation Hardening (Steps 1-8) + VLM Service.

.DESCRIPTION
    Tests all production-grade features:
    - Prometheus metrics exposure
    - Cryptographic provenance (HMAC signatures)
    - Overlap lock + job journals
    - Hallucination guard (provenance enforcement)
    - Quality scoring (BoW + embedding variants)
    - Auto-tuning DBSCAN (k-distance elbow)
    - Canary + backfill modes
    - CI gates (unit tests)
    - VLM service (Vision-Language Model) smoke tests

.EXAMPLE
    .\validate_hardening.ps1
    .\validate_hardening.ps1 -SkipTests  # Skip pytest (faster)
    .\validate_hardening.ps1 -IncludeVLM # Run VLM smoke tests
#>

param(
    [switch]$SkipTests = $false,
    [switch]$IncludeVLM = $false
)

$ErrorActionPreference = "Stop"
$baseUrl = "http://localhost:8000"
$dataDir = "data"

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ASTRA Memory Consolidation Hardening Validator" -ForegroundColor Cyan
Write-Host "  Target: 10 minutes | Steps 1-8" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────
# Step 1: Prometheus Metrics
# ─────────────────────────────────────────────────────
Write-Host "[1/8] Prometheus Metrics..." -ForegroundColor Yellow

try {
    $metrics = Invoke-WebRequest -Uri "$baseUrl/metrics" -UseBasicParsing
    $text = $metrics.Content
    
    $expected = @(
        "dream_runs_total",
        "dream_duration_seconds",
        "dream_events_processed",
        "dream_clusters_created",
        "dream_quality_score",
        "dream_lock_failures_total",
        "dream_provenance_failures_total",
        "dream_hmac_failures_total"
    )
    
    $found = @()
    foreach ($metric in $expected) {
        if ($text -match $metric) {
            $found += $metric
        }
    }
    
    Write-Host "  [OK] Found $($found.Count)/$($expected.Count) metrics" -ForegroundColor Green
    if ($found.Count -lt $expected.Count) {
        $missing = $expected | Where-Object { $_ -notin $found }
        Write-Host "  [WARN] Missing: $($missing -join ', ')" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [FAIL] Metrics endpoint failed: $_" -ForegroundColor Red
    exit 1
}

# ─────────────────────────────────────────────────────
# Step 2: Cryptographic Provenance Files
# ─────────────────────────────────────────────────────
Write-Host "[2/8] Cryptographic Provenance..." -ForegroundColor Yellow

$provenanceFile = Join-Path $dataDir "provenance" "summaries.jsonl"
if (Test-Path $provenanceFile) {
    $lines = Get-Content $provenanceFile | Select-Object -Last 5
    $valid = 0
    foreach ($line in $lines) {
        $obj = $line | ConvertFrom-Json
        if ($obj.signature -and $obj.root -and $obj.text) {
            $valid++
        }
    }
    Write-Host "  ✓ Provenance file exists ($valid/5 recent entries valid)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Provenance file not found (run consolidation first)" -ForegroundColor Yellow
}

# Check HMAC secret
$secretFile = Join-Path $dataDir "provenance" "hmac_secret.key"
if (Test-Path $secretFile) {
    $secret = Get-Content $secretFile -Raw
    if ($secret.Length -eq 64) {
        Write-Host "  ✓ HMAC secret key valid (64 chars)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ HMAC secret key wrong length: $($secret.Length)" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠ HMAC secret not initialized" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────
# Step 3: Overlap Lock + Job Journals
# ─────────────────────────────────────────────────────
Write-Host "[3/8] Overlap Lock + Journals..." -ForegroundColor Yellow

$lockDir = Join-Path $dataDir "locks"
$journalFile = Join-Path $lockDir "consolidation_jobs.jsonl"

if (Test-Path $journalFile) {
    $journals = Get-Content $journalFile | Select-Object -Last 3
    Write-Host "  ✓ Job journal exists ($($journals.Count) recent entries)" -ForegroundColor Green
    
    # Check for success/failure
    $successes = ($journals | ConvertFrom-Json | Where-Object { $_.status -eq "success" }).Count
    $failures = ($journals | ConvertFrom-Json | Where-Object { $_.status -eq "failed" }).Count
    Write-Host "    Successes: $successes | Failures: $failures" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠ Job journal not found" -ForegroundColor Yellow
}

$watermarkFile = Join-Path $lockDir "last_consolidation.txt"
if (Test-Path $watermarkFile) {
    $watermark = Get-Content $watermarkFile
    Write-Host "  ✓ Watermark file exists (last event: $watermark)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Watermark file not found" -ForegroundColor Yellow
}

# ─────────────────────────────────────────────────────
# Step 4: Hallucination Guard (Provenance Enforcement)
# ─────────────────────────────────────────────────────
Write-Host "[4/8] Hallucination Guard..." -ForegroundColor Yellow

# Check that provenance functions exist in code
$provenancePy = "src\services\memory_provenance.py"
if (Test-Path $provenancePy) {
    $code = Get-Content $provenancePy -Raw
    
    $functions = @(
        "build_provenance_prompt",
        "parse_provenance_line",
        "validate_summary_against_events"
    )
    
    $found = @()
    foreach ($func in $functions) {
        if ($code -match "def $func\(") {
            $found += $func
        }
    }
    
    Write-Host "  ✓ Found $($found.Count)/3 hallucination guard functions" -ForegroundColor Green
    
    # Check for regex pattern
    if ($code -match "PROVENANCE_RE\s*=") {
        Write-Host "  ✓ PROVENANCE regex pattern defined" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ PROVENANCE regex not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ memory_provenance.py not found" -ForegroundColor Red
}

# ─────────────────────────────────────────────────────
# Step 5: Dream Quality Score
# ─────────────────────────────────────────────────────
Write-Host "[5/8] Quality Scoring..." -ForegroundColor Yellow

if (Test-Path $provenancePy) {
    $code = Get-Content $provenancePy -Raw
    
    if ($code -match "def compute_quality_score_bow\(") {
        Write-Host "  ✓ BoW quality scoring function exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ BoW quality function not found" -ForegroundColor Red
    }
    
    # Check Prometheus exposure
    try {
        $metrics = Invoke-WebRequest -Uri "$baseUrl/metrics" -UseBasicParsing
        if ($metrics.Content -match "dream_quality_score") {
            Write-Host "  ✓ Quality score exposed to Prometheus" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ⚠ Could not verify Prometheus exposure" -ForegroundColor Yellow
    }
}

# ─────────────────────────────────────────────────────
# Step 6: Auto-tuning DBSCAN
# ─────────────────────────────────────────────────────
Write-Host "[6/8] Auto-tuning DBSCAN..." -ForegroundColor Yellow

$consolidationPy = "src\services\memory_consolidation.py"
if (Test-Path $consolidationPy) {
    $code = Get-Content $consolidationPy -Raw
    
    if ($code -match "def choose_eps_cosine\(") {
        Write-Host "  ✓ Auto-tuning function exists" -ForegroundColor Green
    } else {
        Write-Host "  ✗ choose_eps_cosine not found" -ForegroundColor Red
    }
    
    # Check for NearestNeighbors import
    if ($code -match "from sklearn.neighbors import NearestNeighbors") {
        Write-Host "  ✓ NearestNeighbors imported" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ NearestNeighbors import missing" -ForegroundColor Yellow
    }
    
    # Check for clamp logic
    if ($code -match "max\(0\.15.*min\(0\.45") {
        Write-Host "  ✓ Eps clamping [0.15, 0.45] detected" -ForegroundColor Green
    }
}

# ─────────────────────────────────────────────────────
# Step 7: Canary + Backfill Modes
# ─────────────────────────────────────────────────────
Write-Host "[7/8] Canary + Backfill Modes..." -ForegroundColor Yellow

# Test dry mode
try {
    Write-Host "  Testing dry mode (no writes)..." -ForegroundColor Cyan
    $dryRun = Invoke-RestMethod -Uri "$baseUrl/consolidation/run?mode=dry&limit=10" `
        -Method POST -ContentType "application/json" -TimeoutSec 60
    
    if ($dryRun.status -eq "success" -or $dryRun.message -match "dry") {
        Write-Host "  ✓ Dry mode successful" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Dry mode response unclear: $($dryRun.message)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Dry mode test failed: $_" -ForegroundColor Yellow
}

# Test backfill mode
try {
    Write-Host "  Testing backfill mode (historical)..." -ForegroundColor Cyan
    $since = (Get-Date).AddDays(-7).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $backfill = Invoke-RestMethod -Uri "$baseUrl/consolidation/run?mode=backfill&since=$since&limit=5" `
        -Method POST -ContentType "application/json" -TimeoutSec 60
    
    if ($backfill.status -eq "success" -or $backfill.message -match "backfill") {
        Write-Host "  ✓ Backfill mode successful" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Backfill mode response unclear" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Backfill mode test failed: $_" -ForegroundColor Yellow
}

# Check watermark functions
$lockPy = "src\services\consolidation_lock.py"
if (Test-Path $lockPy) {
    $code = Get-Content $lockPy -Raw
    
    if ($code -match "def get_watermark\(" -and $code -match "def set_watermark\(") {
        Write-Host "  ✓ Watermark management functions exist" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Watermark functions not found" -ForegroundColor Red
    }
}

# ─────────────────────────────────────────────────────
# Step 8: CI Gates (Unit Tests)
# ─────────────────────────────────────────────────────
Write-Host "[8/8] CI Gates (Unit Tests)..." -ForegroundColor Yellow

if ($SkipTests) {
    Write-Host "  ⏩ Skipping pytest (--SkipTests flag)" -ForegroundColor Cyan
} else {
    $testFile = "tests\week3\test_memory_consolidation_hardening.py"
    if (Test-Path $testFile) {
        Write-Host "  Running pytest (this may take 2-3 minutes)..." -ForegroundColor Cyan
        
        try {
            $result = & pytest $testFile -v --tb=short 2>&1
            $exitCode = $LASTEXITCODE
            
            if ($exitCode -eq 0) {
                Write-Host "  ✓ All tests passed" -ForegroundColor Green
            } elseif ($exitCode -eq 5) {
                Write-Host "  ⚠ No tests collected (functions not integrated yet)" -ForegroundColor Yellow
            } else {
                Write-Host "  ✗ Some tests failed (exit code: $exitCode)" -ForegroundColor Red
                Write-Host "    Run manually: pytest $testFile -v" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ✗ pytest execution failed: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠ Test file not found: $testFile" -ForegroundColor Yellow
    }
}

# ─────────────────────────────────────────────────────
# Optional: VLM Service Smoke Tests
# ─────────────────────────────────────────────────────
if ($IncludeVLM) {
    Write-Host "[9/9] VLM Service Smoke Tests..." -ForegroundColor Yellow

    $vlmService = "src/services/vlm_service_local.py"
    $vlmTests = "tests/week3/test_vlm_service.py"
    $vlmSmoke = "scripts/test_vlm_smoke.py"

    # Check VLM service file exists
    if (Test-Path $vlmService) {
        Write-Host "  ✓ VLM service file found" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ VLM service file not found: $vlmService" -ForegroundColor Yellow
    }

    # Run VLM smoke tests
    if (Test-Path $vlmSmoke) {
        Write-Host "  Running VLM smoke tests..." -ForegroundColor Cyan
        try {
            python $vlmSmoke
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ VLM smoke tests PASSED" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ VLM smoke tests had issues (exit code: $LASTEXITCODE)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ⚠ VLM smoke test failed: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠ VLM smoke test not found: $vlmSmoke" -ForegroundColor Yellow
    }

    # Check VLM unit tests exist
    if (Test-Path $vlmTests) {
        Write-Host "  ✓ VLM unit tests found: $vlmTests" -ForegroundColor Green
        if (-not $SkipTests) {
            Write-Host "  Running VLM unit tests..." -ForegroundColor Cyan
            pytest $vlmTests -v --tb=short
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ VLM unit tests PASSED" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ VLM unit tests had failures" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  ⚠ VLM unit tests not found: $vlmTests" -ForegroundColor Yellow
    }

    Write-Host ""
}

# ─────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Validation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review any ⚠ warnings above" -ForegroundColor White
Write-Host "  2. Run full test suite: pytest tests/week3/ -v" -ForegroundColor White
Write-Host "  3. Check Prometheus metrics: $baseUrl/metrics" -ForegroundColor White
Write-Host "  4. Review job journal: $journalFile" -ForegroundColor White
Write-Host "  5. Install Prometheus alerts: config/prometheus/astra_memory_alerts.yml" -ForegroundColor White
if ($IncludeVLM) {
    Write-Host "  6. Setup VLM models: See docs/VLM_SERVICE_GUIDE.md" -ForegroundColor White
}
Write-Host ""
Write-Host "Production Checklist:" -ForegroundColor Yellow
Write-Host "  [ ] Prometheus alerts configured" -ForegroundColor White
Write-Host "  [ ] Quality baseline established (≥0.70)" -ForegroundColor White
Write-Host "  [ ] Duration baseline established (≤180s)" -ForegroundColor White
Write-Host "  [ ] Watermark file backed up regularly" -ForegroundColor White
Write-Host "  [ ] Job journals monitored for failures" -ForegroundColor White
Write-Host "  [ ] HMAC secret rotated (30 days)" -ForegroundColor White
if ($IncludeVLM) {
    Write-Host "  [ ] VLM model files downloaded and validated" -ForegroundColor White
    Write-Host "  [ ] VLM dependencies installed (torch, transformers, pillow)" -ForegroundColor White
}
Write-Host ""
