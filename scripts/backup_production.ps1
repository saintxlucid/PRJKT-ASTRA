# ASTRA Production Backup Script
# Creates timestamped ZIP backups of database and vector store
# Retains only the last 7 backups to save disk space

param(
    [string]$ProjectRoot = "X:\PROJECT_ASTRA",
    [string]$BackupRoot = "X:\PROJECT_ASTRA\backups",
    [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  ASTRA Production Backup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Timestamp for this backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $BackupRoot $timestamp
$zipFile = Join-Path $BackupRoot "$timestamp.zip"

# Create backup directory structure
Write-Host "[1/5] Creating backup directory..." -ForegroundColor Yellow
if (-not (Test-Path $BackupRoot)) {
    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    Write-Host "      Created: $BackupRoot" -ForegroundColor Green
}

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Write-Host "      Created: $backupDir" -ForegroundColor Green

# Backup database
Write-Host ""
Write-Host "[2/5] Backing up SQLite database..." -ForegroundColor Yellow
$dbSource = Join-Path $ProjectRoot "data\astra.db"
$dbDest = Join-Path $backupDir "astra.db"

if (Test-Path $dbSource) {
    Copy-Item -Path $dbSource -Destination $dbDest -Force
    $dbSize = (Get-Item $dbSource).Length / 1MB
    Write-Host "      Copied: astra.db ($([math]::Round($dbSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "      Warning: Database not found at $dbSource" -ForegroundColor Red
}

# Backup vector store
Write-Host ""
Write-Host "[3/5] Backing up ChromaDB vector store..." -ForegroundColor Yellow
$chromaSource = Join-Path $ProjectRoot "data\chromadb"
$chromaDest = Join-Path $backupDir "chromadb"

if (Test-Path $chromaSource) {
    Copy-Item -Path $chromaSource -Destination $chromaDest -Recurse -Force
    $chromaSize = (Get-ChildItem $chromaSource -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "      Copied: chromadb\ ($([math]::Round($chromaSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "      Warning: Vector store not found at $chromaSource" -ForegroundColor Red
}

# Create success marker
$markerFile = Join-Path $backupDir "_BACKUP_OK.txt"
$markerContent = @"
ASTRA Production Backup
Timestamp: $timestamp
Database: $(if (Test-Path $dbSource) { "✓" } else { "✗" })
Vector Store: $(if (Test-Path $chromaSource) { "✓" } else { "✗" })
"@
Set-Content -Path $markerFile -Value $markerContent

# Compress to ZIP
Write-Host ""
Write-Host "[4/5] Compressing backup..." -ForegroundColor Yellow

try {
    # Use .NET compression (built-in, no 7-zip needed)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($backupDir, $zipFile, 'Optimal', $false)
    
    $zipSize = (Get-Item $zipFile).Length / 1MB
    Write-Host "      Created: $timestamp.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
    
    # Remove uncompressed directory after successful compression
    Remove-Item -Path $backupDir -Recurse -Force
    Write-Host "      Removed temporary directory" -ForegroundColor Green
} catch {
    Write-Host "      Error compressing: $_" -ForegroundColor Red
    Write-Host "      Backup kept uncompressed at: $backupDir" -ForegroundColor Yellow
}

# Apply retention policy (keep last 7 backups)
Write-Host ""
Write-Host "[5/5] Applying retention policy (keep last $RetentionDays)..." -ForegroundColor Yellow

$backups = Get-ChildItem $BackupRoot -Filter "*.zip" | Sort-Object LastWriteTime -Descending

if ($backups.Count -gt $RetentionDays) {
    $toDelete = $backups | Select-Object -Skip $RetentionDays
    foreach ($old in $toDelete) {
        Remove-Item -Path $old.FullName -Force
        Write-Host "      Deleted: $($old.Name)" -ForegroundColor Gray
    }
    Write-Host "      Retained: $RetentionDays most recent backups" -ForegroundColor Green
} else {
    Write-Host "      Total backups: $($backups.Count) (under retention limit)" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Backup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup location: $zipFile" -ForegroundColor White
Write-Host "Total backups: $($backups.Count)" -ForegroundColor White
Write-Host ""

# Exit with success
exit 0
