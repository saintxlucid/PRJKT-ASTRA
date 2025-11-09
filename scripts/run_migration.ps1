# Run Migration Script
# This script automates the migration process with validation and rollback capabilities

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false,
    [string]$BackupPath
)

# Configuration
$ErrorActionPreference = "Stop"
$ASTRA_ROOT = "x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$BACKUP_DIR = if ($BackupPath) { $BackupPath } else { Join-Path $ASTRA_ROOT "data\backup" }
$LOG_FILE = Join-Path $ASTRA_ROOT "data\logs\migration.log"

# Ensure log directory exists
$logDir = Split-Path $LOG_FILE -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force
}

function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Tee-Object -FilePath $LOG_FILE -Append
}

function Backup-Database {
    Write-Log "Creating database backup..."
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = Join-Path $BACKUP_DIR "astra_backup_$timestamp.db"
    
    # Ensure backup directory exists
    if (-not (Test-Path $BACKUP_DIR)) {
        New-Item -ItemType Directory -Path $BACKUP_DIR -Force
    }
    
    try {
        Copy-Item -Path (Join-Path $ASTRA_ROOT "data\astra.db") -Destination $backupFile
        Write-Log "Backup created successfully: $backupFile"
        return $backupFile
    }
    catch {
        Write-Log "ERROR: Failed to create backup: $_"
        throw
    }
}

function Test-Migration {
    Write-Log "Running migration tests..."
    
    try {
        # Activate virtual environment if it exists
        $venvPath = Join-Path $ASTRA_ROOT "venv\Scripts\Activate.ps1"
        if (Test-Path $venvPath) {
            . $venvPath
        }
        
        # Run pytest
        $testResult = pytest tests/test_migration.py -v
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Migration tests passed successfully"
            return $true
        }
        else {
            Write-Log "ERROR: Migration tests failed"
            return $false
        }
    }
    catch {
        Write-Log "ERROR: Failed to run migration tests: $_"
        return $false
    }
}

function Invoke-Migration {
    param($BackupFile)
    
    Write-Log "Starting migration process..."
    try {
        # Activate virtual environment if it exists
        $venvPath = Join-Path $ASTRA_ROOT "venv\Scripts\Activate.ps1"
        if (Test-Path $venvPath) {
            . $venvPath
        }
        
        # Run migration script
        python src/astra/service/migration.py
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Migration completed successfully"
            return $true
        }
        else {
            Write-Log "ERROR: Migration failed"
            return $false
        }
    }
    catch {
        Write-Log "ERROR: Migration process failed: $_"
        return $false
    }
}

function Restore-Backup {
    param($BackupFile)
    
    Write-Log "Restoring from backup: $BackupFile"
    try {
        Stop-Service AstraService -ErrorAction SilentlyContinue
        Copy-Item -Path $BackupFile -Destination (Join-Path $ASTRA_ROOT "data\astra.db") -Force
        Write-Log "Backup restored successfully"
        return $true
    }
    catch {
        Write-Log "ERROR: Failed to restore backup: $_"
        return $false
    }
    finally {
        Start-Service AstraService -ErrorAction SilentlyContinue
    }
}

# Main migration process
try {
    Write-Log "=== Starting Migration Process ==="
    
    # Check if migration is already in progress
    $lockFile = Join-Path $ASTRA_ROOT "data\migration.lock"
    if (Test-Path $lockFile) {
        if (-not $Force) {
            throw "Migration appears to be in progress. Use -Force to override."
        }
        Remove-Item $lockFile -Force
    }
    
    # Create lock file
    New-Item -ItemType File -Path $lockFile -Force
    
    # Create backup
    $backupFile = Backup-Database
    Write-Log "Using backup file: $backupFile"
    
    # Run tests first
    if (-not (Test-Migration)) {
        throw "Migration tests failed. Aborting."
    }
    
    if ($DryRun) {
        Write-Log "Dry run completed successfully"
    }
    else {
        # Perform migration
        if (Invoke-Migration -BackupFile $backupFile) {
            Write-Log "Migration completed successfully"
        }
        else {
            throw "Migration failed. Rolling back..."
        }
    }
}
catch {
    Write-Log "ERROR: Migration failed: $_"
    if (-not $DryRun -and $backupFile) {
        Write-Log "Attempting to restore from backup..."
        if (Restore-Backup -BackupFile $backupFile) {
            Write-Log "System restored to previous state"
        }
        else {
            Write-Log "CRITICAL: Restore failed. Manual intervention required!"
        }
    }
    exit 1
}
finally {
    # Remove lock file
    if (Test-Path $lockFile) {
        Remove-Item $lockFile -Force
    }
    Write-Log "=== Migration Process Completed ==="
}