# Operations Hardening Scripts
# Production reliability validation - Post-deployment automation
# Date: October 9, 2025

## 1. Auto-Start Scheduled Task for llama.cpp

### Create Task
```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument `
  "-WindowStyle Hidden -Command `"cd X:\PROJECT_ASTRA; X:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe --model 'X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf' --host 127.0.0.1 --port 8001 --threads 8 --parallel 1 --n-gpu-layers 0 --ctx-size 4096 --batch-size 128 --ubatch-size 32 --cache-type-k q8_0 --cache-type-v q8_0`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "ASTRA_LlamaCpp_Server" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Start llama.cpp server with GPT-OSS model at logon"
```

## 2. Auto-Start Scheduled Task for ASTRA Backend

### Create Task
```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument `
  "-WindowStyle Hidden -Command `"cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe -m uvicorn astra.api.app:app --host 127.0.0.1 --port 8080 --workers 1 --log-level info`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartInterval (New-TimeSpan -Minutes 1) -RestartCount 3

Register-ScheduledTask -TaskName "ASTRA_Backend_Server" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Start ASTRA backend API server at logon with auto-restart"
```

## 3. Health Watchdog Script

### Create Watchdog Script
```powershell
# Create: X:\PROJECT_ASTRA\scripts\health_watchdog.ps1
$content = @'
# Health Watchdog for ASTRA Backend
# Polls /v1/system/health every minute, restarts if unhealthy

$ErrorActionPreference = "Stop"
$healthUrl = "http://127.0.0.1:8080/v1/system/health"
$logFile = "X:\PROJECT_ASTRA\logs\watchdog.log"
$maxConsecutiveFailures = 3
$consecutiveFailures = 0

function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Tee-Object -FilePath $logFile -Append
}

function Restart-Backend {
    Write-Log "Restarting ASTRA backend..."
    
    # Kill existing process
    Get-Process -Name python -ErrorAction SilentlyContinue | 
        Where-Object { $_.CommandLine -like "*uvicorn*astra.api.app*" } | 
        Stop-Process -Force
    
    Start-Sleep -Seconds 3
    
    # Restart via scheduled task
    Start-ScheduledTask -TaskName "ASTRA_Backend_Server"
    
    Write-Log "Backend restart initiated"
}

Write-Log "Health watchdog started"

while ($true) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 10 -ErrorAction Stop
        
        if ($response.status -eq "healthy") {
            $consecutiveFailures = 0
            Write-Log "Health check: OK"
        } else {
            $consecutiveFailures++
            Write-Log "Health check: UNHEALTHY ($consecutiveFailures/$maxConsecutiveFailures)"
            
            if ($consecutiveFailures -ge $maxConsecutiveFailures) {
                Restart-Backend
                $consecutiveFailures = 0
                Start-Sleep -Seconds 30  # Wait longer after restart
            }
        }
    } catch {
        $consecutiveFailures++
        Write-Log "Health check: FAILED ($consecutiveFailures/$maxConsecutiveFailures) - $($_.Exception.Message)"
        
        if ($consecutiveFailures -ge $maxConsecutiveFailures) {
            Restart-Backend
            $consecutiveFailures = 0
            Start-Sleep -Seconds 30
        }
    }
    
    Start-Sleep -Seconds 60
}
'@

$content | Set-Content "X:\PROJECT_ASTRA\scripts\health_watchdog.ps1" -Encoding UTF8
```

### Create Watchdog Scheduled Task
```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument `
  "-WindowStyle Hidden -File `"X:\PROJECT_ASTRA\scripts\health_watchdog.ps1`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "ASTRA_Health_Watchdog" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Monitor ASTRA backend health and restart if unhealthy"
```

## 4. Log Rotation Script

