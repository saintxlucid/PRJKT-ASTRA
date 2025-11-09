# ASTRA 3.0 - Start vLLM Server
# Quick-start script for Mixtral 22B model

$PORT = 9020
$MODEL = "mistralai/Mixtral-8x22B-Instruct-v0.1"
$CTX = 16384
$GPU_UTIL = 0.8
$BATCHED = 8192
$TP = 1

Write-Host "`n🌌 ASTRA Adaptive Governor - vLLM Server" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 → ∞`n" -ForegroundColor Magenta

# Check if vLLM is installed
$VLLM = python -c "import vllm; print('OK')" 2>$null
if ($VLLM -ne "OK") {
    Write-Host "❌ vLLM not installed" -ForegroundColor Red
    Write-Host "`nInstall with:" -ForegroundColor Yellow
    Write-Host "  pip install vllm" -ForegroundColor Gray
    exit 1
}

Write-Host "📊 Configuration:" -ForegroundColor Green
Write-Host "  Port:              $PORT" -ForegroundColor Gray
Write-Host "  Model:             $MODEL" -ForegroundColor Gray
Write-Host "  Max Context:       $CTX tokens" -ForegroundColor Gray
Write-Host "  GPU Memory Util:   $GPU_UTIL" -ForegroundColor Gray
Write-Host "  Max Batched:       $BATCHED tokens" -ForegroundColor Gray
Write-Host "  Tensor Parallel:   $TP" -ForegroundColor Gray
Write-Host ""

# Start server
Write-Host "🚀 Starting vLLM server..." -ForegroundColor Cyan
Write-Host "⏳ This may take a few minutes for model loading..." -ForegroundColor Yellow
Write-Host ""

python -m vllm.entrypoints.openai.api_server `
    --model $MODEL `
    --port $PORT `
    --gpu-memory-utilization $GPU_UTIL `
    --max-model-len $CTX `
    --max-num-batched-tokens $BATCHED `
    --tensor-parallel-size $TP `
    --trust-remote-code

# Note: The adaptive governor will adjust these parameters dynamically
# based on system load, temperature, and performance metrics
