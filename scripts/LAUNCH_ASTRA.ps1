# ============================================================
# ASTRA CORE LAUNCH SCRIPT  (GPT-OSS edition)
# ============================================================

Write-Host "🔹 Initializing ASTRA Core..." -ForegroundColor Cyan
Set-Location $PSScriptRoot\..

# 1️⃣  Activate Python environment
if (-not (Test-Path ".\.venv")) {
    Write-Host "🪶 Creating virtual environment..."
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

# 2️⃣  Ensure dependencies
Write-Host "📦 Installing/updating dependencies..."
pip install --upgrade pip wheel poetry | Out-Null
poetry install --no-root | Out-Null

# 3️⃣  Verify GPT-OSS model
Write-Host "🔍 Checking GPT-OSS-20B model..."
$verify = python .\scripts\verify_model.py | ConvertFrom-Json
if ($verify.status -ne "ok") {
    Write-Host "❌ Model missing or corrupted. Please place gpt-oss-20b-q4_k_m.gguf in /models." -ForegroundColor Red
    exit 1
}
Write-Host ("✅ Model verified: {0} GB, SHA {1}" -f $verify.size_gb, $verify.sha)

# 4️⃣  Hardware detection
Write-Host "🧠 Detecting hardware..."
$hw = python .\scripts\hw_detect.py | ConvertFrom-Json
Write-Host ("→ {0}, {1} GB RAM, GPU={2} ({3} GB VRAM)" -f $hw.os,$hw.ram_gb,$hw.gpu_name,$hw.vram_gb)

# Set runtime optimization vars
if ($hw.gpu) { 
    $env:ASTRA_MODE="GPU" 
    $env:ASTRA_BATCH="8" 
    Write-Host "⚡ GPU mode enabled with batch size 8"
} else { 
    $env:ASTRA_MODE="CPU" 
    $env:ASTRA_BATCH="2" 
    Write-Host "💻 CPU mode enabled with batch size 2"
}

# 5️⃣  Launch core API
Write-Host "🚀 Starting ASTRA Core API..."
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "astra.api.app:app --host 0.0.0.0 --port 8080"

# 6️⃣  Start watchdog
Write-Host "🛡️  Starting self-healing watchdog..."
Start-Job -ScriptBlock { python .\scripts\selfheal.py }

# 7️⃣  Health check loop
Write-Host "🧩 Verifying startup..."
for ($i=0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/system/health" -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { 
            Write-Host "✅ ASTRA Core is online." -ForegroundColor Green
            break 
        }
    } catch { }
    if ($i -eq 9) { 
        Write-Host "⚠️ ASTRA failed to start properly." -ForegroundColor Red
        exit 1
    }
}

Write-Host "✨ Ready for further development — GPT-OSS core active." -ForegroundColor Cyan
Write-Host "🔄 Watchdog is monitoring API health in the background." -ForegroundColor Yellow
Write-Host "🔗 API available at http://127.0.0.1:8080" -ForegroundColor Blue