### Create Log Rotation Script
```powershell
# Create: X:\PROJECT_ASTRA\scripts\rotate_logs.ps1
$content = @'
# Log Rotation for ASTRA
# Compress logs older than 7 days, delete logs older than 30 days

$logDir = "X:\PROJECT_ASTRA\logs"
$archiveDir = "$logDir\archive"
$daysToKeep = 30
$daysToCompress = 7

# Create archive directory if it doesn't exist
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir | Out-Null
}

# Compress logs older than 7 days
Get-ChildItem -Path $logDir -Filter "*.log" -File | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$daysToCompress) } |
    ForEach-Object {
        $zipName = "$archiveDir\$($_.BaseName)_$($_.LastWriteTime.ToString('yyyyMMdd')).zip"
        if (-not (Test-Path $zipName)) {
            Compress-Archive -Path $_.FullName -DestinationPath $zipName
            Remove-Item $_.FullName
            Write-Host "Compressed: $($_.Name)"
        }
    }

# Delete archived logs older than 30 days
Get-ChildItem -Path $archiveDir -Filter "*.zip" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$daysToKeep) } |
    ForEach-Object {
        Remove-Item $_.FullName
        Write-Host "Deleted: $($_.Name)"
    }
'@

$content | Set-Content "X:\PROJECT_ASTRA\scripts\rotate_logs.ps1" -Encoding UTF8
```

### Schedule Daily Log Rotation
```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument `
  "-WindowStyle Hidden -File `"X:\PROJECT_ASTRA\scripts\rotate_logs.ps1`""

$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "ASTRA_Log_Rotation" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Rotate and compress ASTRA logs daily at 3 AM"
```

## 5. Database Backup Script

### Create Backup Script
```powershell
# Create: X:\PROJECT_ASTRA\scripts\backup_database.ps1
$content = @'
# Database Backup for ASTRA
# Creates nightly backup of astra.db with timestamp

$dbPath = "X:\PROJECT_ASTRA\data\database\astra.db"
$backupDir = "X:\PROJECT_ASTRA\data\database\backups"
$daysToKeep = 14

# Create backup directory if it doesn't exist
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

# Create timestamped backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "$backupDir\astra_$timestamp.db"

if (Test-Path $dbPath) {
    Copy-Item -Path $dbPath -Destination $backupPath
    Write-Host "Backup created: $backupPath"
    
    # Verify backup
    if ((Get-Item $backupPath).Length -gt 0) {
        Write-Host "Backup verified: $('{0:N2}' -f ((Get-Item $backupPath).Length / 1MB)) MB"
    } else {
        Write-Host "WARNING: Backup file is empty!" -ForegroundColor Red
    }
} else {
    Write-Host "ERROR: Database file not found: $dbPath" -ForegroundColor Red
}

# Delete backups older than retention period
Get-ChildItem -Path $backupDir -Filter "astra_*.db" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$daysToKeep) } |
    ForEach-Object {
        Remove-Item $_.FullName
        Write-Host "Deleted old backup: $($_.Name)"
    }
'@

$content | Set-Content "X:\PROJECT_ASTRA\scripts\backup_database.ps1" -Encoding UTF8
```

### Schedule Nightly Database Backup
```powershell
$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument `
  "-WindowStyle Hidden -File `"X:\PROJECT_ASTRA\scripts\backup_database.ps1`""

$trigger = New-ScheduledTaskTrigger -Daily -At "03:30"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "ASTRA_Database_Backup" `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Backup ASTRA database daily at 3:30 AM"
```

## 6. Verify All Tasks

```powershell
# List all ASTRA scheduled tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ASTRA_*" } | 
  Select-Object TaskName, State, @{Name="NextRun";Expression={(Get-ScheduledTaskInfo $_).NextRunTime}} |
  Format-Table -AutoSize
```

## 7. Manual Task Control

```powershell
# Start all ASTRA tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ASTRA_*" } | Start-ScheduledTask

# Stop all ASTRA tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ASTRA_*" } | Stop-ScheduledTask

# Disable all ASTRA tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ASTRA_*" } | Disable-ScheduledTask

# Enable all ASTRA tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "ASTRA_*" } | Enable-ScheduledTask
```

## 8. Monitoring Dashboard (Optional - Grafana)

### Install Prometheus Windows Exporter
```powershell
# Download from: https://github.com/prometheus-community/windows_exporter/releases
# Install and configure to export on port 9182
```

### Configure Prometheus
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'astra'
    static_configs:
      - targets: ['127.0.0.1:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
    
  - job_name: 'windows'
    static_configs:
      - targets: ['127.0.0.1:9182']
```

### Setup Grafana Dashboard
- Import dashboard ID: 14694 (Windows metrics)
- Create custom dashboard for ASTRA metrics:
  - `astra_requests_total`
  - `astra_request_duration_seconds`
  - `astra_tokens_total`
