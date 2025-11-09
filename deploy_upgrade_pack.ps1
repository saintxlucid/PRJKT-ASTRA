# deploy_upgrade_pack.ps1
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# --- Paths ---
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ROOT) { $ROOT = (Get-Location).Path }
$PY   = Join-Path $ROOT ".venv\Scripts\python.exe"
$HF   = Join-Path $ROOT ".hf_cache"
$TORCH= Join-Path $ROOT ".torch_cache"
$MODEL_DIR = Join-Path $ROOT "models\bge-m3"
$CHROMA    = Join-Path $ROOT "data\chromadb"
$ENVFILE   = Join-Path $ROOT ".env"

# --- Ensure directories ---
$null = New-Item -Force -ItemType Directory $HF,$TORCH,$MODEL_DIR,$CHROMA 2>$null

# --- Persist cache env to X: (current session + future shells) ---
$env:HF_HOME=$HF; $env:TRANSFORMERS_CACHE=$HF; $env:SENTENCE_TRANSFORMERS_HOME=$HF; $env:TORCH_HOME=$TORCH
setx HF_HOME $HF | Out-Null
setx TRANSFORMERS_CACHE $HF | Out-Null
setx SENTENCE_TRANSFORMERS_HOME $HF | Out-Null
setx TORCH_HOME $TORCH | Out-Null

# --- Helpers to edit .env ---
function Set-EnvLine($Key,$Val) {
  if (-not (Test-Path $ENVFILE)) { New-Item -ItemType File -Path $ENVFILE | Out-Null }
  $content = (Get-Content $ENVFILE -Raw -ErrorAction SilentlyContinue) -as [string]
  if ($content -match "(?m)^\s*$Key\s*=") {
    $content = [regex]::Replace($content, "(?m)^\s*$Key\s*=.*$", "$Key=$Val")
  } else {
    if ($content -and -not $content.EndsWith("`r`n")) { $content += "`r`n" }
    $content += "$Key=$Val`r`n"
  }
  Set-Content -Path $ENVFILE -Value $content -Encoding UTF8
}

# --- Ensure python-dotenv so config can load .env automatically (optional) ---
Step "Installing python-dotenv (optional)"
& $PY -m pip install --quiet python-dotenv
if ($LASTEXITCODE -ne 0) { Write-Warning "python-dotenv install failed (non-fatal)"; }

# --- Download BGE-M3 to X:\PROJECT_ASTRA\models\bge-m3 ---
Step "Downloading BAAI/bge-m3 to $MODEL_DIR"
$HFCLI = Join-Path $ROOT ".venv\Scripts\huggingface-cli.exe"
& $HFCLI download "BAAI/bge-m3" --local-dir $MODEL_DIR --local-dir-use-symlinks False
if ($LASTEXITCODE -ne 0) { throw "Model download failed. Check internet / disk space on X:." }

# --- Update .env for embeddings + collections ---
Step "Updating .env"
Set-EnvLine "ASTRA_EMBEDDINGS_MODEL_PATH" ($MODEL_DIR -replace "\\","/")
Set-EnvLine "ASTRA_EMBEDDINGS_BATCH" "32"
# your current collection name (you said it was 'astra_memory')
Set-EnvLine "ASTRA_VECTOR_COLLECTION" "astra_memory"
Set-EnvLine "ASTRA_VECTOR_COLLECTION_NEW" "astra_memories_m3"

# --- Run re-embedding (BGE-M3) ---
Step "Re-embedding existing memories with BGE-M3"
& $PY "$ROOT\scripts\reembed_bge_m3.py"
if ($LASTEXITCODE -ne 0) { throw "reembed_bge_m3.py failed" }

# --- Switch runtime to new collection ---
Step "Switching runtime collection to astra_memories_m3"
Set-EnvLine "ASTRA_VECTOR_COLLECTION" "astra_memories_m3"

Write-Host "`n✅ Upgrade Pack deployment steps completed." -ForegroundColor Green
Write-Host "Next: restart your backend so it picks up the new .env." -ForegroundColor Yellow
