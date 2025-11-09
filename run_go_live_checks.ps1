# ASTRA Go-Live Check Script
Write-Host "ASTRA Pre-deployment Validation Suite" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Ensure we're in a virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$requiredPackages = @(
    "fastapi",
    "uvicorn",
    "aiohttp",
    "locust",
    "structlog"
)

foreach ($package in $requiredPackages) {
    $installed = pip list | Select-String -Pattern "^$package\s"
    if (-not $installed) {
        Write-Host "Installing $package..." -ForegroundColor Yellow
        pip install $package
    }
}

# Start ASTRA server in background
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    uvicorn astra_core:app --port 8001
}

# Wait for server to start
Write-Host "Starting ASTRA server..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Run validation suite
try {
    Write-Host "Running pre-deployment checks..." -ForegroundColor Yellow
    python go_live_check.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nValidation PASSED ✅" -ForegroundColor Green
        Write-Host "Review go_live_validation_report.md for details"
    } else {
        Write-Host "`nValidation FAILED ❌" -ForegroundColor Red
        Write-Host "Check go_live_validation_report.md for failure details"
    }
} finally {
    # Cleanup
    Write-Host "`nStopping ASTRA server..." -ForegroundColor Yellow
    Stop-Job -Job $serverJob
    Remove-Job -Job $serverJob
}

# Final status
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🚀 Ready for deployment!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Deployment blockers found" -ForegroundColor Red
    exit 1
}