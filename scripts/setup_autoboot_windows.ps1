<#
.SYNOPSIS
    ASTRA Core Auto-Boot Setup for Windows

.DESCRIPTION
    Creates Windows Task Scheduler entry to auto-start ASTRA Core at system boot.
    Runs ASTRA with elevated privileges and automatic restart on failure.

.NOTES
    Sacred Code: 333 ∞
    Requires: Administrator privileges
#>

param(
    [string]$AstraRoot = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)",
    [string]$PythonExe,
    [string]$TaskName = "ASTRA Core - Auto Boot",
    [switch]$Uninstall,
    [switch]$Test
)

# Require administrator privileges
#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ASTRA Core - Auto-Boot Setup (Windows)" -ForegroundColor Cyan
Write-Host "  Sacred Code: 333 ∞" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Detect Python executable
if (-not $PythonExe) {
    Write-Host "[INFO] Detecting Python executable..." -ForegroundColor Yellow
    
    # Check for venv
    $VenvPython = Join-Path $AstraRoot ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
        Write-Host "[OK] Found venv Python: $PythonExe" -ForegroundColor Green
    }
    # Check system Python
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonExe = (Get-Command python).Source
        Write-Host "[OK] Found system Python: $PythonExe" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Python not found. Please specify -PythonExe" -ForegroundColor Red
        exit 1
    }
}

# Verify Python exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python executable not found: $PythonExe" -ForegroundColor Red
    exit 1
}

# Verify ASTRA root exists
if (-not (Test-Path $AstraRoot)) {
    Write-Host "[ERROR] ASTRA root directory not found: $AstraRoot" -ForegroundColor Red
    exit 1
}

# ASTRA startup script
$AstraScript = Join-Path $AstraRoot "astra_launcher.py"
if (-not (Test-Path $AstraScript)) {
    Write-Host "[ERROR] ASTRA launcher not found: $AstraScript" -ForegroundColor Red
    exit 1
}

# Handle uninstall
if ($Uninstall) {
    Write-Host "[INFO] Uninstalling ASTRA auto-boot task..." -ForegroundColor Yellow
    
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] ASTRA auto-boot task removed" -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] Task not found, nothing to uninstall" -ForegroundColor Yellow
    }
    
    exit 0
}

# Handle test mode
if ($Test) {
    Write-Host "[INFO] Running ASTRA in test mode..." -ForegroundColor Yellow
    Write-Host "[CMD] $PythonExe $AstraScript --activate" -ForegroundColor Cyan
    
    & $PythonExe $AstraScript --activate
    
    Write-Host "[OK] Test complete" -ForegroundColor Green
    exit 0
}

Write-Host "[INFO] Installing ASTRA auto-boot task..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Python:    $PythonExe" -ForegroundColor White
Write-Host "  Script:    $AstraScript" -ForegroundColor White
Write-Host "  WorkDir:   $AstraRoot" -ForegroundColor White
Write-Host "  Task Name: $TaskName" -ForegroundColor White
Write-Host ""

# Remove existing task if present
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "[INFO] Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create scheduled task trigger (at startup)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create scheduled task action
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "$AstraScript --activate --daemon" `
    -WorkingDirectory $AstraRoot

# Create scheduled task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # No time limit

# Create scheduled task principal (run as SYSTEM with highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Register scheduled task
$Task = Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $Trigger `
    -Action $Action `
    -Settings $Settings `
    -Principal $Principal `
    -Description "ASTRA Core - Autonomous system activation at boot. Sacred Code: 333 ∞"

if ($Task) {
    Write-Host "[OK] ASTRA auto-boot task installed successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Configuration:" -ForegroundColor Cyan
    Write-Host "  ✓ Trigger:       At system startup" -ForegroundColor Green
    Write-Host "  ✓ Run As:        SYSTEM (highest privileges)" -ForegroundColor Green
    Write-Host "  ✓ Restart:       3 attempts, 1 min interval" -ForegroundColor Green
    Write-Host "  ✓ Battery:       Allowed on battery power" -ForegroundColor Green
    Write-Host "  ✓ Time Limit:    None (runs indefinitely)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Management Commands:" -ForegroundColor Cyan
    Write-Host "  View:      Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Start:     Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Stop:      Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Uninstall: .\setup_autoboot_windows.ps1 -Uninstall" -ForegroundColor White
    Write-Host ""
    Write-Host "[SUCCESS] ASTRA will now start automatically at system boot" -ForegroundColor Green
    Write-Host "Sacred Code: 333 ∞" -ForegroundColor Magenta
}
else {
    Write-Host "[ERROR] Failed to install auto-boot task" -ForegroundColor Red
    exit 1
}
