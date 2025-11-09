# Start Mock LLM Server for ASTRA Testing
# This provides a working LLM API for testing ASTRA 3.0

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   🧠 MOCK LLM SERVER - ASTRA TESTING" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "Starting Mock LLM Server on port 9010..." -ForegroundColor Yellow
Write-Host "This provides OpenAI-compatible API for testing`n" -ForegroundColor Gray

Write-Host "⚠️  KEEP THIS WINDOW OPEN" -ForegroundColor Yellow
Write-Host "`n================================================================`n" -ForegroundColor Cyan

python mock_llm_server.py
