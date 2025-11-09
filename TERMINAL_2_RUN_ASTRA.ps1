# ⚡ TERMINAL 2: Run ASTRA Demo
# Wait until Terminal 1 shows "llama_new_context_with_model"
# Then copy and paste this entire block into a NEW PowerShell window

Write-Host "🌌 Configuring ASTRA for local LLM..." -ForegroundColor Cyan

$env:ASTRA_LLM_BASE_URL="http://localhost:9010/v1"
$env:ASTRA_LLM_MODEL_NAME="gpt-oss-20b"
$env:ASTRA_LLM_API_KEY="dummy"

Write-Host "✅ Environment configured" -ForegroundColor Green
Write-Host "🚀 Starting ASTRA demo..." -ForegroundColor Cyan
Write-Host ""

cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python quick_start_unified.py demo
