# =====================================================================
# ASTRA Fusion Pipeline - Step 1: Prepare Model Environment
# =====================================================================
# Purpose: Set up paths and directories for GGUF rebuild process
# Sacred Code: 333
# =====================================================================

Write-Host "🔧 ASTRA Fusion Pipeline - Environment Preparation" -ForegroundColor Cyan
Write-Host "Sacred Code: 333" -ForegroundColor Yellow
Write-Host ""

# Core paths
$env:LLAMA_CPP_DIR = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-local\backend\bin\llama.cpp"
$env:HF_SRC        = "X:\models\gpt-oss-20b-hf"   # HuggingFace format (safetensors)
$env:OUT_DIR       = "X:\models\ASTRA_CORE_BUILD"

# Validate llama.cpp exists
if (-not (Test-Path $env:LLAMA_CPP_DIR)) {
    Write-Host "❌ ERROR: llama.cpp not found at: $env:LLAMA_CPP_DIR" -ForegroundColor Red
    Write-Host "   Please build llama.cpp or update the path." -ForegroundColor Yellow
    exit 1
}

# Validate source model exists
if (-not (Test-Path $env:HF_SRC)) {
    Write-Host "⚠️  WARNING: HuggingFace model not found at: $env:HF_SRC" -ForegroundColor Yellow
    Write-Host "   If using a different model, update `$env:HF_SRC in this script." -ForegroundColor Yellow
    Write-Host "   Continuing anyway..." -ForegroundColor Yellow
}

# Create output directory
Write-Host "📁 Creating output directory..."
New-Item -ItemType Directory -Path $env:OUT_DIR -Force -ErrorAction SilentlyContinue | Out-Null

if (Test-Path $env:OUT_DIR) {
    Write-Host "   ✅ Output directory ready: $env:OUT_DIR" -ForegroundColor Green
} else {
    Write-Host "   ❌ Failed to create output directory" -ForegroundColor Red
    exit 1
}

# Display configuration
Write-Host ""
Write-Host "Environment Configuration:" -ForegroundColor Cyan
Write-Host "  LLAMA_CPP_DIR : $env:LLAMA_CPP_DIR" -ForegroundColor White
Write-Host "  HF_SRC        : $env:HF_SRC" -ForegroundColor White
Write-Host "  OUT_DIR       : $env:OUT_DIR" -ForegroundColor White
Write-Host ""
Write-Host "✅ Environment preparation complete." -ForegroundColor Green
Write-Host "   Next: Run 02_convert_with_tokens.ps1" -ForegroundColor Yellow
