# GPT-OSS Integration Runbook

This guide explains how to run ASTRA 2.0 against the bundled GPT-OSS 20B Harmony model using llama.cpp on Windows.

## Prerequisites

- Windows host with at least 32 GB RAM
- `llama-server.exe` built from the workspace (available under `astra-local\backend\bin\llama.cpp\build\bin`)
- GPT-OSS model: `X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf`
- Python virtual environment created at `X:\PROJECT_ASTRA\.venv`

## 1. Launch llama.cpp with GPT-OSS Harmony

```powershell
$LlamaServer = where.exe /r X:\PROJECT_ASTRA llama-server.exe | Select-Object -First 1
if (-not $LlamaServer) { throw "llama-server.exe not found" }

Start-Process -FilePath $LlamaServer -ArgumentList @(
    "--model","X:/PROJECT_ASTRA/astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf",
    "--host","127.0.0.1",
    "--port","8001",
    "--threads",$Env:NUMBER_OF_PROCESSORS,
    "--ctx-size","4096",
    "--chat-template","gpt-oss",
    "--batch-size","128",
    "--ubatch-size","32",
    "--parallel","1",
    "--n-gpu-layers","0"
) -WorkingDirectory (Split-Path $LlamaServer -Parent) -WindowStyle Minimized

(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8001/health').StatusCode
```

> Increase `--ctx-size` to `8192` only after verifying memory headroom. Reduce to `3072` or `2048` if paging occurs.

## 2. Configure ASTRA for GPT-OSS

Ensure `.env` contains the following entries (the defaults now ship with these values):

```
ASTRA_LLM_PROVIDER=llamacpp
ASTRA_LLM_BASE_URL=http://127.0.0.1:8001
ASTRA_LLM_MODEL_PATH=X:/PROJECT_ASTRA/astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf
ASTRA_LLM_USE_HARMONY_FORMAT=true
ASTRA_SAMPLING_PRESET=gptoss-strict
```

> The configuration loader now normalizes provider aliases like `llama_cpp` automatically, preventing startup failures.

## 3. Restart ASTRA API

```powershell
Start-Process -FilePath "X:\PROJECT_ASTRA\.venv\Scripts\python.exe" -ArgumentList @(
    "-m","uvicorn","astra.api.app:app",
    "--host","127.0.0.1",
    "--port","8080",
    "--workers","1",
    "--log-level","info"
) -WorkingDirectory "X:\PROJECT_ASTRA" -WindowStyle Minimized

(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/v1/system/health').StatusCode
```

## 4. Smoke Test Chat Endpoint

```powershell
$BaseUri = 'http://127.0.0.1:8080'
$Conversation = Invoke-RestMethod -Method Post -Uri "$BaseUri/v1/conversations/" -ContentType 'application/json' -Body '{}'
$ConvId = $Conversation.conversation_id

$ChatBody = @{
    conversation_id = $ConvId
    message         = "Please reply with a one-line greeting."
    use_memory      = $false
    temperature     = 0.7
    max_tokens      = 64
} | ConvertTo-Json -Compress

Invoke-RestMethod -Method Post -Uri "$BaseUri/v1/chat/" -ContentType 'application/json' -Body $ChatBody
```

If the request fails, validate llama.cpp health, `.env` values, and uvicorn logs.

## 5. Load Test Targets

Baseline (should hit ≥95% OK, p95 ≤ 1.2 s, p99 ≤ 2.5 s):

```powershell
$env:ASTRA_LOAD_URL      = "http://127.0.0.1:8080/v1/chat/"
$env:ASTRA_LOAD_METHOD   = "POST"
$env:ASTRA_LOAD_CONC     = "24"
$env:ASTRA_LOAD_SECS     = "45"
$env:ASTRA_LOAD_RPS      = "24"
$env:ASTRA_LOAD_PAYLOAD  = "X:\PROJECT_ASTRA\data\load_test_payload.json"
X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\scripts\load_test.py
```

Saturation (expect controlled 429/503, no crashes):

```powershell
$env:ASTRA_LOAD_CONC = "60"
$env:ASTRA_LOAD_SECS = "20"
$env:ASTRA_LOAD_RPS  = "60"
X:\PROJECT_ASTRA\.venv\Scripts\python.exe X:\PROJECT_ASTRA\scripts\load_test.py
```

After each run, capture counters via:

```powershell
(Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/metrics').Content |
    Select-String 'astra_http_requests_total{.*status="200"|.*status="503"|.*status="429"'
```

## 6. Memory and Performance Tuning

- Drop `--ctx-size` to `3072` or `2048` if RSS exceeds 28 GB.
- Lower `--batch-size` to `64` if CPU saturation raises latency.
- Attempt `--ctx-size 8192` only after baseline stability is proven.

## 7. Status Snippet Template

```markdown
### ASTRA – GPT-OSS Validation (YYYY-MM-DD)
llama.cpp: `llama-server.exe --model "X:/PROJECT_ASTRA/astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf" --host 127.0.0.1 --port 8001 --threads <nproc> --ctx-size 4096 --chat-template gpt-oss --batch-size 128 --ubatch-size 32 --parallel 1 --n-gpu-layers 0`
Baseline 24c/24rps/45s:
    {"calls":{int},"ok":{int},"ok_pct":{float},"p50":{float},"p95":{float},"p99":{float},"avg":{float}}

Saturation 60c/60rps/20s:
    {"calls":{int},"ok":{int},"ok_pct":{float},"p50":{float},"p95":{float},"p99":{float},"avg":{float}}

Metrics: status=200:{count}, status=503:{count}, status=429:{count}
Decision: **GO / NO-GO** (based on ≥95% OK and latency targets)
```
