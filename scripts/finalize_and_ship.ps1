# ═══════════════════════════════════════════════════════════════
#  ASTRA v1.0.0 - ONE-SHOT FINALIZER AND DEPLOYMENT
# ═══════════════════════════════════════════════════════════════
#
#  Production-grade deployment with strict preflight checks.
#  Supports dry-run mode for safe rehearsal.
#
#  Usage:
#    # Normal deployment
#    powershell -ExecutionPolicy Bypass -File .\scripts\finalize_and_ship.ps1
#
#    # Dry-run (preflight checks only, no changes)
#    powershell -ExecutionPolicy Bypass -File .\scripts\finalize_and_ship.ps1 -DryRun
#
# ═══════════════════════════════════════════════════════════════

[CmdletBinding()]
param(
    [Parameter(HelpMessage="Run preflight checks only, make no changes")]
    [switch]$DryRun,
    
    [Parameter(HelpMessage="Path to .env file")]
    [string]$EnvPath = ".\.env",
    
    [Parameter(HelpMessage="Repository root directory")]
    [string]$RepoRoot = $null,
    
    [Parameter(HelpMessage="Skip model checksum verification")]
    [switch]$SkipChecksumVerify
)

$ErrorActionPreference = "Stop"

# Determine repo root
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

Set-Location $RepoRoot

# Setup logging
$LogDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "finalize_$(Get-Date -Format yyyyMMdd_HHmmss).log"
$ShipLogFile = Join-Path $LogDir "ship_$(Get-Date -Format yyyyMMdd_HHmmss).log"

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$Timestamp] $Message"
    Add-Content -Path $LogFile -Value $LogLine
    if ($Color -ne "White") {
        Write-Host $Message -ForegroundColor $Color
    } else {
        Write-Host $Message
    }
}

# Header
$ModeText = if ($DryRun) { "DRY-RUN MODE" } else { "LIVE DEPLOYMENT" }
Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         ASTRA v1.0.0 - FINALIZER & DEPLOYMENT                 ║" -ForegroundColor Cyan
Write-Host "║         $ModeText" -PadRight 62 -ForegroundColor $(if ($DryRun) { "Yellow" } else { "Green" })
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Log "Starting finalizer (DryRun=$DryRun)" "Cyan"
Write-Log "Log file: $LogFile" "Gray"

# ═══════════════════════════════════════════════════════════════
# STEP 0: PREFLIGHT CHECKS (STRICT)
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[0/6] Running preflight checks..." "Cyan"

# Helper functions for checks
function Assert-Tool {
    param([string]$Name, [scriptblock]$Check)
    try {
        $result = & $Check
        if (-not $result) {
            throw "Check failed"
        }
        Write-Log "  ✅ $Name" "Green"
        return $true
    } catch {
        Write-Log "  ❌ $Name - $($_.Exception.Message)" "Red"
        throw "Missing or misconfigured: $Name"
    }
}

function Test-PythonEnvironment {
    try {
        $pythonCheck = python -c @"
import sys
assert sys.version_info >= (3, 10), f'Python 3.10+ required, got {sys.version}'
try:
    import uvicorn
    import fastapi
    print('OK')
except ImportError as e:
    raise AssertionError(f'Missing dependency: {e}')
"@ 2>&1
        return $pythonCheck -match "OK"
    } catch {
        return $false
    }
}

function Test-PortFree {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -eq $connections
}

# Parse ship.ps1 configuration
Write-Log "  🔍 Parsing ship.ps1 configuration..." "White"
$ShipScript = Join-Path $RepoRoot "scripts\ship.ps1"
if (!(Test-Path $ShipScript)) {
    throw "ship.ps1 not found at: $ShipScript"
}

$ShipContent = Get-Content $ShipScript -Raw

# Extract configuration (with fallbacks)
$LlamaExeMatch = [regex]::Match($ShipContent, '\$LlamaExe\s*=\s*"([^"]+)"')
$ModelPathMatch = [regex]::Match($ShipContent, '\$ModelPath\s*=\s*"([^"]+)"')
$ApiPortMatch = [regex]::Match($ShipContent, '\$ApiPort\s*=\s*(\d+)')
$LlmPortMatch = [regex]::Match($ShipContent, '\$LlmPort\s*=\s*(\d+)')
$HostBindMatch = [regex]::Match($ShipContent, '\$HostBind\s*=\s*"([^"]+)"')

if (-not $LlamaExeMatch.Success) {
    throw "Could not parse `$LlamaExe from ship.ps1"
}
if (-not $ModelPathMatch.Success) {
    throw "Could not parse `$ModelPath from ship.ps1"
}

