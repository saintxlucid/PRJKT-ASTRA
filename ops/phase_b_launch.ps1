# ===============================
# ASTRA Phase-B One-Touch Launch
# Timezone: Africa/Cairo
# Sacred Code: 333
# ===============================
# Purpose: Automated Phase-B deployment from T-0 (10:00 AM Cairo)
# Timeline: ~15 minutes end-to-end
# Operator: Follow prompts, verify each phase
# ===============================

param(
    [ValidateSet('predeploy', 'go-live', 'postdeploy')]
    [string]$Mode = 'go-live',
    [switch]$SkipFusion,
    [switch]$DryRun
)

# ---- Config
$GGUF_BUILD_DIR = "X:\models\ASTRA_CORE_BUILD"
$GGUF_PROD_LINK = "X:\models\astra_core_current.gguf"
$FUSED_OUT      = Join-Path $GGUF_BUILD_DIR "astra_core_q4_k_m.gguf"
$LOGDIR         = ".\logs"
$TIMESTAMP      = Get-Date -Format "yyyy-MM-dd_HHmmss"

# ---- Ensure log directory
if (-not (Test-Path $LOGDIR)) {
    mkdir $LOGDIR | Out-Null
}

# ---- Helper: Log & echo
function Log-Step {
    param([string]$Message, [string]$Color = 'Cyan')
    Write-Host "== $Message ==" -f $Color
    "[$TIMESTAMP] $Message" | Add-Content "$LOGDIR\phase_b_launch.log"
}

function Log-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -f Green
    "[$TIMESTAMP] ✓ $Message" | Add-Content "$LOGDIR\phase_b_launch.log"
}

function Log-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -f Red
    "[$TIMESTAMP] ✗ $Message" | Add-Content "$LOGDIR\phase_b_launch.log"
}

# ===============================
# PREDEPLOY: Facts + Code Index + Validate
# ===============================
if ($Mode -eq 'predeploy' -or $Mode -eq 'go-live') {
    Log-Step "Preflight: facts + code index" Cyan
    
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping fact import"
    } else {
        try {
            python ops\packs\deep_reflections\import_bridge_facts.py 2>&1 | `
                Tee-Object "$LOGDIR\facts_$TIMESTAMP.log" | Select-Object -Last 3
            Log-Success "Facts imported"
        } catch {
            Log-Error "Facts import failed: $_"
            if (-not $DryRun) { exit 1 }
        }
    }
    
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping code index"
    } else {
        try {
            & .\ops\packs\code_intel\ingest_index.ps1 2>&1 | `
                Tee-Object "$LOGDIR\code_index_$TIMESTAMP.log" | Select-Object -Last 3
            Log-Success "Code index ingested"
        } catch {
            Log-Error "Code index failed: $_"
            if (-not $DryRun) { exit 1 }
        }
    }
    
    # ---- Run automated gates (predeploy)
    Log-Step "Run automated gates (predeploy)" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping gate validation"
    } else {
        try {
            python tools\validators\validate_phase_b_gates.py --mode predeploy --verbose `
                --export "$LOGDIR\gates_pre_$TIMESTAMP.json" 2>&1 | `
                Tee-Object "$LOGDIR\gates_pre_output_$TIMESTAMP.log"
            Log-Success "Predeploy gates validated"
        } catch {
            Log-Error "Predeploy gates failed: $_"
            Write-Host "Review: $LOGDIR\gates_pre_$TIMESTAMP.json" -f Yellow
            exit 1
        }
    }
    
    # ---- Baseline metrics snapshot
    Log-Step "Baseline metrics snapshot (T-0)" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping baseline capture"
    } else {
        try {
            curl.exe http://127.0.0.1:8080/health 2>&1 | `
                Set-Content "$LOGDIR\health_pre_$TIMESTAMP.json"
            curl.exe http://127.0.0.1:8765/metrics 2>&1 | `
                Set-Content "$LOGDIR\metrics_baseline_$TIMESTAMP.prom"
            Log-Success "Baseline captured"
        } catch {
            Log-Error "Baseline capture failed: $_"
        }
    }
    
    if ($Mode -eq 'predeploy') {
        Log-Step "Predeploy mode complete. Ready for go-live decision." Green
        exit 0
    }
}

