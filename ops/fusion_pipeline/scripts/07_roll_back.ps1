# =====================================================================
# ASTRA Fusion Pipeline - Step 7: Rollback
# =====================================================================
# Purpose: Restore model from backup if fusion fails
# Sacred Code: 333
# =====================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ModelPath = ""
)

Write-Host "↩️  ASTRA Fusion Pipeline - Rollback Utility" -ForegroundColor Cyan
Write-Host "Sacred Code: 333" -ForegroundColor Yellow
Write-Host ""

# Determine model path
if (-not $ModelPath) {
    if ($env:OUT_DIR) {
        $ModelPath = Join-Path $env:OUT_DIR "astra_core_q4_k_m.gguf"
    } else {
        Write-Host "❌ ERROR: No model path specified and OUT_DIR not set." -ForegroundColor Red
        Write-Host "Usage: .\07_roll_back.ps1 -ModelPath <path_to_gguf>" -ForegroundColor Yellow
        exit 1
    }
}

$BackupPath = "$ModelPath.bak"

# Validate paths
if (-not (Test-Path $BackupPath)) {
    Write-Host "❌ ERROR: No backup found at: $BackupPath" -ForegroundColor Red
    Write-Host "   Cannot rollback without a backup file." -ForegroundColor Yellow
    exit 1
}

Write-Host "📄 Model  : $ModelPath" -ForegroundColor White
Write-Host "📄 Backup : $BackupPath" -ForegroundColor White
Write-Host ""

# Confirm rollback
$confirmation = Read-Host "⚠️  This will restore the model from backup. Continue? (y/N)"

if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "❌ Rollback cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "↩️  Rolling back..." -ForegroundColor Yellow

try {
    # Archive current (corrupted/failed) version
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $failedPath = "$ModelPath.failed_$timestamp"
    
    if (Test-Path $ModelPath) {
        Write-Host "   📦 Archiving failed version to: $failedPath" -ForegroundColor Gray
        Copy-Item $ModelPath $failedPath -Force
    }
    
    # Restore from backup
    Write-Host "   📥 Restoring from backup..." -ForegroundColor Gray
    Copy-Item $BackupPath $ModelPath -Force
    
    Write-Host ""
    Write-Host "✅ Rollback complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Status:" -ForegroundColor Cyan
    Write-Host "  Restored : $ModelPath" -ForegroundColor White
    Write-Host "  Backup   : $BackupPath (preserved)" -ForegroundColor White
    Write-Host "  Failed   : $failedPath (archived)" -ForegroundColor White
    Write-Host ""
    Write-Host "The model has been restored to its pre-fusion state." -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "❌ ERROR during rollback: $_" -ForegroundColor Red
    Write-Host "   Manual intervention may be required." -ForegroundColor Yellow
    exit 1
}
