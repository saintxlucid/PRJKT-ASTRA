#!/usr/bin/env pwsh
# ASTRA OS — Start All Services

Write-Host "🌌 Starting ASTRA OS Services..." -ForegroundColor Cyan
Write-Host ""

# Check if services are already running
$memoryRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*embed_server.py*"}
$pantheonRunning = Get-Process node -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*vite*"}

if ($memoryRunning) {
    Write-Host "⚠ Memory service already running" -ForegroundColor Yellow
} else {
    Write-Host "🧠 Starting Dream Grove Memory Service..." -ForegroundColor Green
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\services\memory'; .\.venv\Scripts\Activate.ps1; python embed_server.py"
    Start-Sleep -Seconds 2
}

if ($pantheonRunning) {
    Write-Host "⚠ Pantheon UI already running" -ForegroundColor Yellow
} else {
    Write-Host "🎨 Starting Pantheon UI..." -ForegroundColor Green
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\apps\pantheon'; npm run dev"
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "✓ Services starting up..." -ForegroundColor Green
Write-Host ""
Write-Host "📍 Memory API:   http://127.0.0.1:7007" -ForegroundColor Cyan
Write-Host "📍 Pantheon UI:  http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in each terminal to stop services" -ForegroundColor Yellow
