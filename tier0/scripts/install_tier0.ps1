# ASTRA Tier-0 Installation Script
# Installs dependencies and downloads Whisper model
# Run as Administrator: powershell -ExecutionPolicy Bypass -File install_tier0.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$Tier0Dir = Split-Path -Parent $ProjectRoot

Write-Host "[ASTRA] Installing Tier-0 dependencies..." -ForegroundColor Cyan

# Check Python
$PythonCmd = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERR] Python not found. Install Python 3.10+ first." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python: $PythonCmd" -ForegroundColor Green

# Create virtual environment if needed
$VenvPath = "$Tier0Dir\.venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvPath
}

# Activate venv
$ActivateScript = "$VenvPath\Scripts\Activate.ps1"
& $ActivateScript

# Upgrade pip
Write-Host "[*] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "[*] Installing Python packages..." -ForegroundColor Yellow
pip install -r "$Tier0Dir\requirements-tier0.txt" --quiet

# Download Whisper model
$ModelDir = "$Tier0Dir\models\whisper-small-int8"
if (-not (Test-Path $ModelDir)) {
    Write-Host "[*] Downloading Whisper small model (int8)..." -ForegroundColor Yellow
    python -c "
from faster_whisper import WhisperModel
print('[ASTRA] Downloading model...')
model = WhisperModel('small', device='cpu', compute_type='int8', model_dir='$ModelDir')
print('[OK] Model downloaded to $ModelDir')
"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERR] Model download failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Whisper model already present" -ForegroundColor Green
}

# Setup environment file
$EnvFile = "$Tier0Dir\.env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[*] Creating .env file..." -ForegroundColor Yellow
    Copy-Item "$Tier0Dir\.env.example" $EnvFile
    Write-Host "[OK] Created .env - edit as needed" -ForegroundColor Green
}

Write-Host "[OK] Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env file: $EnvFile" -ForegroundColor Gray
Write-Host "  2. Run API:   .\run_api.ps1" -ForegroundColor Gray
Write-Host "  3. Run voice: .\run_voice.ps1" -ForegroundColor Gray