$LlamaExe = $LlamaExeMatch.Groups[1].Value
$ModelPath = $ModelPathMatch.Groups[1].Value
$ApiPort = if ($ApiPortMatch.Success) { [int]$ApiPortMatch.Groups[1].Value } else { 8080 }
$LlmPort = if ($LlmPortMatch.Success) { [int]$LlmPortMatch.Groups[1].Value } else { 8001 }
$HostBind = if ($HostBindMatch.Success) { $HostBindMatch.Groups[1].Value } else { "127.0.0.1" }

Write-Log "  📋 Configuration:" "Gray"
Write-Log "     LLM Exe:    $LlamaExe" "Gray"
Write-Log "     Model:      $ModelPath" "Gray"
Write-Log "     LLM Port:   $LlmPort" "Gray"
Write-Log "     API Port:   $ApiPort" "Gray"
Write-Log "     Bind:       $HostBind" "Gray"

# Run preflight checks
Write-Log "`n  🔧 Checking dependencies..." "White"

Assert-Tool "Python 3.10+ with uvicorn/fastapi" { Test-PythonEnvironment }
Assert-Tool "llama-server.exe exists" { Test-Path $LlamaExe }
Assert-Tool "Model GGUF exists" { Test-Path $ModelPath }
Assert-Tool "LLM port $LlmPort available" { Test-PortFree $LlmPort }
Assert-Tool "API port $ApiPort available" { Test-PortFree $ApiPort }

# Check for placeholder paths
if ($LlamaExe -like "*C:\llama\*" -or $LlamaExe -like "*changeme*") {
    Write-Log "  ⚠️  WARNING: LlamaExe path looks like placeholder" "Yellow"
}
if ($ModelPath -like "*C:\models\*" -or $ModelPath -like "*changeme*") {
    Write-Log "  ⚠️  WARNING: ModelPath looks like placeholder" "Yellow"
}

# Verify model checksum if checksums.txt exists
if (-not $SkipChecksumVerify) {
    $ChecksumFile = Join-Path $RepoRoot "models\checksums.txt"
    if (Test-Path $ChecksumFile) {
        Write-Log "  🔐 Verifying model integrity..." "White"
        $ModelName = Split-Path -Leaf $ModelPath
        $ChecksumLines = Get-Content $ChecksumFile
        $ExpectedLine = $ChecksumLines | Where-Object { $_ -match [regex]::Escape($ModelName) }
        
        if ($ExpectedLine) {
            $ExpectedHash = ($ExpectedLine -split '\s+')[0]
            $ActualHash = (Get-FileHash -Path $ModelPath -Algorithm SHA256).Hash
            
            if ($ActualHash -eq $ExpectedHash) {
                Write-Log "  ✅ Model checksum verified" "Green"
            } else {
                Write-Log "  ❌ Model checksum mismatch!" "Red"
                Write-Log "     Expected: $ExpectedHash" "Red"
                Write-Log "     Actual:   $ActualHash" "Red"
                throw "Model integrity check failed. Re-download the model or use -SkipChecksumVerify"
            }
        } else {
            Write-Log "  ℹ️  No checksum entry for $ModelName" "Gray"
        }
    }
}

# Check security binding
if ($HostBind -ne "127.0.0.1" -and $HostBind -ne "localhost") {
    Write-Log "  ⚠️  WARNING: Binding to $HostBind (exposed to network)" "Yellow"
    Write-Log "     Consider using 127.0.0.1 for localhost-only access" "Yellow"
}

Write-Log "`n  ✅ All preflight checks passed!" "Green"

if ($DryRun) {
    Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ✅ DRY-RUN COMPLETE - CHECKS PASSED               ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green
    Write-Log "Dry-run complete. No changes made." "Cyan"
    Write-Log "Ready for live deployment: Remove -DryRun flag" "Green"
    exit 0
}

# ═══════════════════════════════════════════════════════════════
# STEP 1: ENSURE .env EXISTS AND SET REAL API KEY
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[1/6] Configuring .env file..." "Cyan"

$envPath = if ([System.IO.Path]::IsPathRooted($EnvPath)) { $EnvPath } else { Join-Path $RepoRoot $EnvPath }

if (!(Test-Path $envPath)) {
    Write-Log "  ⚠️  .env not found, creating..." "Yellow"
    New-Item -ItemType File -Path $envPath | Out-Null
}

# Generate cryptographically secure API key (PowerShell/.NET)
Write-Log "  🔐 Generating secure API key..." "White"
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$apiKey = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')

