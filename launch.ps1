# ASTRA 3.0 — INSTANT LAUNCH
# Starts Docker services + TUI

Write-Host "`n🟢 ASTRA 3.0 — INSTANT LAUNCH`n" -ForegroundColor Green

# Check .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env..." -ForegroundColor Yellow
    @"
POSTGRES_PASSWORD=astra_pass
DATABASE_URL=postgresql://astra:astra_pass@postgres:5432/astra
REDIS_URL=redis://redis:6379/0
JWT_SECRET=astra_dev_secret
LLAMA_CPP_BASE_URL=http://localhost:9010/v1
JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
"@ | Out-File ".env" -Encoding UTF8
}

# Start infrastructure
Write-Host "Starting Docker services..." -ForegroundColor Yellow

docker run -d --name astra_redis --rm -p 6379:6379 redis:7-alpine 2>$null | Out-Null
docker run -d --name astra_postgres --rm -e POSTGRES_DB=astra -e POSTGRES_USER=astra -e POSTGRES_PASSWORD=astra_pass -p 5432:5432 postgres:15 2>$null | Out-Null
docker run -d --name astra_jaeger --rm -p 16686:16686 -p 4318:4318 -e COLLECTOR_OTLP_ENABLED=true jaegertracing/all-in-one:latest 2>$null | Out-Null

Write-Host "✅ Services started" -ForegroundColor Green
Write-Host "`n📌 IMPORTANT: Start ONE model endpoint in another terminal:" -ForegroundColor Yellow
Write-Host "   ollama serve" -ForegroundColor Cyan
Write-Host "   (or: X:\llama.cpp\server.exe -m model.gguf --port 9010)" -ForegroundColor Cyan

Write-Host "`n🚀 Launching ASTRA TUI..." -ForegroundColor Green
python .\astra_tui.py

Write-Host "`nStopping Docker services..." -ForegroundColor Yellow
docker stop astra_redis astra_postgres astra_jaeger 2>$null | Out-Null
Write-Host "👋 Done." -ForegroundColor Green
