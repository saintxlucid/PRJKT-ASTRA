# ASTRA Asset Ingestion Script - Clone Repos & Download Datasets
# Phase 4 Staging Environment Setup
# Date: November 13, 2025

$ErrorActionPreference = "Continue"

# ============================================================================
# CONFIGURATION
# ============================================================================

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$baseDir = Split-Path -Parent (Split-Path -Parent $scriptPath)
$repoDir = Join-Path $baseDir "phase4_staging\repos"
$datasetDir = Join-Path $baseDir "phase4_staging\datasets"
$logDir = Join-Path $baseDir "phase4_staging\logs"
$registry = Join-Path $baseDir "phase4_staging\registry\assets_registry.yml"

# Create directories
@($repoDir, $datasetDir, $logDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
    }
}

# Setup logging
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "ingestion_$timestamp.log"
$logStream = New-Object System.IO.StreamWriter($logFile, $true)

function Log {
    param([string]$message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $message"
    Write-Host $line
    $logStream.WriteLine($line)
    $logStream.Flush()
}

Log "╔════════════════════════════════════════════════════════════════╗"
Log "║        ASTRA PHASE 4 - ASSET INGESTION SCRIPT                 ║"
Log "║            Staging Environment Setup                          ║"
Log "╚════════════════════════════════════════════════════════════════╝"
Log ""
Log "Base Directory: $baseDir"
Log "Repo Directory: $repoDir"
Log "Dataset Directory: $datasetDir"
Log "Log File: $logFile"
Log ""

# ============================================================================
# CLONE REPOSITORIES
# ============================================================================

Log "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting repository cloning..."
Log ""

$repos = @(
    "https://github.com/KalyanKS-NLP/llm-engineer-toolkit.git",
    "https://github.com/neulab/ragged.git",
    "https://github.com/tensorchord/Awesome-LLMOps.git",
    "https://github.com/kaushikb11/awesome-llm-agents.git",
    "https://github.com/tooniez/llm-toolkit.git"
)

$clonedRepos = 0
$failedRepos = 0

foreach ($url in $repos) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($url)
    $dest = Join-Path $repoDir $name
    
    Log "Repository: $name"
    Log "  URL: $url"
    Log "  Destination: $dest"
    
    if (Test-Path $dest) {
        Log "  Status: Already exists, pulling latest..."
        Push-Location $dest
        try {
            git pull 2>&1 | ForEach-Object { Log "  $_" }
            Log "  OK: Pull successful"
            $clonedRepos++
        } catch {
            Log "  WARNING: Pull failed (may be offline or permission issue)"
            $failedRepos++
        }
        Pop-Location
    } else {
        Log "  Status: Cloning..."
        try {
            git clone --depth 1 $url $dest 2>&1 | ForEach-Object { Log "  $_" }
            Log "  OK: Clone successful"
            $clonedRepos++
        } catch {
            Log "  ERROR: Clone failed"
            $failedRepos++
        }
    }
    Log ""
}

Log "Repositories Summary:"
Log "  OK: Cloned/Updated: $clonedRepos"
Log "  ERROR: Failed: $failedRepos"
Log ""

# ============================================================================
# DOWNLOAD DATASETS
# ============================================================================

Log "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting dataset download..."
Log ""

# Call Python script to download datasets
if (Get-Command python -ErrorAction SilentlyContinue) {
    python "$scriptPath\download_datasets.py" 2>&1 | ForEach-Object { Log "$_" }
} else {
    Log "WARNING: Python not found. Skipping dataset download."
    Log "  Install Python and run: python $scriptPath\download_datasets.py"
}

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================

Log ""
Log "╔════════════════════════════════════════════════════════════════╗"
Log "║                 INGESTION SCRIPT COMPLETE                      ║"
Log "╚════════════════════════════════════════════════════════════════╝"
Log ""
Log "Next Steps:"
Log "  1. Review cloned repositories:"
Log "     dir $repoDir"
Log ""
Log "  2. Review downloaded datasets:"
Log "     dir $datasetDir"
Log ""
Log "  3. Run smoke tests on repositories:"
Log "     cd $scriptPath; python test_repo_builds.py"
Log ""
Log "  4. Ingest datasets to vector store:"
Log "     python $scriptPath\ingest_to_vectorstore.py"
Log ""
Log "  5. Run integration tests:"
Log "     python $scriptPath\run_integration_tests.py"
Log ""
Log "  6. Update registry with results:"
Log "     Registry file: $registry"
Log ""
Log "Log file: $logFile"
Log ""

$logStream.Close()
