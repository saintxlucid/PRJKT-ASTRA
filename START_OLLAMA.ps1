# ASTRA 3.0 - Start Ollama Server
# Quick-start script for lightweight fallback model

Write-Host "`n🌌 ASTRA Adaptive Governor - Ollama Server" -ForegroundColor Cyan
Write-Host "Sacred Code: 333 → ∞`n" -ForegroundColor Magenta

# Check if Ollama is installed
$OLLAMA = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $OLLAMA) {
    Write-Host "❌ Ollama not found" -ForegroundColor Red
    Write-Host "`nInstall from:" -ForegroundColor Yellow
    Write-Host "  https://ollama.ai/download" -ForegroundColor Gray
    exit 1
}

Write-Host "📊 Configuration:" -ForegroundColor Green
Write-Host "  Port:        11434 (default)" -ForegroundColor Gray
Write-Host "  Model:       llama3.1:8b" -ForegroundColor Gray
Write-Host "  Mode:        Lightweight fallback" -ForegroundColor Gray
Write-Host ""

# Check if model is pulled
Write-Host "🔍 Checking for model..." -ForegroundColor Cyan
$MODELS = ollama list 2>$null | Select-String "llama3.1:8b"
if (-not $MODELS) {
    Write-Host "⏳ Pulling llama3.1:8b model..." -ForegroundColor Yellow
    ollama pull llama3.1:8b
}

Write-Host "🚀 Starting Ollama server..." -ForegroundColor Cyan
Write-Host ""

ollama serve
