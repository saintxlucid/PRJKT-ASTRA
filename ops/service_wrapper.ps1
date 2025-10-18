# ═══════════════════════════════════════════════════════════════
#  ASTRA Service Wrapper for NSSM / Task Scheduler
# ═══════════════════════════════════════════════════════════════
#
#  Wraps ASTRA for running as a Windows service or scheduled task.
#  Handles graceful shutdown, logging, and auto-restart.
#
#  Setup with NSSM (Non-Sucking Service Manager):
#    1. Download NSSM: https://nssm.cc/download
#    2. Install service:
#       nssm install ASTRA "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" ^
#         "-ExecutionPolicy Bypass -NoProfile -File X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\ops\service_wrapper.ps1"
#    3. Configure service:
#       nssm set ASTRA AppDirectory "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
#       nssm set ASTRA DisplayName "ASTRA Core v1.0"
#       nssm set ASTRA Description "ASTRA AI Core Services (LLM + API)"
#       nssm set ASTRA Start SERVICE_AUTO_START
#       nssm set ASTRA AppStdout "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\logs\service.log"
#       nssm set ASTRA AppStderr "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\logs\service_error.log"
#       nssm set ASTRA AppRotateFiles 1
#       nssm set ASTRA AppRotateBytes 10485760  # 10MB
#    4. Start service:
#       nssm start ASTRA
#
#  Setup with Task Scheduler:
#    1. Open Task Scheduler
#    2. Create Task -> General:
#       - Name: "ASTRA Core Service"
#       - Run whether user is logged on or not
#       - Run with highest privileges
#    3. Triggers:
#       - At system startup
#    4. Actions:
#       - Program: powershell.exe
#       - Arguments: -ExecutionPolicy Bypass -NoProfile -File "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\ops\service_wrapper.ps1"
#       - Start in: X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)
#    5. Conditions:
#       - Uncheck "Start only if on AC power"
#    6. Settings:
#       - If task fails, restart every 1 minute, up to 3 times
#
# ═══════════════════════════════════════════════════════════════

param(
    [string]$RepoRoot = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
)

$ErrorActionPreference = "Continue"
Set-Location $RepoRoot

$LogDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$ServiceLog = Join-Path $LogDir "service_$(Get-Date -Format yyyyMMdd).log"

function Write-ServiceLog {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogLine = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $ServiceLog -Value $LogLine
    Write-Host $LogLine
}

function Stop-AstraServices {
    Write-ServiceLog "Stopping ASTRA services..." "INFO"
    
    try {
        & "$RepoRoot\scripts\stop.ps1" 2>&1 | ForEach-Object { Write-ServiceLog $_ "INFO" }
        Write-ServiceLog "Services stopped successfully" "INFO"
    } catch {
        Write-ServiceLog "Error stopping services: $($_.Exception.Message)" "ERROR"
    }
}

# Register shutdown handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-AstraServices
}

# Trap Ctrl+C
$null = [Console]::TreatControlCAsInput = $false
$null = [Console]::CancelKeyPress.Add({
    param($sender, $e)
    $e.Cancel = $true
    Stop-AstraServices
    exit 0
})

# ═══════════════════════════════════════════════════════════════
# MAIN SERVICE LOOP
# ═══════════════════════════════════════════════════════════════

Write-ServiceLog "═══════════════════════════════════════════════════════════════" "INFO"
Write-ServiceLog "ASTRA Service Wrapper Starting" "INFO"
Write-ServiceLog "Repository: $RepoRoot" "INFO"
Write-ServiceLog "═══════════════════════════════════════════════════════════════" "INFO"

try {
    # Verify prerequisites
    if (!(Test-Path "$RepoRoot\scripts\ship.ps1")) {
        throw "ship.ps1 not found at $RepoRoot\scripts\ship.ps1"
    }
    
    if (!(Test-Path "$RepoRoot\.env")) {
        throw ".env file not found at $RepoRoot\.env"
    }
    
    Write-ServiceLog "Prerequisites verified" "INFO"
    
    # Launch ASTRA
    Write-ServiceLog "Launching ASTRA deployment..." "INFO"
    
    $shipProcess = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-ExecutionPolicy Bypass -NoProfile -File `"$RepoRoot\scripts\ship.ps1`"" `
        -WorkingDirectory $RepoRoot `
        -PassThru `
        -NoNewWindow
    
    Write-ServiceLog "ASTRA launched (PID: $($shipProcess.Id))" "INFO"
    
    # Monitor process
    while (!$shipProcess.HasExited) {
        Start-Sleep -Seconds 30
        
        # Periodic health check (optional)
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/system/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            Write-ServiceLog "Health check OK" "DEBUG"
        } catch {
            Write-ServiceLog "Health check failed: $($_.Exception.Message)" "WARN"
        }
    }
    
    $exitCode = $shipProcess.ExitCode
    Write-ServiceLog "ASTRA process exited with code $exitCode" "WARN"
    
    if ($exitCode -ne 0) {
        Write-ServiceLog "Non-zero exit code detected, service will restart" "ERROR"
        exit $exitCode
    }
    
} catch {
    Write-ServiceLog "Fatal error: $($_.Exception.Message)" "ERROR"
    Write-ServiceLog "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    Stop-AstraServices
    exit 1
} finally {
    Write-ServiceLog "Service wrapper shutting down" "INFO"
    Stop-AstraServices
}

Write-ServiceLog "═══════════════════════════════════════════════════════════════" "INFO"
Write-ServiceLog "ASTRA Service Wrapper Stopped" "INFO"
Write-ServiceLog "═══════════════════════════════════════════════════════════════" "INFO"

exit 0
