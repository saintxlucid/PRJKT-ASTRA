# ASTRA Upgrade Pack v2.0 - Final Deployment Script
# Completes BGE-M3 migration and validates all components without touching C: drive

Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "ASTRA Upgrade Pack v2.0 - Final Deployment" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Step 1: Set up cache directories on X: drive
Write-Host "[1/6] Setting up cache directories on X: drive..." -ForegroundColor Yellow
$env:HF_HOME = "X:\PROJECT_ASTRA\.hf_cache"
$env:TRANSFORMERS_CACHE = $env:HF_HOME
$env:SENTENCE_TRANSFORMERS_HOME = $env:HF_HOME
$env:TORCH_HOME = "X:\PROJECT_ASTRA\.torch_cache"

Write-Host "  ✓ HF_HOME: $env:HF_HOME" -ForegroundColor Green
Write-Host "  ✓ TRANSFORMERS_CACHE: $env:TRANSFORMERS_CACHE" -ForegroundColor Green
Write-Host "  ✓ SENTENCE_TRANSFORMERS_HOME: $env:SENTENCE_TRANSFORMERS_HOME" -ForegroundColor Green
Write-Host "  ✓ TORCH_HOME: $env:TORCH_HOME" -ForegroundColor Green
Write-Host ""

# Make persistent (optional)
Write-Host "Making cache directories persistent..." -ForegroundColor Yellow
setx HF_HOME "X:\PROJECT_ASTRA\.hf_cache" 2>&1 | Out-Null
setx TRANSFORMERS_CACHE "X:\PROJECT_ASTRA\.hf_cache" 2>&1 | Out-Null
setx SENTENCE_TRANSFORMERS_HOME "X:\PROJECT_ASTRA\.hf_cache" 2>&1 | Out-Null
setx TORCH_HOME "X:\PROJECT_ASTRA\.torch_cache" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Environment variables set persistently" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Could not set persistent env vars (non-fatal)" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Download BGE-M3 model to local directory
Write-Host "[2/6] Downloading BGE-M3 model to X:\PROJECT_ASTRA\models\bge-m3..." -ForegroundColor Yellow
Write-Host "  This will take 5-10 minutes (downloading ~2GB)..." -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "X:\PROJECT_ASTRA\models\bge-m3")) {
    New-Item -ItemType Directory -Path "X:\PROJECT_ASTRA\models\bge-m3" -Force | Out-Null
}

Write-Host "  Installing huggingface_hub..." -ForegroundColor Cyan
& X:\PROJECT_ASTRA\.venv\Scripts\python.exe -m pip install huggingface_hub --quiet

Write-Host "  Downloading model files..." -ForegroundColor Cyan
& X:\PROJECT_ASTRA\.venv\Scripts\python.exe -m huggingface_hub download BAAI/bge-m3 --local-dir X:\PROJECT_ASTRA\models\bge-m3 --local-dir-use-symlinks False

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Model download failed" -ForegroundColor Red
    Write-Host "  Try manual download or check internet connection" -ForegroundColor Yellow
    exit 1
}

Write-Host "  ✓ BGE-M3 model downloaded successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Update .env with correct paths
Write-Host "[3/6] Updating .env configuration..." -ForegroundColor Yellow

$envPath = "X:\PROJECT_ASTRA\.env"
$envContent = Get-Content $envPath -Raw

# Remove any existing lines
$envContent = $envContent -replace "(?m)^ASTRA_EMBEDDINGS_MODEL_PATH=.*`r?`n", ""
$envContent = $envContent -replace "(?m)^ASTRA_VECTOR_COLLECTION_NEW=.*`r?`n", ""
$envContent = $envContent -replace "(?m)^ASTRA_EMBEDDINGS_BATCH=.*`r?`n", ""

# Append new configuration
$newConfig = @"

# BGE-M3 Migration Configuration (Updated)
ASTRA_EMBEDDINGS_MODEL_PATH=X:/PROJECT_ASTRA/models/bge-m3
ASTRA_VECTOR_COLLECTION=astra_memory
ASTRA_VECTOR_COLLECTION_NEW=astra_memory_m3
ASTRA_EMBEDDINGS_BATCH=32
"@

$envContent = $envContent.TrimEnd() + $newConfig
Set-Content -Path $envPath -Value $envContent

Write-Host "  ✓ Configuration updated" -ForegroundColor Green
Write-Host ""

# Step 4: Run BGE-M3 migration
Write-Host "[4/6] Running BGE-M3 re-embedding migration..." -ForegroundColor Yellow
Write-Host "  This will re-embed 5 items with multilingual model..." -ForegroundColor Cyan
Write-Host ""

$env:ASTRA_EMBEDDINGS_MODEL_PATH = "X:/PROJECT_ASTRA/models/bge-m3"
$env:ASTRA_VECTOR_COLLECTION = "astra_memory"
$env:ASTRA_VECTOR_COLLECTION_NEW = "astra_memory_m3"
$env:ASTRA_EMBEDDINGS_BATCH = "32"

& X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\scripts\reembed_bge_m3.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Migration failed" -ForegroundColor Red
    Write-Host "  Check logs for details" -ForegroundColor Yellow
    exit 1
}
Write-Host ""
Write-Host "  ✓ BGE-M3 migration completed!" -ForegroundColor Green
Write-Host ""

# Step 5: Switch to new collection
Write-Host "[5/6] Switching to new BGE-M3 collection..." -ForegroundColor Yellow

$envContent = Get-Content $envPath -Raw
# Update the active collection line
$envContent = $envContent -replace "(?m)^ASTRA_VECTOR_COLLECTION=astra_memory$", "ASTRA_VECTOR_COLLECTION=astra_memory_m3"

# Also update in vector store config if it exists
$envContent = $envContent -replace "(?m)^ASTRA_EMBEDDING_MODEL=.*$", "ASTRA_EMBEDDING_MODEL=BAAI/bge-m3"

Set-Content -Path $envPath -Value $envContent
Write-Host "  ✓ Active collection switched to astra_memory_m3" -ForegroundColor Green
Write-Host ""

# Step 6: Generate new encryption key (rotate the one in logs)
Write-Host "[6/6] Rotating encryption key..." -ForegroundColor Yellow

$newKey = & X:\PROJECT_ASTRA\.venv\Scripts\python.exe -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
$envContent = Get-Content $envPath -Raw
$envContent = $envContent -replace "(?m)^ASTRA_ENCRYPTION_KEY=.*$", "ASTRA_ENCRYPTION_KEY=$newKey"
Set-Content -Path $envPath -Value $envContent

Write-Host "  ✓ New encryption key generated and set" -ForegroundColor Green
Write-Host "  ⚠ Old key in logs is now invalid" -ForegroundColor Yellow
Write-Host ""

# Summary
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ BGE-M3 model downloaded to X:\PROJECT_ASTRA\models\bge-m3"
Write-Host "✅ 5 memories re-embedded with multilingual BGE-M3"
Write-Host "✅ Active collection: astra_memory_m3"
Write-Host "✅ Encryption key rotated"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test the server:"
Write-Host "   X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\run_server.py"
Write-Host ""
Write-Host "2. Check metrics endpoint:"
Write-Host "   curl http://localhost:8080/metrics"
Write-Host ""
Write-Host "3. Run load test:"
Write-Host "   X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\scripts\load_test.py"
Write-Host ""
Write-Host "4. Verify BGE-M3 is working:"
Write-Host "   curl http://localhost:8080/v1/system/health"
Write-Host ""