# Read .env and update or append ASTRA_API_KEYS
$envLines = Get-Content $envPath -Raw
$hasKey = $false

if ($envLines -match '(?m)^ASTRA_API_KEYS=.*$') {
    $hasKey = $true
    # Check if it's a placeholder
    if ($envLines -match 'ASTRA_API_KEYS=your-generated-api-key') {
        Write-Host "  ⚠️  Placeholder API key detected, replacing..." -ForegroundColor Yellow
    }
    $envLines = $envLines -replace '(?m)^ASTRA_API_KEYS=.*$', "ASTRA_API_KEYS=$apiKey"
} else {
    Write-Host "  ➕ Adding ASTRA_API_KEYS to .env..." -ForegroundColor White
    $envLines += "`nASTRA_API_KEYS=$apiKey"
}

# Write back to file
$envLines | Set-Content -Path $envPath -NoNewline
Add-Content -Path $envPath -Value "`n"  # Ensure trailing newline

# Secure .env file permissions (Windows)
try {
    Write-Log "  🔒 Securing .env file permissions..." "White"
    icacls $envPath /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
    Write-Log "  ✅ .env permissions set to user-only" "Green"
} catch {
    Write-Log "  ⚠️  Could not set .env permissions (non-fatal)" "Yellow"
}

Write-Log "  ✅ API key configured" "Green"
Write-Log "     Key: $($apiKey.Substring(0, 8))...***" "Gray"

# ═══════════════════════════════════════════════════════════════
# STEP 2: INITIALIZE GIT REPOSITORY IF NEEDED
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[2/6] Checking git repository..." "Cyan"

if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-Log "  ⚠️  Git repository not initialized" "Yellow"
    Write-Log "  🔄 Initializing git repository..." "White"
    
    git init 2>&1 | Tee-Object -Variable gitOutput | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  ❌ Git init failed: $gitOutput" "Red"
        exit 1
    }
    
    Write-Log "  📝 Creating initial commit..." "White"
    git add . 2>&1 | Out-Null
    git commit -m "ASTRA Core v1.0.0 - Initial production release" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "  ⚠️  Initial commit failed (non-fatal)" "Yellow"
    } else {
        Write-Log "  ✅ Git repository initialized" "Green"
    }
} else {
    Write-Log "  ✅ Git repository exists" "Green"
    
    # Check for uncommitted changes
    $status = git status --porcelain 2>&1
    if ($status) {
        Write-Log "  ℹ️  Uncommitted changes detected" "Gray"
    }
}

# ═══════════════════════════════════════════════════════════════
# STEP 3: CREATE BACKUP
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[3/6] Creating pre-deployment backup..." "Cyan"

$backupDir = Join-Path $RepoRoot "backup"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupDir "astra_pre_v1_$timestamp.zip"

try {
    # Backup .env and data directory
    $itemsToBackup = @()
    if (Test-Path $envPath) { $itemsToBackup += $envPath }
    if (Test-Path (Join-Path $RepoRoot "data")) { $itemsToBackup += (Join-Path $RepoRoot "data") }
    
    if ($itemsToBackup.Count -gt 0) {
        Compress-Archive -Path $itemsToBackup -DestinationPath $backupPath -Force
        $backupSize = (Get-Item $backupPath).Length / 1MB
        Write-Log "  ✅ Backup created: $([System.IO.Path]::GetFileName($backupPath))" "Green"
        Write-Log "     Size: $($backupSize.ToString('F2')) MB" "Gray"
    } else {
        Write-Log "  ⚠️  No data to backup (first deployment?)" "Yellow"
    }
} catch {
    Write-Log "  ⚠️  Backup failed (non-fatal): $($_.Exception.Message)" "Yellow"
}

# ═══════════════════════════════════════════════════════════════
# STEP 4: FINAL PRE-LAUNCH VERIFICATION
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[4/6] Final pre-launch verification..." "Cyan"

# Double-check critical files exist
$criticalFiles = @(
    "scripts\ship.ps1",
    "scripts\smoke_test.ps1",
    "src\astra\api\app.py"
)

foreach ($file in $criticalFiles) {
    $fullPath = Join-Path $RepoRoot $file
    if (!(Test-Path $fullPath)) {
        Write-Log "  ❌ Critical file missing: $file" "Red"
        exit 1
    }
}
Write-Log "  ✅ All critical files present" "Green"

