# 🚀 DIRECTIVES 001 & 002 — QUICK DEPLOYMENT GUIDE

**Status**: Ready for production  
**Timeline**: 15-45 minutes total (both directives)  
**Prerequisites**: PowerShell admin terminal, venv activated, llama.cpp running on 127.0.0.1:8001

---

## ⚡ DIRECTIVE 001 — Capacity Controls (15-30 min)

### One-Command Deploy
```powershell
.\scripts\directive_001_go_live.ps1
```

### What Gets Deployed
- ✅ **Per-key rate limiting**: 120 req/60s per API key (token bucket algorithm)
- ✅ **Queue metrics**: Depth gauge, wait time histogram
- ✅ **Per-key counters**: Allowed/blocked requests per key_hash
- ✅ **Benchmark tool**: Test llama.cpp with different flags

### Manual Steps (if automated script unavailable)
```powershell
# 1. Configure .env
Add-Content .\.env "ASTRA_PER_KEY_RATE=120"
Add-Content .\.env "ASTRA_PER_KEY_PERIOD_SEC=60"

# 2. Restart backend
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit","-Command","cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe run_server.py"
Start-Sleep 10

# 3. Verify metrics
curl http://127.0.0.1:8080/metrics | Select-String "astra_limiter_per_key|astra_queue"

# 4. Burst test (expect ~120 success, ~30 blocked)
$apiKey = (Get-Content .\.env | Select-String '^ASTRA_API_KEY=').ToString().Split('=')[1].Trim()
$conv = (Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8080/v1/conversations/" -Headers @{"X-API-Key"=$apiKey;"Content-Type"="application/json"} -Body '{"title":"Test"}').id
$payload = @{conversation_id=$conv; message="ok"; use_memory=$false} | ConvertTo-Json -Compress
1..150 | ForEach-Object { Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/chat/" -Method POST -Headers @{"X-API-Key"=$apiKey;"Content-Type"="application/json"} -Body $payload -UseBasicParsing -TimeoutSec 10 } | Group-Object StatusCode
```

### Validation Checklist
- [ ] Health endpoint responds (no auth): `curl http://127.0.0.1:8080/v1/system/health`
- [ ] 4 new metrics visible: `astra_limiter_per_key_allowed_total`, `astra_limiter_per_key_blocked_total`, `astra_queue_depth`, `astra_queue_wait_seconds`
- [ ] Burst test shows mix of 200 and 429 responses
- [ ] Blocked counter > 0 after burst: `curl http://127.0.0.1:8080/metrics | Select-String "limiter_per_key_blocked"`

### Grafana Import
1. Open http://localhost:3000
2. Click **+** → **Import**
3. Upload `ops\grafana_astra_dashboard.json`
4. Select Prometheus datasource
5. Verify 14 panels render (4 new capacity panels)

### Alerts to Configure
```promql
# Alert 1: Per-Key Block Rate High
rate(astra_limiter_per_key_blocked_total[5m]) > 10 for 5m

# Alert 2: Queue Depth Sustained
avg_over_time(astra_queue_depth[5m]) > 50 for 10m
```

### Benchmark llama.cpp (Optional)
```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_llama_flags.py
# Outputs JSON with mean/p50/p95/p99 latencies
# Try different --threads, --batch, --ctx-size flags
# Update llama.cpp startup script with best config
```

### Rollback (< 2 minutes)
```powershell
git restore src/astra/security.py src/astra/metrics.py src/astra/queue_guard.py
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit","-Command","cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe run_server.py"
```

---

## 🌊 DIRECTIVE 002 — SSE Streaming (10-15 min)

### One-Command Deploy
```powershell
.\scripts\directive_002_sse_streaming.ps1
```

### What Gets Deployed
- ✅ **POST /v1/chat/stream**: Server-Sent Events endpoint
- ✅ **3 new metrics**: `astra_stream_tokens_total`, `astra_stream_clients_active`, `astra_stream_chunk_size_bytes`
- ✅ **Backward compatible**: Non-streaming POST /v1/chat/ unchanged
- ✅ **Same middleware**: Auth, rate limits, tracing all apply

### Manual Test
```powershell
# Extract API key
$apiKey = (Get-Content .\.env | Select-String '^ASTRA_API_KEY=').ToString().Split('=')[1].Trim()

# Create conversation
$conv = (Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8080/v1/conversations/" -Headers @{"X-API-Key"=$apiKey;"Content-Type"="application/json"} -Body '{"title":"Stream Test"}').id

# Stream request (requires curl for SSE)
$payload = @{conversation_id=$conv; message="Count to 5"; use_memory=$false} | ConvertTo-Json
$payload | Out-File temp_payload.json
curl -N -H "Accept: text/event-stream" -H "X-API-Key: $apiKey" -H "Content-Type: application/json" -d "@temp_payload.json" http://127.0.0.1:8080/v1/chat/stream
Remove-Item temp_payload.json
```

### Expected Output
```
data: 1
data: ,
data:  2
data: ,
data:  3
data: ,
data:  4
data: ,
data:  5
data: [DONE]
```

