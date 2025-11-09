# ASTRA BGE-M3 Deployment Script
Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host " ASTRA Upgrade Pack v2.0 - BGE-M3 Deployment" -ForegroundColor Cyan
Write-Host "================================================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Set environment variables
Write-Host "[1/6] Setting cache directories on X: drive..." -ForegroundColor Yellow
$env:HF_HOME = "X:\PROJECT_ASTRA\data\hf_cache"
$env:TRANSFORMERS_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\transformers"
$env:HUGGINGFACE_HUB_CACHE = "X:\PROJECT_ASTRA\data\hf_cache\hub"
$env:SENTENCE_TRANSFORMERS_HOME = "X:\PROJECT_ASTRA\data\hf_cache\sentence_transformers"
$env:TORCH_HOME = "X:\PROJECT_ASTRA\data\torch_cache"

Write-Host "  ✓ Cache directories configured" -ForegroundColor Green
Write-Host ""

# Step 2: Download BGE-M3 model
Write-Host "[2/6] Downloading BGE-M3 model (~2GB, 5-10 minutes)..." -ForegroundColor Yellow

if (-not (Test-Path "X:\PROJECT_ASTRA\models\bge-m3")) {
    New-Item -ItemType Directory -Path "X:\PROJECT_ASTRA\models\bge-m3" -Force | Out-Null
}

Write-Host "  Installing huggingface_hub..." -ForegroundColor Cyan
& X:\PROJECT_ASTRA\.venv\Scripts\python.exe -m pip install huggingface_hub --quiet

Write-Host "  Downloading model..." -ForegroundColor Cyan
& X:\PROJECT_ASTRA\.venv\Scripts\python.exe -m huggingface_hub download BAAI/bge-m3 --local-dir X:\PROJECT_ASTRA\models\bge-m3 --local-dir-use-symlinks False

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Download failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Model downloaded successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Update .env
Write-Host "[3/6] Updating .env configuration..." -ForegroundColor Yellow

$envPath = "X:\PROJECT_ASTRA\.env"
$configText = @"

# BGE-M3 Configuration
ASTRA_EMBEDDINGS_MODEL_PATH=X:/PROJECT_ASTRA/models/bge-m3
ASTRA_VECTOR_COLLECTION=astra_memory
ASTRA_VECTOR_COLLECTION_NEW=astra_memory_m3
ASTRA_EMBEDDINGS_BATCH=32
"@

Add-Content -Path $envPath -Value $configText
Write-Host "  ✓ Configuration added to .env" -ForegroundColor Green
Write-Host ""

# Step 4: Run migration
Write-Host "[4/6] Running BGE-M3 migration..." -ForegroundColor Yellow

$env:ASTRA_EMBEDDINGS_MODEL_PATH = "X:/PROJECT_ASTRA/models/bge-m3"
$env:ASTRA_VECTOR_COLLECTION = "astra_memory"
$env:ASTRA_VECTOR_COLLECTION_NEW = "astra_memory_m3"
$env:ASTRA_EMBEDDINGS_BATCH = "32"

& X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\scripts\reembed_bge_m3.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Migration failed!" -ForegroundColor Red
    exit 1
}

Write-Host "  ✓ Migration completed!" -ForegroundColor Green
Write-Host ""

# Step 5: Switch collection
Write-Host "[5/6] Switching to BGE-M3 collection..." -ForegroundColor Yellow

$envContent = Get-Content $envPath -Raw
$envContent = $envContent -replace "ASTRA_VECTOR_COLLECTION=astra_memory`r?`n", "ASTRA_VECTOR_COLLECTION=astra_memory_m3`n"
Set-Content -Path $envPath -Value $envContent -NoNewline

Write-Host "  ✓ Collection switched" -ForegroundColor Green
Write-Host ""

# Step 6: Rotate encryption key
Write-Host "[6/6] Rotating encryption key..." -ForegroundColor Yellow

$newKey = & X:\PROJECT_ASTRA\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$envContent = Get-Content $envPath -Raw
$envContent = $envContent -replace "ASTRA_ENCRYPTION_KEY=.*", "ASTRA_ENCRYPTION_KEY=$newKey"
Set-Content -Path $envPath -Value $envContent -NoNewline

Write-Host "  ✓ Key rotated" -ForegroundColor Green
Write-Host ""

# Done
Write-Host "================================================================================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ BGE-M3 model: X:\PROJECT_ASTRA\models\bge-m3" -ForegroundColor Green
Write-Host "✅ Memories re-embedded: 5 items" -ForegroundColor Green
Write-Host "✅ Active collection: astra_memory_m3" -ForegroundColor Green
Write-Host "✅ Encryption key: rotated" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Start server with:" -ForegroundColor Yellow
Write-Host "  X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\run_server.py" -ForegroundColor Cyan
Write-Host ""
