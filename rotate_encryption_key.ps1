# rotate_encryption_key.ps1
# Generates a new Fernet key and updates .env safely

[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ROOT) { $ROOT = (Get-Location).Path }
$PY = Join-Path $ROOT ".venv\Scripts\python.exe"
$ENVFILE = Join-Path $ROOT ".env"

Write-Host "==> Generating new Fernet encryption key..." -ForegroundColor Cyan

# Generate new key
$newKey = & $PY -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if ($LASTEXITCODE -ne 0) { throw "Failed to generate encryption key" }

Write-Host "    New key: $newKey" -ForegroundColor Yellow

# Update .env
if (-not (Test-Path $ENVFILE)) { 
    Write-Warning ".env file not found, creating new one"
    New-Item -ItemType File -Path $ENVFILE | Out-Null 
}

$content = (Get-Content $ENVFILE -Raw -ErrorAction SilentlyContinue) -as [string]
if ($content -match "(?m)^\s*ASTRA_ENCRYPTION_KEY\s*=") {
    $content = [regex]::Replace($content, "(?m)^\s*ASTRA_ENCRYPTION_KEY\s*=.*$", "ASTRA_ENCRYPTION_KEY=$newKey")
    Write-Host "==> Updated existing ASTRA_ENCRYPTION_KEY in .env" -ForegroundColor Green
} else {
    if ($content -and -not $content.EndsWith("`r`n")) { $content += "`r`n" }
    $content += "ASTRA_ENCRYPTION_KEY=$newKey`r`n"
    Write-Host "==> Added ASTRA_ENCRYPTION_KEY to .env" -ForegroundColor Green
}

Set-Content -Path $ENVFILE -Value $content -Encoding UTF8

Write-Host "`n✅ Encryption key rotated successfully." -ForegroundColor Green
Write-Host "⚠  Old key in logs is now invalid." -ForegroundColor Yellow
Write-Host "`nRestart your backend to pick up the new key." -ForegroundColor Cyan
