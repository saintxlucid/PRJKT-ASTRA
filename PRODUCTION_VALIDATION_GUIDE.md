# Production Reliability Validation - Execution Guide
# Date: October 9, 2025
# Status: Ready for Manual Execution

## Current Status

✅ **Prerequisites Verified:**
- GPT-OSS model found: `X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf`
- llama-server.exe found: `X:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe`
- ASTRA backend running: Port 8080 (healthy, 25 memories)
- .env updated with correct model path

## Step-by-Step Execution

### STEP 1: Start GPT-OSS llama.cpp Server

**Terminal 1** (keep open):
```powershell
cd X:\PROJECT_ASTRA
$MODEL = "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"
$LLAMA = "X:\PROJECT_ASTRA\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe"
& $LLAMA --model $MODEL --host 127.0.0.1 --port 8001 --threads 8 --parallel 1 --n-gpu-layers 0 --ctx-size 4096 --batch-size 128 --ubatch-size 32 --cache-type-k q8_0 --cache-type-v q8_0
```

**Wait for:** "server is listening on http://127.0.0.1:8001"

**Verify:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8001/health"
```

### STEP 2: Create Test Conversation

**Terminal 2:**
```powershell
cd X:\PROJECT_ASTRA
$conv = Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8080/v1/conversations/" `
  -ContentType "application/json" -Body '{"title":"GPT-OSS Baseline Load Test"}'
$convId = $conv.id
Write-Host "Conversation ID: $convId" -ForegroundColor Green
```

### STEP 3: Prepare Load Test Payload

```powershell
cd X:\PROJECT_ASTRA
@"
{"conversation_id":"$convId","message":"One-line greeting.","use_memory":false,"temperature":0.2,"max_tokens":32}
"@ | Set-Content X:\PROJECT_ASTRA\data\load_test_payload.json -Encoding UTF8
```

### STEP 4: Run Baseline Load Test

**SLO Target:** OK ≥ 95%, p95 ≤ 1.2s, p99 ≤ 2.5s, no crashes

```powershell
cd X:\PROJECT_ASTRA
$env:ASTRA_LOAD_URL="http://127.0.0.1:8080/v1/chat/"
$env:ASTRA_LOAD_METHOD="POST"
$env:ASTRA_LOAD_CONC="24"
$env:ASTRA_LOAD_SECS="45"
$env:ASTRA_LOAD_RPS="24"
$env:ASTRA_LOAD_PAYLOAD="X:\PROJECT_ASTRA\data\load_test_payload.json"
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object -FilePath ".\data\baseline_load_test.log"
```

**Save results:**
```powershell
# Copy JSON output to deployment status
```

### STEP 5: Run Saturation Load Test

**SLO Target:** Some 503/429, no 5xx storm

```powershell
cd X:\PROJECT_ASTRA
$env:ASTRA_LOAD_CONC="60"
$env:ASTRA_LOAD_SECS="20"
$env:ASTRA_LOAD_RPS="60"
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object -FilePath ".\data\saturation_load_test.log"
```

**Check metrics:**
```powershell
(Invoke-WebRequest http://127.0.0.1:8080/metrics).Content | 
  Select-String 'astra_http_requests_total{.*status="200"|.*status="503"|.*status="429"'
```

### STEP 6: Fix Failing Tests

```powershell
cd X:\PROJECT_ASTRA
.\.venv\Scripts\python.exe -m pytest -v --tb=short
```

**Target:** 49/49 passing

Common fixes:
- Import path issues: Update `tests/conftest.py`
- Type hints: Add `from __future__ import annotations`
- Harmony config: Ensure `ConfigDict` is used

### STEP 7: Record Results

Append to `DEPLOYMENT_STATUS.md`:
- Baseline test JSON
- Saturation test JSON
- Go/No-Go decision based on SLOs

---

## Troubleshooting

### High Latency
```powershell
# Reduce context size
--ctx-size 3072 or --ctx-size 2048
--batch-size 64
```

### Too Many 500s
```bash
# Check .env
ASTRA_ACTIVE_GGUF=X:/PROJECT_ASTRA/astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf
ASTRA_SAMPLING_PRESET=gptoss-strict
```

### Queue Overflows
```bash
# Tune concurrency limits in .env
ASTRA_CONCURRENCY_MAX_INFLIGHT=24
ASTRA_CONCURRENCY_MAX_QUEUE=48
ASTRA_RATE_LIMIT_MAX=30
ASTRA_RATE_LIMIT_WINDOW_SEC=5
```

---

## After Go Decision

See `ops_hardening_scripts.ps1` for:
1. Auto-start scheduled tasks
2. Health watchdog
3. Log rotation and backups