# Verify .gitignore protects .env
$gitignorePath = Join-Path $RepoRoot ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw
    if ($gitignoreContent -match '\.env') {
        Write-Log "  ✅ .gitignore protects .env" "Green"
    } else {
        Write-Log "  ⚠️  WARNING: .env not in .gitignore" "Yellow"
    }
}

Write-Log "  ✅ Pre-launch verification complete" "Green"

# ═══════════════════════════════════════════════════════════════
# STEP 5: LAUNCH DEPLOYMENT
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[5/6] Launching ASTRA deployment..." "Cyan"
Write-Log "  📡 Starting LLM + API + Smoke Tests..." "White"
Write-Log "  📝 Logging to: $ShipLogFile" "Gray"
Write-Host ""

# Call ship.ps1 with output logging
$shipScript = Join-Path $RepoRoot "scripts\ship.ps1"
& powershell -ExecutionPolicy Bypass -File $shipScript 2>&1 | Tee-Object -FilePath $ShipLogFile

$shipExitCode = $LASTEXITCODE

Write-Host ""
Write-Log "Ship exit code: $shipExitCode" "Gray"

# ═══════════════════════════════════════════════════════════════
# STEP 6: POST-DEPLOYMENT VERIFICATION
# ═══════════════════════════════════════════════════════════════

Write-Log "`n[6/6] Post-deployment verification..." "Cyan"

if ($shipExitCode -eq 0) {
    # Quick health check
    Start-Sleep -Seconds 2
    try {
        Invoke-WebRequest -Uri "http://$($HostBind):$ApiPort/v1/system/health" -UseBasicParsing -TimeoutSec 5 | Out-Null
        Write-Log "  ✅ API health check passed" "Green"
    } catch {
        Write-Log "  ⚠️  API health check failed (may need more time to start)" "Yellow"
    }
    
    Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                    ✅ DEPLOYMENT SUCCESSFUL                    ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green
    
    Write-Log "🎉 ASTRA v1.0.0 is now running!" "Green"
    Write-Host ""
    Write-Host "📋 NEXT STEPS:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1️⃣  VERIFY SERVICES:" -ForegroundColor White
    Write-Host "   Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null" -ForegroundColor Gray
    Write-Host "   Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null" -ForegroundColor Gray
    Write-Host "   Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2️⃣  TAG RELEASE:" -ForegroundColor White
    Write-Host '   git tag -a v1.0.0 -m "ASTRA Core v1.0.0 - Production Ready"' -ForegroundColor Gray
    Write-Host "   git push origin v1.0.0  # if remote configured" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3️⃣  MONITOR (30 minutes):" -ForegroundColor White
    Write-Host "   .\scripts\monitor_golden_signals.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "📊 ENDPOINTS:" -ForegroundColor Cyan
    Write-Host "   LLM:     http://127.0.0.1:8001" -ForegroundColor Gray
    Write-Host "   API:     http://127.0.0.1:8080" -ForegroundColor Gray
    Write-Host "   Health:  http://127.0.0.1:8080/v1/system/health" -ForegroundColor Gray
    Write-Host "   Bridge:  http://127.0.0.1:8080/v1/bridge/healthz" -ForegroundColor Gray
    Write-Host "   Metrics: http://127.0.0.1:8080/metrics" -ForegroundColor Gray
    Write-Host ""
    Write-Host "🔐 YOUR API KEY:" -ForegroundColor Cyan
    Write-Host "   $apiKey" -ForegroundColor Yellow
    Write-Host "   (Saved in .env file)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Log "Deployment completed successfully" "Green"
    exit 0
    
} else {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║                    ❌ DEPLOYMENT FAILED                        ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔍 TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Check ship.ps1 paths (lines 13-14):" -ForegroundColor White
    Write-Host "   notepad scripts\ship.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Verify llama-server.exe exists:" -ForegroundColor White
    Write-Host "   Test-Path `"C:\llama\llama-server.exe`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Verify model file exists:" -ForegroundColor White
    Write-Host "   Test-Path `"C:\models\gpt-oss-20b-q4_k_m.gguf`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Check ports not in use:" -ForegroundColor White
    Write-Host "   netstat -ano | findstr `":8001 :8080`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. Review deployment logs above for errors" -ForegroundColor White
    Write-Host ""
    Write-Host "📄 See: DEPLOY_CARD.md for detailed troubleshooting" -ForegroundColor Cyan
    Write-Host "📝 Logs: $ShipLogFile" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Log "Deployment failed with exit code $shipExitCode" "Red"
    Write-Log "Review logs for details: $ShipLogFile" "Yellow"
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan
Write-Log "Finalizer complete" "Cyan"
