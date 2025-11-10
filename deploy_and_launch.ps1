# ⚡ ASTRA 3.0 — INSTANT DEPLOYMENT + TUI LAUNCH
# Zero-drama setup: starts all backend services + launches TUI
# Usage: .\deploy_and_launch.ps1

$ErrorActionPreference = "Stop"
$WarningPreference = "SilentlyContinue"

Write-Host "`n════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🟢 ASTRA 3.0 — INSTANT DEPLOYMENT + TUI LAUNCH" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Check Docker
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "🐳 Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    Write-Host "  ✅ $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker not found. Install Docker Desktop or Docker CLI." -ForegroundColor Red
    Write-Host "     https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Check/Create .env
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n📝 Checking .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  Creating .env with default values..." -ForegroundColor Cyan
    @"
# ASTRA 3.0 Configuration
ENVIRONMENT=production
SECRET_PROVIDER=env

# Database
POSTGRES_PASSWORD=astra_pass
DATABASE_URL=postgresql://astra:astra_pass@postgres:5432/astra

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
JWT_SECRET=astra_secret_key_change_in_production

# LLM (pick ONE)
LLAMA_CPP_BASE_URL=http://localhost:9010/v1
# OLLAMA_BASE_URL=http://localhost:11434/v1
# VLLM_BASE_URL=http://localhost:9020/v1

# Observability
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
LOG_LEVEL=info
"@ | Out-File -Encoding UTF8 ".env"
    Write-Host "  ✅ .env created" -ForegroundColor Green
} else {
    Write-Host "  ✅ .env exists" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Start Infrastructure Services
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n🚀 Starting infrastructure services..." -ForegroundColor Yellow

Write-Host "   Starting Redis (cache)..." -ForegroundColor Gray
docker run -d --name astra_redis --rm -p 6379:6379 redis:7-alpine 2>$null
Start-Sleep -Seconds 2

Write-Host "   Starting PostgreSQL (database)..." -ForegroundColor Gray
docker run -d --name astra_postgres --rm `
  -e POSTGRES_DB=astra `
  -e POSTGRES_USER=astra `
  -e POSTGRES_PASSWORD=astra_pass `
  -p 5432:5432 `
  postgres:15 2>$null
Start-Sleep -Seconds 3

Write-Host "   Starting Jaeger (tracing)..." -ForegroundColor Gray
docker run -d --name astra_jaeger --rm `
  -p 16686:16686 `
  -p 4318:4318 `
  -e COLLECTOR_OTLP_ENABLED=true `
  jaegertracing/all-in-one:latest 2>$null
Start-Sleep -Seconds 2

Write-Host "   Starting etcd (coordination)..." -ForegroundColor Gray
docker run -d --name astra_etcd --rm `
  -e ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379 `
  -e ETCD_ADVERTISE_CLIENT_URLS=http://0.0.0.0:2379 `
  -p 2379:2379 `
  quay.io/coreos/etcd:v3.5.10 2>$null
Start-Sleep -Seconds 2

Write-Host "  ✅ Infrastructure started" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Verify Services
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n🔍 Verifying services..." -ForegroundColor Yellow

$services = @(
    @{name="Redis"; port=6379},
    @{name="PostgreSQL"; port=5432},
    @{name="Jaeger"; port=16686},
    @{name="etcd"; port=2379}
)

foreach ($svc in $services) {
    $portOpen = $false
    try {
        $socket = New-Object System.Net.Sockets.TcpClient
        $socket.Connect("localhost", $svc.port)
        $socket.Close()
        $portOpen = $true
    } catch {}
    
    if ($portOpen) {
        Write-Host "  ✅ $($svc.name) running on port $($svc.port)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $($svc.name) not responding on port $($svc.port)" -ForegroundColor Yellow
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: Mock ASTRA Services (for testing without full build)
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n🎯 Setting up ASTRA services..." -ForegroundColor Yellow

# Check if Python mock services exist, if not explain
if (Test-Path "src/astra/api/main.py") {
    Write-Host "   FastAPI found - would start main:app" -ForegroundColor Cyan
} else {
    Write-Host "   ℹ️  Note: Full ASTRA services (master, memory, sigil-gate) require" -ForegroundColor Gray
    Write-Host "       source code to be built. This setup uses Docker for infra." -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: Check Python & Dependencies
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n🐍 Checking Python & dependencies..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python not found" -ForegroundColor Red
    exit 1
}

# Check required packages
$packages = @("requests", "prompt_toolkit")
foreach ($pkg in $packages) {
    try {
        python -c "import $pkg" 2>$null
        Write-Host "  ✅ $pkg installed" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  $pkg not found, installing..." -ForegroundColor Yellow
        python -m pip install $pkg -q
        Write-Host "     ✅ installed" -ForegroundColor Green
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7: Launch TUI
# ═══════════════════════════════════════════════════════════════════════════════

Write-Host "`n════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ SETUP COMPLETE" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host @"

🌐 Service Endpoints:
  • Jaeger UI:     http://localhost:16686
  • Redis:         localhost:6379
  • PostgreSQL:    localhost:5432
  • etcd:          localhost:2379

📌 IMPORTANT:
  You still need to start ONE model endpoint:
  
  Option A) Ollama (easiest):
    ollama serve
  
  Option B) llama.cpp (GPU optimized):
    X:\llama.cpp\server.exe -m "X:\Models\gpt-oss-20b\gpt-oss-20b.Q4_K_M.gguf" --port 9010
  
  Then the ASTRA backend services (if not using Docker):
    python -m uvicorn src.astra.api.main:app --host 0.0.0.0 --port 8000

🚀 Now launching ASTRA TUI...
  → Type /help for commands
  → Type /health to check services
  → Type your message to chat

"@

Write-Host "Press ENTER to launch TUI..." -ForegroundColor Cyan
Read-Host

python .\astra_tui.py

Write-Host "`n👋 ASTRA TUI closed.`n" -ForegroundColor Cyan
Write-Host "Tip: Services are still running. Stop them with:" -ForegroundColor Gray
Write-Host "  docker stop astra_redis astra_postgres astra_jaeger astra_etcd`n" -ForegroundColor Gray
