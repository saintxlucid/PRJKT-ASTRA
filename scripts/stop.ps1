#!/usr/bin/env pwsh
# scripts/stop.ps1
# Stops all ASTRA-related processes (llama-server, uvicorn, python)

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = "Continue"

Write-Host "== ASTRA CORE STOP ==" -ForegroundColor Cyan
Write-Host "Stopping llama-server, uvicorn, and python processes..." -ForegroundColor Yellow
Write-Host ""

$processes = Get-Process | Where-Object { 
    $_.ProcessName -match 'llama-server|llama|uvicorn|python' 
}

if ($processes) {
    $count = ($processes | Measure-Object).Count
    Write-Host "Found $count process(es) to stop:" -ForegroundColor Yellow
    
    foreach ($proc in $processes) {
        try {
            Write-Host "  Stopping $($proc.ProcessName) (PID: $($proc.Id))..." -ForegroundColor Cyan
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            Write-Host "    Stopped" -ForegroundColor Green
        } catch {
            Write-Host "    Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "All ASTRA processes stopped." -ForegroundColor Green
} else {
    Write-Host "No ASTRA processes found running." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "To restart, run: .\scripts\ship.ps1" -ForegroundColor Cyan
