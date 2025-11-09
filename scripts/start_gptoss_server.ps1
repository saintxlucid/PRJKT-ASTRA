# Start GPT-OSS via llama.cpp server
# Production reliability validation - CPU mode, 32GB RAM

$ErrorActionPreference = "Stop"

# Configuration from .env
$MODEL = "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"
$LLAMA_SERVER = "X:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe"
$SERVER_HOST = "127.0.0.1"
$PORT = 8001
$THREADS = $Env:NUMBER_OF_PROCESSORS
if (-not $THREADS) { $THREADS = 8 }

# Optimized settings for 32GB RAM, CPU-only
$CTX_SIZE = 4096
$BATCH_SIZE = 128
$UBATCH_SIZE = 32
$PARALLEL = 1
$N_GPU_LAYERS = 0  # CPU only

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Starting GPT-OSS llama.cpp Server" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Model:       $MODEL" -ForegroundColor White
Write-Host "Server:      $LLAMA_SERVER" -ForegroundColor White
Write-Host "Endpoint:    http://${SERVER_HOST}:${PORT}" -ForegroundColor White
Write-Host "Context:     $CTX_SIZE tokens" -ForegroundColor White
Write-Host "Threads:     $THREADS" -ForegroundColor White
Write-Host "Batch:       $BATCH_SIZE / $UBATCH_SIZE" -ForegroundColor White
Write-Host "GPU Layers:  $N_GPU_LAYERS (CPU mode)" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Verify files exist
if (-not (Test-Path $MODEL)) {
    Write-Host "ERROR: Model not found: $MODEL" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $LLAMA_SERVER)) {
    Write-Host "ERROR: llama-server.exe not found: $LLAMA_SERVER" -ForegroundColor Red
    exit 1
}

# Check if port is already in use
$portCheck = netstat -ano | findstr ":$PORT"
if ($portCheck) {
    Write-Host "WARNING: Port $PORT already in use" -ForegroundColor Yellow
    Write-Host $portCheck
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "Starting llama.cpp server (this may take 30-60 seconds)..." -ForegroundColor Yellow

# Launch in new window
Start-Process pwsh -ArgumentList @(
    "-NoExit"
    "-Command"
    "& '$LLAMA_SERVER' --model '$MODEL' --host $SERVER_HOST --port $PORT --threads $THREADS --parallel $PARALLEL --n-gpu-layers $N_GPU_LAYERS --ctx-size $CTX_SIZE --batch-size $BATCH_SIZE --ubatch-size $UBATCH_SIZE --cache-type-k q8_0 --cache-type-v q8_0"
)

# Wait for server to be ready
Write-Host "Waiting for server to respond..." -ForegroundColor Yellow
$maxAttempts = 60
$attempt = 0
$ready = $false

while (-not $ready -and $attempt -lt $maxAttempts) {
    $attempt++
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://${SERVER_HOST}:${PORT}/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $ready = $true
        }
    } catch {
        # Still waiting
    }
    
    if ($attempt % 5 -eq 0) {
        Write-Host "  Still waiting... ($attempt seconds)" -ForegroundColor Gray
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "llama.cpp server is ready!" -ForegroundColor Green
    Write-Host "  Health: http://${SERVER_HOST}:${PORT}/health" -ForegroundColor White
    Write-Host "  Completions: http://${SERVER_HOST}:${PORT}/v1/completions" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Server did not respond within $maxAttempts seconds" -ForegroundColor Red
    Write-Host "  Check the llama.cpp window for errors" -ForegroundColor Yellow
    exit 1
}
