# Production Validation Script - GPT-OSS End-to-End Reliability Test
# Date: October 9, 2025

Write-Host "`n========================================"

 -ForegroundColor Cyan
Write-Host "   GPT-OSS PRODUCTION VALIDATION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Clear ports 8001 and 8080
Write-Host "[1/6] Clearing ports..." -ForegroundColor Yellow
$ports = @(8001,8080)
foreach ($p in $ports) {
  $connections = netstat -ano | findstr ":$p"
  if ($connections) {
    $connections | ForEach-Object {
      $processId = ($_ -split '\s+')[-1]
      if ($processId -match '^\d+$') { 
        try { Stop-Process -Id $processId -Force -ErrorAction Stop } catch {}
      }
    }
  }
}
Start-Sleep -Seconds 2
Write-Host "  ✓ Ports cleared`n" -ForegroundColor Green

# Resolve model path
Write-Host "[2/6] Resolving model path..." -ForegroundColor Yellow
$envLine = Get-Content ".\.env" | Select-String 'ASTRA_GPTOSS_MODEL_PATH='
$MODEL = $envLine.ToString().Split('=')[1].Trim('"').Trim()
if (-not (Test-Path $MODEL)) { throw "Model not found: $MODEL" }
Write-Host "  ✓ Model: $MODEL`n" -ForegroundColor Green

# Start llama.cpp
Write-Host "[3/6] Starting llama.cpp on port 8001..." -ForegroundColor Yellow
$LLAMA = "X:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe"
$threads = if ($env:NUMBER_OF_PROCESSORS) { $env:NUMBER_OF_PROCESSORS } else { 8 }
$llamaCmd = "& '$LLAMA' --model '$MODEL' --host 127.0.0.1 --port 8001 --threads $threads --parallel 1 --n-gpu-layers 0 --ctx-size 4096 --batch-size 128 --ubatch-size 32 --cache-type-k q8_0 --cache-type-v q8_0"
Start-Process pwsh -WindowStyle Minimized -ArgumentList "-NoExit", "-Command", $llamaCmd
Start-Sleep -Seconds 2

# Wait for llama.cpp
Write-Host "  ⏳ Waiting for llama.cpp..." -ForegroundColor Cyan
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try { 
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { throw "llama.cpp failed to start" }
Write-Host "  ✓ llama.cpp ready`n" -ForegroundColor Green

# Start ASTRA backend
Write-Host "[4/6] Starting ASTRA backend on port 8080..." -ForegroundColor Yellow
$backendCmd = "cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe -m uvicorn astra.api.app:app --host 127.0.0.1 --port 8080 --workers 1 --log-level info"
Start-Process pwsh -WindowStyle Minimized -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Seconds 2

# Wait for backend
Write-Host "  ⏳ Waiting for ASTRA backend..." -ForegroundColor Cyan
$ready = $false
for ($i = 1; $i -le 15; $i++) {
    try { 
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 2 -ErrorAction Stop
        if ($h.healthy -eq $true) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { throw "ASTRA backend failed to start" }
Write-Host "  ✓ ASTRA backend ready`n" -ForegroundColor Green

# Create conversation
Write-Host "[5/6] Running BASELINE load test..." -ForegroundColor Yellow
$convBody = "{`"title`":`"GPT-OSS Baseline`"}"
$conv = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8080/v1/conversations/" `
    -ContentType "application/json" -Body $convBody -TimeoutSec 10
$convId = $conv.id
Write-Host "  ✓ Conversation: $convId" -ForegroundColor Green

# Create payload
$payload = @{
    conversation_id = $convId
    message = "One-line greeting, please."
    use_memory = $false
    temperature = 0.2
    max_tokens = 32
}
$payload | ConvertTo-Json | Set-Content "X:\PROJECT_ASTRA\data\load_test_payload.json" -Encoding UTF8

# Run baseline test
$env:ASTRA_LOAD_URL = "http://127.0.0.1:8080/v1/chat/"
$env:ASTRA_LOAD_METHOD = "POST"
$env:ASTRA_LOAD_CONC = "24"
$env:ASTRA_LOAD_SECS = "45"
$env:ASTRA_LOAD_RPS = "24"
$env:ASTRA_LOAD_PAYLOAD = "X:\PROJECT_ASTRA\data\load_test_payload.json"

Write-Host "  Running baseline: 24 rps, 45 seconds..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object "X:\PROJECT_ASTRA\data\baseline_out.txt"
Write-Host "  ✓ Baseline complete`n" -ForegroundColor Green

# Save baseline metrics
(Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5).Content | 
    Set-Content "X:\PROJECT_ASTRA\data\baseline_metrics.prom"

# Run saturation test
Write-Host "[6/6] Running SATURATION load test..." -ForegroundColor Yellow
$env:ASTRA_LOAD_CONC = "60"
$env:ASTRA_LOAD_SECS = "20"
$env:ASTRA_LOAD_RPS = "60"

Write-Host "  Running saturation: 60 rps, 20 seconds..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object "X:\PROJECT_ASTRA\data\saturation_out.txt"
Write-Host "  ✓ Saturation complete`n" -ForegroundColor Green

# Save saturation metrics
(Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5).Content | 
    Set-Content "X:\PROJECT_ASTRA\data\saturation_metrics.prom"

# Record results
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   RECORDING RESULTS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
$baselineOut = Get-Content "X:\PROJECT_ASTRA\data\baseline_out.txt" -Raw
$saturationOut = Get-Content "X:\PROJECT_ASTRA\data\saturation_out.txt" -Raw

# Append to DEPLOYMENT_STATUS.md
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"========================================" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"## Validation Run - $stamp" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"### Baseline Load Test - 24 concurrent, 24 RPS, 45 seconds" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"``````" | Add-Content ".\DEPLOYMENT_STATUS.md"
$baselineOut | Add-Content ".\DEPLOYMENT_STATUS.md"
"``````" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"### Saturation Load Test - 60 concurrent, 60 RPS, 20 seconds" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"``````" | Add-Content ".\DEPLOYMENT_STATUS.md"
$saturationOut | Add-Content ".\DEPLOYMENT_STATUS.md"
"``````" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"### Go/No-Go Decision: PENDING REVIEW" | Add-Content ".\DEPLOYMENT_STATUS.md"
"" | Add-Content ".\DEPLOYMENT_STATUS.md"
"========================================" | Add-Content ".\DEPLOYMENT_STATUS.md"

Write-Host "✓ Results appended to DEPLOYMENT_STATUS.md" -ForegroundColor Green
Write-Host "`nOutput files:" -ForegroundColor Cyan
Write-Host "  - data\baseline_out.txt" -ForegroundColor White
Write-Host "  - data\saturation_out.txt" -ForegroundColor White
Write-Host "  - data\baseline_metrics.prom" -ForegroundColor White
Write-Host "  - data\saturation_metrics.prom" -ForegroundColor White
Write-Host "  - DEPLOYMENT_STATUS.md (updated)`n`n" -ForegroundColor White
