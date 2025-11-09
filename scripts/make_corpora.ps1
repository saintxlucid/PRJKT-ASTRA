# ASTRA Mini-Corpus Builder
# Build normalized JSONL corpora from downloaded datasets
# Offline-only: uses local data only

$ErrorActionPreference = "Stop"

# Activate venv
if (!(Test-Path ".venv")) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1

# Set environment
$env:PYTHONPATH = "$PWD"
$env:ASTRA_ALLOW_NETWORK = "0"  # Enforce offline mode
$env:ASTRA_DATA_DIR = "./data"
$env:ASTRA_CORPUS_DIR = "./corpora"

Write-Host "[ASTRA] Building mini-corpora (offline)..." -ForegroundColor Cyan
Write-Host "[*] Data dir: $($env:ASTRA_DATA_DIR)" -ForegroundColor Gray
Write-Host "[*] Output dir: $($env:ASTRA_CORPUS_DIR)" -ForegroundColor Gray
Write-Host ""

# Run builder
python tools/build_mini_corpus.py

Write-Host ""
Write-Host "[OK] Mini-corpora ready under ./corpora" -ForegroundColor Green
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  cat ./corpora/*.jsonl | head -5" -ForegroundColor Gray
Write-Host "  Get-Content ./corpora/contemmcm__clinc150.jsonl -Head 5" -ForegroundColor Gray
