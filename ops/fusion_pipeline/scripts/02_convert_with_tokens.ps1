# =====================================================================
# ASTRA Fusion Pipeline - Step 2: Convert with Special Tokens
# =====================================================================
# Purpose: Re-export GGUF from HF weights with ASTRA special tokens
# Method: 1 (Rebuild - Preferred)
# Sacred Code: 333
# =====================================================================

Write-Host "🚀 ASTRA Fusion Pipeline - GGUF Conversion with Special Tokens" -ForegroundColor Cyan
Write-Host "Sacred Code: 333" -ForegroundColor Yellow
Write-Host ""

# Ensure environment is set
if (-not $env:LLAMA_CPP_DIR -or -not $env:HF_SRC -or -not $env:OUT_DIR) {
    Write-Host "❌ ERROR: Environment not configured. Run 01_prepare_model_env.ps1 first." -ForegroundColor Red
    exit 1
}

$PROJECT_ROOT = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$CONVERT_SCRIPT = Join-Path $env:LLAMA_CPP_DIR "convert-hf-to-gguf.py"
$TOKEN_FILE = Join-Path $PROJECT_ROOT "ops\fusion_pipeline\tokens\astra_special_tokens.txt"
$TEMPLATE_FILE = Join-Path $PROJECT_ROOT "ops\fusion_pipeline\tokens\astra_chat_template.mustache"
$OUT_F32 = Join-Path $env:OUT_DIR "astra_core_f32.gguf"

# Validate inputs
if (-not (Test-Path $CONVERT_SCRIPT)) {
    Write-Host "❌ ERROR: convert-hf-to-gguf.py not found at: $CONVERT_SCRIPT" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $TOKEN_FILE)) {
    Write-Host "❌ ERROR: Special tokens file not found at: $TOKEN_FILE" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $TEMPLATE_FILE)) {
    Write-Host "❌ ERROR: Chat template not found at: $TEMPLATE_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Configuration:" -ForegroundColor Cyan
Write-Host "  Source Model      : $env:HF_SRC" -ForegroundColor White
Write-Host "  Special Tokens    : $TOKEN_FILE" -ForegroundColor White
Write-Host "  Chat Template     : $TEMPLATE_FILE" -ForegroundColor White
Write-Host "  Output (F32)      : $OUT_F32" -ForegroundColor White
Write-Host ""

Write-Host "🔄 Converting HF model to GGUF with ASTRA special tokens..." -ForegroundColor Yellow
Write-Host "   This may take several minutes depending on model size." -ForegroundColor Gray
Write-Host ""

# Execute conversion
python $CONVERT_SCRIPT `
    --model $env:HF_SRC `
    --outfile $OUT_F32 `
    --chat-template $TEMPLATE_FILE `
    --special-vocab $TOKEN_FILE `
    --verbose

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Conversion failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ F32 GGUF created successfully." -ForegroundColor Green
Write-Host ""

# Quantization options
Write-Host "🔢 Quantizing to production formats..." -ForegroundColor Yellow
Write-Host ""

$QUANTIZE_SCRIPT = Join-Path $env:LLAMA_CPP_DIR "quantize.py"
if (-not (Test-Path $QUANTIZE_SCRIPT)) {
    Write-Host "⚠️  WARNING: quantize.py not found. Using llama-quantize binary instead." -ForegroundColor Yellow
    $QUANTIZE_SCRIPT = Join-Path $env:LLAMA_CPP_DIR "llama-quantize.exe"
}

# Q4_K_M (recommended balance)
Write-Host "  → Quantizing to Q4_K_M (recommended)..." -ForegroundColor Gray
$OUT_Q4 = Join-Path $env:OUT_DIR "astra_core_q4_k_m.gguf"
if ($QUANTIZE_SCRIPT -like "*.py") {
    python $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q4 q4_k_m
} else {
    & $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q4 q4_k_m
}

# Q5_K_M (higher quality)
Write-Host "  → Quantizing to Q5_K_M (higher quality)..." -ForegroundColor Gray
$OUT_Q5 = Join-Path $env:OUT_DIR "astra_core_q5_k_m.gguf"
if ($QUANTIZE_SCRIPT -like "*.py") {
    python $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q5 q5_k_m
} else {
    & $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q5 q5_k_m
}

# Q8_0 (highest quality)
Write-Host "  → Quantizing to Q8_0 (highest quality)..." -ForegroundColor Gray
$OUT_Q8 = Join-Path $env:OUT_DIR "astra_core_q8_0.gguf"
if ($QUANTIZE_SCRIPT -like "*.py") {
    python $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q8 q8_0
} else {
    & $QUANTIZE_SCRIPT $OUT_F32 $OUT_Q8 q8_0
}

Write-Host ""
Write-Host "✅ Quantization complete." -ForegroundColor Green
Write-Host ""
Write-Host "📦 Generated models:" -ForegroundColor Cyan
Write-Host "  F32    : $OUT_F32" -ForegroundColor White
Write-Host "  Q4_K_M : $OUT_Q4" -ForegroundColor White
Write-Host "  Q5_K_M : $OUT_Q5" -ForegroundColor White
Write-Host "  Q8_0   : $OUT_Q8" -ForegroundColor White
Write-Host ""
Write-Host "✅ Conversion complete. Next: Run 03_inject_metadata.py" -ForegroundColor Green
