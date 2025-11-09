# ASTRA Ascension Stack V2 - Restart Script
# Stops existing server and starts with V2 add-ons loaded

Write-Host "`n🔄 Restarting ASTRA Ascension Stack V2..." -ForegroundColor Cyan

# Stop existing Python processes
Write-Host "Stopping existing server..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -eq "" -and $_.StartTime -gt (Get-Date).AddHours(-1)
}

if ($pythonProcesses) {
    foreach ($proc in $pythonProcesses) {
        Write-Host "  Stopping process $($proc.Id)..." -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Set PYTHONPATH
$env:PYTHONPATH = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
Write-Host "PYTHONPATH set: $env:PYTHONPATH" -ForegroundColor Green

# Optional: Set Whisper environment variables (uncomment if you have whisper.cpp)
# $env:WHISPER_BIN = "C:\path\to\whisper.cpp\main.exe"
# $env:WHISPER_MODEL = "C:\path\to\whisper.cpp\models\ggml-turbo.bin"

# Launch server
Write-Host "`n🚀 Launching server with V2 add-ons..." -ForegroundColor Cyan
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python launch_ascension_stack.py

Write-Host "`n✅ Server started!" -ForegroundColor Green
Write-Host "   🎛️  Control Panel: http://127.0.0.1:8765/" -ForegroundColor White
Write-Host "   📚 API Docs: http://127.0.0.1:8765/docs" -ForegroundColor White
Write-Host "   🎤 Voice Health: http://127.0.0.1:8765/api/voice/health" -ForegroundColor White
Write-Host "   🎹 DAW Tools: 6 actions registered" -ForegroundColor White
