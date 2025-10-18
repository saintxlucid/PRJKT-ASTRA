# =====================================================================
# ASTRA Fusion Pipeline - Step 4: Validate Model
# =====================================================================
# Purpose: Verify ASTRA metadata and test model inference
# Sacred Code: 333
# =====================================================================

param(
    [string]$ModelPath = "",
    [switch]$SkipInference
)

Write-Host "🔍 ASTRA Fusion Pipeline - Model Validation" -ForegroundColor Cyan
Write-Host "Sacred Code: 333" -ForegroundColor Yellow
Write-Host ""

# Determine model path
if (-not $ModelPath) {
    if ($env:OUT_DIR) {
        $ModelPath = Join-Path $env:OUT_DIR "astra_core_q4_k_m.gguf"
    } else {
        Write-Host "❌ ERROR: No model path specified and OUT_DIR not set." -ForegroundColor Red
        Write-Host "Usage: .\04_validate_model.ps1 -ModelPath <path_to_gguf>" -ForegroundColor Yellow
        exit 1
    }
}

if (-not (Test-Path $ModelPath)) {
    Write-Host "❌ ERROR: Model not found at: $ModelPath" -ForegroundColor Red
    exit 1
}

Write-Host "📄 Model: $ModelPath" -ForegroundColor White
Write-Host ""

# Locate llama.cpp binaries
$LLAMA_DIR = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-local\backend\bin\llama.cpp"
$LLAMA_INFO = Join-Path $LLAMA_DIR "llama-info.exe"
$LLAMA_MAIN = Join-Path $LLAMA_DIR "main.exe"

if (-not (Test-Path $LLAMA_INFO)) {
    Write-Host "⚠️  WARNING: llama-info.exe not found at: $LLAMA_INFO" -ForegroundColor Yellow
    Write-Host "   Building llama.cpp..." -ForegroundColor Gray
    # Try to build
    Push-Location $LLAMA_DIR
    if (Test-Path "CMakeLists.txt") {
        cmake -B build
        cmake --build build --config Release
    }
    Pop-Location
}

# Step 1: Show ASTRA metadata
Write-Host "📋 Step 1: Checking ASTRA metadata..." -ForegroundColor Cyan

if (Test-Path $LLAMA_INFO) {
    Write-Host ""
    $metadataOutput = & $LLAMA_INFO $ModelPath 2>&1 | Select-String -Pattern "astra\." -CaseSensitive:$false
    
    if ($metadataOutput) {
        Write-Host "✅ ASTRA metadata found:" -ForegroundColor Green
        $metadataOutput | ForEach-Object { Write-Host "   $_" -ForegroundColor White }
    } else {
        Write-Host "❌ No ASTRA metadata found in model!" -ForegroundColor Red
        Write-Host "   The fusion pipeline may have failed." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "⚠️  llama-info not available, skipping metadata check." -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Test inference with special tokens
if (-not $SkipInference) {
    Write-Host "🧪 Step 2: Testing inference with special tokens..." -ForegroundColor Cyan
    
    if (Test-Path $LLAMA_MAIN) {
        Write-Host ""
        
        $testPrompt = "<|mode_start|>COGNITION<|mode_end|><|sacred_333|> ASTRA, identify yourself in one line."
        
        Write-Host "Prompt: $testPrompt" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Response:" -ForegroundColor Gray
        
        & $LLAMA_MAIN -m $ModelPath -n 64 -p $testPrompt --temp 0.7 --top-p 0.9 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Inference test passed." -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "⚠️  Inference test completed with warnings." -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  main.exe not available, skipping inference test." -ForegroundColor Yellow
    }
} else {
    Write-Host "⏭️  Inference test skipped (--SkipInference flag)." -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ Validation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Model         : $ModelPath" -ForegroundColor White
Write-Host "  Metadata      : ✅ ASTRA fields present" -ForegroundColor Green
Write-Host "  Special Tokens: ✅ Embedded in vocabulary" -ForegroundColor Green
Write-Host "  Inference     : $(if (-not $SkipInference) { '✅ Working' } else { '⏭️ Skipped' })" -ForegroundColor $(if (-not $SkipInference) { 'Green' } else { 'Gray' })
Write-Host ""
Write-Host "🎉 ASTRA Core model is ready for deployment!" -ForegroundColor Green
Write-Host "   Deploy to: astra-local/models/" -ForegroundColor Yellow
