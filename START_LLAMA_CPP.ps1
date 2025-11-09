# ASTRA 3.0 - Start llama.cpp Server
# Quick-start script for gpt-oss-20b model

$PORT = 9010
$MODEL = "models\gpt-oss-20b-q4_k_m.gguf"
$CTX = 16384
$BATCH = 384
$THREADS = 12
$GPU_LAYERS = 30
$PARALLEL = 2

Write-Host "`n🌌 ASTRA Adaptive Governor - llama.cpp Server" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 → ∞`n" -ForegroundColor Magenta

# Check if model exists
if (-not (Test-Path $MODEL)) {
    Write-Host "❌ Model not found: $MODEL" -ForegroundColor Red
    Write-Host "`nPlease download the model first:" -ForegroundColor Yellow
    Write-Host "  https://huggingface.co/<model-repo>/resolve/main/gpt-oss-20b-q4_k_m.gguf" -ForegroundColor Gray
    exit 1
}

# Check if llama-server exists
$LLAMA_SERVER = Get-Command llama-server.exe -ErrorAction SilentlyContinue
if (-not $LLAMA_SERVER) {
    $LLAMA_SERVER = Get-Command .\llama-server.exe -ErrorAction SilentlyContinue
    if (-not $LLAMA_SERVER) {
        Write-Host "❌ llama-server.exe not found" -ForegroundColor Red
        Write-Host "`nPlease install llama.cpp:" -ForegroundColor Yellow
        Write-Host "  https://github.com/ggerganov/llama.cpp/releases" -ForegroundColor Gray
        exit 1
    }
}

Write-Host "📊 Configuration:" -ForegroundColor Green
Write-Host "  Port:        $PORT" -ForegroundColor Gray
Write-Host "  Model:       $MODEL" -ForegroundColor Gray
Write-Host "  Context:     $CTX tokens" -ForegroundColor Gray
Write-Host "  Batch:       $BATCH" -ForegroundColor Gray
Write-Host "  Threads:     $THREADS" -ForegroundColor Gray
Write-Host "  GPU Layers:  $GPU_LAYERS" -ForegroundColor Gray
Write-Host "  Parallel:    $PARALLEL" -ForegroundColor Gray
Write-Host ""

# Start server
Write-Host "🚀 Starting llama.cpp server..." -ForegroundColor Cyan
Write-Host ""

& llama-server.exe `
    --model $MODEL `
    --port $PORT `
    --ctx-size $CTX `
    --batch-size $BATCH `
    --threads $THREADS `
    --ngl $GPU_LAYERS `
    --parallel $PARALLEL `
    --embeddings `
    --log-disable `
    --metrics

# Note: The adaptive governor will adjust these parameters dynamically
# based on system load, temperature, and performance metrics