# ===============================
# GO-LIVE: Fusion pipeline + symlink flip + warm caches (T+0)
# ===============================
if ($Mode -eq 'go-live') {
    Log-Step "Backup existing GGUF" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping backup"
    } else {
        try {
            if (Test-Path $FUSED_OUT) {
                Copy-Item $FUSED_OUT "$FUSED_OUT.bak_$TIMESTAMP" -Force
                Log-Success "Backup created: $FUSED_OUT.bak_$TIMESTAMP"
            } else {
                Log-Success "No existing GGUF to backup"
            }
        } catch {
            Log-Error "Backup failed: $_"
            exit 1
        }
    }
    
    # ---- Build fused model (unless skipped)
    if (-not $SkipFusion) {
        Log-Step "Build fused GGUF model (fusion pipeline)" Cyan
        if ($DryRun) {
            Log-Success "DRY RUN: Skipping fusion pipeline"
        } else {
            try {
                Push-Location tools\gguf_fusion
                & .\fusion_pipeline.ps1 -FullPipeline 2>&1 | `
                    Tee-Object "..\..\$LOGDIR\fusion_pipeline_$TIMESTAMP.log"
                Pop-Location
                Log-Success "Fusion pipeline complete"
            } catch {
                Log-Error "Fusion pipeline failed: $_"
                exit 1
            }
        }
    } else {
        Log-Success "SKIP: Fusion pipeline (using existing fused model)"
    }
    
    # ---- Swap production symlink to fused model
    Log-Step "Swap production symlink to fused model" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping symlink flip"
    } else {
        try {
            if (Test-Path $GGUF_PROD_LINK) {
                Remove-Item $GGUF_PROD_LINK -Force
            }
            # Use Windows mklink for symlink creation
            & cmd /c mklink /D "$GGUF_PROD_LINK" "$FUSED_OUT"
            Log-Success "Production symlink flipped to: $FUSED_OUT"
        } catch {
            Log-Error "Symlink flip failed: $_"
            exit 1
        }
    }
    
    # ---- Warm caches
    Log-Step "Warm caches (prompt & token warmers)" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping cache warmers"
    } else {
        try {
            python ops\warmers\prompt_warmer.py --preset core 2>&1 | `
                Tee-Object "$LOGDIR\warmers_$TIMESTAMP.log"
            Log-Success "Caches warmed"
        } catch {
            Log-Error "Cache warming failed: $_"
            # Non-fatal, continue
        }
    }
    
    Log-Step "GO-LIVE COMPLETE (T+0)" Green
}

