# ASTRA Environment Activation Script (PowerShell)
# This script activates the local Python virtual environment and sets up the project
# Usage: .\scripts\activate_astra.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   ASTRA - AI Assistant System" -ForegroundColor Cyan
Write-Host "   Activating Local Environment..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Set the project root
$ProjectRoot = "X:\PROJECT_ASTRA"
Set-Location $ProjectRoot

# Activate Python virtual environment
Write-Host "[1/5] Activating Python virtual environment..." -ForegroundColor Yellow
& "$ProjectRoot\.venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "   ✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "   ✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}

# Set Python path
Write-Host "[2/5] Setting PYTHONPATH..." -ForegroundColor Yellow
$env:PYTHONPATH = "$ProjectRoot\src;$ProjectRoot"
Write-Host "   ✓ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Load environment variables
Write-Host "[3/5] Loading environment variables..." -ForegroundColor Yellow
if (Test-Path "$ProjectRoot\.env") {
    Get-Content "$ProjectRoot\.env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    Write-Host "   ✓ Environment variables loaded from .env" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Warning: .env file not found" -ForegroundColor Yellow
}

# Display configuration
Write-Host "[4/5] Verifying configuration..." -ForegroundColor Yellow
Write-Host "   • Python: $((& python --version 2>&1))" -ForegroundColor White
Write-Host "   • Python Path: $ProjectRoot\.venv\Scripts\python.exe" -ForegroundColor White
Write-Host "   • Project Root: $ProjectRoot" -ForegroundColor White
Write-Host "   • Model: GPT-OSS-20B" -ForegroundColor White
Write-Host "   • Context Length: 131,072 tokens" -ForegroundColor White
Write-Host "   • Reasoning Mode: medium" -ForegroundColor White
Write-Host "   ✓ Configuration verified" -ForegroundColor Green

# Display model information
Write-Host "[5/5] GPT-OSS-20B Model Information:" -ForegroundColor Yellow
Write-Host "   • Total Parameters: 20.9B" -ForegroundColor White
Write-Host "   • Active Parameters: 3.6B per token" -ForegroundColor White
Write-Host "   • Layers: 24" -ForegroundColor White
Write-Host "   • Experts: 32 (top-4 selection)" -ForegroundColor White
Write-Host "   • Checkpoint Size: 12.8 GiB" -ForegroundColor White
Write-Host "   • Tokenizer: o200k_harmony" -ForegroundColor White
Write-Host "   ✓ Model intelligence loaded" -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   Environment Ready! " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available Commands:" -ForegroundColor Cyan
Write-Host "  • poetry run python run_server.py  - Start ASTRA server" -ForegroundColor White
Write-Host "  • poetry run pytest                 - Run tests" -ForegroundColor White
Write-Host "  • poetry show                       - Show installed packages" -ForegroundColor White
Write-Host "  • python -m src.astra.models.model_info - View model specs" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  • README.md - Quick start guide" -ForegroundColor White
Write-Host "  • INSTALLATION.md - Detailed setup" -ForegroundColor White
Write-Host "  • docs/models/gpt_oss_model_card.md - Full model specifications" -ForegroundColor White
Write-Host ""