### Validation Checklist
- [ ] Backend restarted successfully
- [ ] `/v1/chat/stream` responds with `text/event-stream` content-type
- [ ] First token arrives in < 300ms (perceived speed)
- [ ] Stream ends with `data: [DONE]`
- [ ] 3 new metrics visible: `curl http://127.0.0.1:8080/metrics | Select-String "astra_stream"`
- [ ] Non-streaming endpoint still works: `POST /v1/chat/`

### Grafana Panels to Add
```promql
# Panel 1: Stream Tokens/sec
rate(astra_stream_tokens_total[5m])

# Panel 2: Active Streaming Clients
astra_stream_clients_active

# Panel 3: Chunk Size p95 (bytes)
histogram_quantile(0.95, rate(astra_stream_chunk_size_bytes_bucket[5m]))
```

### Unit Tests
```powershell
pytest tests\unit\test_streaming.py -v
# Expected: 8 passed
```

### Rollback
```powershell
git restore src/astra/api/routes/chat.py src/astra/metrics.py
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit","-Command","cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe run_server.py"
```

---

## 🎯 Combined Success Criteria

### Directive 001
- ✅ 4 new metrics present in `/metrics`
- ✅ Burst test shows ~120 OK + ~30 blocked (80/20 split)
- ✅ Per-key counters incrementing independently
- ✅ Grafana dashboard imports cleanly

### Directive 002
- ✅ 3 new streaming metrics present
- ✅ First token arrives < 300ms
- ✅ SSE format correct (data: prefix, [DONE] terminator)
- ✅ Non-streaming endpoint unaffected

---

## 📊 Metrics Reference

### Directive 001 Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `astra_queue_depth` | Gauge | Current request queue size |
| `astra_queue_wait_seconds` | Histogram | Time waiting in queue (11 buckets: 5ms-10s) |
| `astra_limiter_per_key_allowed_total{key_hash}` | Counter | Requests allowed per key |
| `astra_limiter_per_key_blocked_total{key_hash}` | Counter | Requests blocked (429) per key |

### Directive 002 Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `astra_stream_tokens_total` | Counter | Total tokens streamed to clients |
| `astra_stream_clients_active` | Gauge | Active streaming connections |
| `astra_stream_chunk_size_bytes` | Histogram | Chunk size distribution (8 buckets: 10B-5KB) |

---

## 🔥 Common Issues & Fixes

### Issue: No metrics visible
**Fix**: Backend may not have restarted with new code
```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit","-Command","cd X:\PROJECT_ASTRA; .\.venv\Scripts\python.exe run_server.py"
Start-Sleep 10
curl http://127.0.0.1:8080/v1/system/health
```

### Issue: Burst test shows 0 blocked requests
**Fix**: Rate too high or not enough requests sent fast enough
```powershell
# Lower rate for testing
(Get-Content .\.env) -replace 'ASTRA_PER_KEY_RATE=.*', 'ASTRA_PER_KEY_RATE=30' | Set-Content .\.env
# Restart backend
```

### Issue: Streaming returns 500 error
**Fix**: Check llama.cpp is running and streaming enabled
```powershell
curl http://127.0.0.1:8001/health
# Ensure llama.cpp started with --port 8001
```

### Issue: First token slow (> 1 second)
**Fix**: Benchmark llama.cpp flags and optimize
```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_llama_flags.py
# Test different thread counts: --threads 4, --threads 8, etc.
```

---

## 📝 Git Commits

### After Directive 001
```powershell
git add -A
git commit -m "capacity(Dir001): per-key limits + queue metrics live; baseline captured"
git push
```

### After Directive 002
```powershell
git add -A
git commit -m "streaming(Dir002): SSE endpoint + metrics live; first-word latency < 300ms"
git push
```

---

## 🚀 Next Steps (Directive 003)

**Goal**: Health drill-down + CI load baseline

**Plan**:
1. Expand `/v1/system/health` to show dependency statuses (llama.cpp, SQLite, ChromaDB)
2. Create CI workflow to run load test baseline (50 concurrent users, 1000 requests)
3. Assert baseline metrics (p95 latency < 2s, error rate < 1%)
4. Store baseline in `docs/baseline_metrics.json`

**Timeline**: 1-2 hours

**Blocker**: None (can start immediately after Directives 001 & 002)

---

## 📚 Documentation Links

- **Full Deployment Guide**: `CAPACITY_MANAGEMENT_GUIDE.md`
- **Implementation Summary**: `CAPACITY_IMPLEMENTATION_SUMMARY.md`
- **A→Z Roadmap**: `ROADMAP_A_TO_Z.md`
- **Directive 001 Execution**: `DIRECTIVE_001_EXECUTION.md`
- **Quick Command Card**: `DIRECTIVE_001_QUICK.md`
- **RUNBOOK**: `docs/RUNBOOK.md`
- **QUICKSTART**: `QUICKSTART.md`

---

**Last Updated**: 2025-01-09  
**Phase**: 1 (Capacity & Safety) — 50% complete (Dir 001 + 002 of 4 tasks)  
**Next Gate**: 3 green baselines, tuned alerts, runbook validation