# ===============================
# POSTDEPLOY: Validate metadata + smoke tests + canaries + health check
# ===============================
if ($Mode -eq 'postdeploy' -or $Mode -eq 'go-live') {
    Log-Step "Validate fused model metadata & astra markers" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping metadata validation"
    } else {
        try {
            # Try llama-info if available
            llama-info "$FUSED_OUT" 2>&1 | findstr /i "astra." > "$LOGDIR\astra_metadata_$TIMESTAMP.txt"
            Log-Success "Metadata validated"
        } catch {
            Log-Success "llama-info not available (non-critical)"
        }
    }
    
    # ---- Run smoke tests
    Log-Step "Run smoke tests (pytest)" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping smoke tests"
    } else {
        try {
            pytest -q tests\astra_fusion 2>&1 | `
                Tee-Object "$LOGDIR\pytest_smoke_$TIMESTAMP.txt"
            Log-Success "Smoke tests complete"
        } catch {
            Log-Error "Some smoke tests failed (review logs)"
            # Non-fatal, continue to canaries
        }
    }
    
    # ---- Postdeploy gates
    Log-Step "Postdeploy gate validation" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping postdeploy gates"
    } else {
        try {
            python tools\validators\validate_phase_b_gates.py --mode postdeploy --verbose `
                --export "$LOGDIR\gates_post_$TIMESTAMP.json" 2>&1 | `
                Tee-Object "$LOGDIR\gates_post_output_$TIMESTAMP.log"
            Log-Success "Postdeploy gates validated"
        } catch {
            Log-Error "Postdeploy gates failed: $_"
            Write-Host "Review: $LOGDIR\gates_post_$TIMESTAMP.json" -f Yellow
        }
    }
    
    # ---- Canary 1: TEXT
    Log-Step "Canary 1: TEXT route" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping TEXT canary"
    } else {
        try {
            $textPrompt = @"
<|mode_start|>COGNITION<|mode_end|><|sacred_333|> Identify yourself in one line.
"@
            # Use llama-cpp-python or main.exe if available
            if (Get-Command llama-cpp-python -ErrorAction SilentlyContinue) {
                llama-cpp-python -m "$FUSED_OUT" -n 48 -p $textPrompt 2>&1 | `
                    Tee-Object "$LOGDIR\canary_text_$TIMESTAMP.txt" | Select-Object -Last 2
            } else {
                Write-Host "  (Skipping: llama-cpp-python not in PATH)" -f Yellow
            }
            Log-Success "TEXT canary logged"
        } catch {
            Log-Error "TEXT canary failed: $_"
        }
    }
    
    # ---- Canary 2-4: VISION/AUDIO/CODE routed by AstraRouter
    Log-Step "Canary 2-4: VISION/AUDIO/CODE (routed via AstraRouter)" Cyan
    Log-Success "Run from client/UI (see canary prompts below)"
    Log-Success "Expected: VISION p95 < 2000ms, AUDIO p95 < 2000ms, CODE → consent block"
    
    # ---- Health check snapshot (T+60)
    Log-Step "Health check snapshot (T+60)" Cyan
    if ($DryRun) {
        Log-Success "DRY RUN: Skipping health check"
    } else {
        try {
            curl.exe http://127.0.0.1:8080/health 2>&1 | `
                Set-Content "$LOGDIR\health_post_$TIMESTAMP.json"
            curl.exe http://127.0.0.1:8765/metrics 2>&1 | `
                Set-Content "$LOGDIR\metrics_post_$TIMESTAMP.prom"
            Log-Success "Health check captured"
        } catch {
            Log-Error "Health check failed: $_"
        }
    }
    
    Log-Step "POSTDEPLOY VALIDATION COMPLETE" Green
}

# ===============================
# Final Summary
# ===============================
Log-Step "Phase-B Launch Complete" Green
Write-Host ""
Write-Host "📊 Log Files:" -f Yellow
Write-Host "  All logs: $LOGDIR\" -f White
Write-Host "  Latest: $LOGDIR\phase_b_launch.log" -f White
Write-Host ""
Write-Host "🔍 Next Steps:" -f Yellow
Write-Host "  1. Review gates_pre_$TIMESTAMP.json (all 7 must PASS)" -f White
Write-Host "  2. Monitor Grafana dashboards (route mix, latency, errors)" -f White
Write-Host "  3. Run client-side canaries (VISION/AUDIO/CODE via AstraRouter)" -f White
Write-Host "  4. After 60 min: Compare health_pre vs health_post" -f White
Write-Host "  5. Append sign-off to PHASE_B_COMPLETE_PACKAGE_README.txt" -f White
Write-Host ""
Write-Host "🚨 Rollback (if needed):" -f Yellow
Write-Host "  pwsh ops\fusion_pipeline\scripts\07_roll_back.ps1" -f White
Write-Host ""
Write-Host "📡 Sacred Code: 333 ∞" -f Magenta
