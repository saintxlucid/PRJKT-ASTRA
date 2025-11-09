# ===================================================================
#  ASTRA v1.0.0 - QUICK API KEY FIX (Idempotent)
# ===================================================================
#
#  Run this once to fix the API key placeholder in .env
#  Safe to run multiple times - will not duplicate keys
#
#  Usage from repo root:
#    powershell -ExecutionPolicy Bypass -File .\scripts\fix_api_key.ps1
#
# ===================================================================

$ErrorActionPreference = "Stop"

Write-Host "`n[*] Fixing ASTRA_API_KEYS in .env..." -ForegroundColor Cyan

# Ensure we're in repo root
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$envPath = ".\.env"

# Create .env if it doesn't exist
if (!(Test-Path $envPath)) {
    Write-Host "  [!] .env not found, creating..." -ForegroundColor Yellow
    New-Item -ItemType File -Path $envPath | Out-Null
}

# Generate secure API key using Python
Write-Host "  [+] Generating secure API key..." -ForegroundColor White
$apiKey = $(python -c "import secrets; print(secrets.token_urlsafe(32))").Trim()

if (!$apiKey -or $apiKey.Length -lt 20) {
    Write-Host "  [X] Failed to generate API key" -ForegroundColor Red
    Write-Host "     Ensure Python is available in PATH" -ForegroundColor Yellow
    exit 1
}

# Read current content
$content = Get-Content $envPath

# Replace existing ASTRA_API_KEYS line or append if missing
$replaced = $false
$content = $content | ForEach-Object {
    if ($_ -match '^\s*ASTRA_API_KEYS\s*=') {
        $replaced = $true
        # Check if it's a placeholder
        if ($_ -match 'placeholder|your-generated|example|changeme') {
            Write-Host "  [!] Placeholder detected, replacing..." -ForegroundColor Yellow
        } else {
            Write-Host "  [i] Existing key found, replacing..." -ForegroundColor Gray
        }
        "ASTRA_API_KEYS=$apiKey"
    } else {
        $_
    }
}

# Append if no existing key was found
if (-not $replaced) {
    Write-Host "  [+] Adding ASTRA_API_KEYS to .env..." -ForegroundColor White
    $content += "ASTRA_API_KEYS=$apiKey"
}

# Write back to file
Set-Content $envPath $content

Write-Host "`n[OK] API key configured successfully!" -ForegroundColor Green
Write-Host "     Key: $($apiKey.Substring(0, 12))...***" -ForegroundColor Gray
Write-Host "     Location: $envPath" -ForegroundColor Gray

Write-Host "`n[=>] Next step: Update ship.ps1 paths (lines 13-14)" -ForegroundColor Cyan
Write-Host "     notepad .\scripts\ship.ps1" -ForegroundColor White
Write-Host ""
