# Register ASTRA_CORE Docs Guardrail Scheduled Task
# Run this script once to set up nightly documentation validation at 3:00 AM

$taskName = "ASTRA_CORE-Docs-Guardrail"
$scriptPath = Join-Path (Resolve-Path .).Path "scripts\docs_guardrail.ps1"
$logDir = Join-Path (Resolve-Path .).Path "logs"

# Ensure logs directory exists
if (-not (Test-Path $logDir)) {
  New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}

$logPath = Join-Path $logDir "docs_guardrail_$(Get-Date -Format 'yyyy-MM-dd').txt"

$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" > `"$logPath`" 2>&1"

$trigger = New-ScheduledTaskTrigger -Daily -At 3am

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
  Write-Host "⚠ Task '$taskName' already exists. Unregistering..." -ForegroundColor Yellow
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Nightly docs quality guardrail for ASTRA_CORE" `
  -User $env:USERNAME

Write-Host "✓ Scheduled task '$taskName' registered successfully" -ForegroundColor Green
Write-Host "  Runs daily at 3:00 AM" -ForegroundColor Cyan
Write-Host "  Logs to: $logDir\docs_guardrail_YYYY-MM-DD.txt" -ForegroundColor Cyan
Write-Host "`nTo test immediately, run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
