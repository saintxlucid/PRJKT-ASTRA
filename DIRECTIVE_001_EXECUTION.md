# 🚀 DIRECTIVE 001 — Execution Commands

**Date:** October 9, 2025  
**Objective:** Deploy capacity controls (per-key limits + queue metrics + benchmarking)  
**Duration:** 30-45 minutes  
**Risk:** LOW (additive, backward-compatible)

---

## ⚡ Quick Start (Copy-Paste Commands)

### Option 1: Automated Deployment (Recommended)
```powershell
# Run deployment script
.\scripts\deploy_capacity_controls.ps1

# Expected: Automated validation + guidance
# Duration: ~15 minutes
```

### Option 2: Manual Step-by-Step
```powershell
# Step 1: Configure per-key limits
Add-Content .env "`nASTRA_PER_KEY_RATE=120"
Add-Content .env "`nASTRA_PER_KEY_PERIOD_SEC=60"

# Step 2: Restart backend (Ctrl+C in server terminal, then:)
.\.venv\Scripts\python.exe run_server.py

# Step 3: Smoke checks
curl http://127.0.0.1:8080/v1/system/health
curl http://127.0.0.1:8080/metrics | Select-String "astra_limiter_per_key"

# Step 4: Burst test (150 requests)
$h=@{"X-API-Key"="$env:ASTRA_API_KEY";"Content-Type"="application/json"}
$body='{"conversation_id":"burst-test","message":"ping","use_memory":false}'

1..150 | ForEach-Object {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/chat/" `
            -Method POST -Headers $h -Body $body -UseBasicParsing -TimeoutSec 10
        Write-Host "." -NoNewline -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 429) {
            Write-Host "X" -NoNewline -ForegroundColor Yellow
        } else {
            Write-Host "!" -NoNewline -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 50
}

Write-Host "`nExpected: ~120 dots (200 OK), ~30 X's (429 blocked)"

# Step 5: Verify metrics
curl http://127.0.0.1:8080/metrics > metrics.txt
Select-String -Path metrics.txt -Pattern "astra_limiter_per_key_allowed_total"
Select-String -Path metrics.txt -Pattern "astra_limiter_per_key_blocked_total"
Select-String -Path metrics.txt -Pattern "astra_queue_depth"

# Step 6: Benchmark llama.cpp (optional but recommended)
.\.venv\Scripts\python.exe scripts\benchmark_llama_flags.py
# Save output, test different flag combos

# Step 7: Git commit
git add -A
git commit -m "capacity: per-key limits + queue metrics (Directive 001)

- Add PerKeyLimiter with token bucket algorithm
- Add queue depth and wait time metrics  
- Add astra_limiter_per_key_allowed/blocked_total counters
- Add benchmark_llama_flags.py for flag tuning
- Default: 120 req/60s = 2 req/sec per key
"
```

---

## 📊 Grafana Import (Step 5 Continued)

### Import Dashboard
1. Open Grafana → http://localhost:3000 (if installed)
2. Click **+** → **Import Dashboard**
3. Upload file: `X:\PROJECT_ASTRA\ops\grafana_astra_dashboard.json`
4. Select Prometheus data source
5. Click **Import**

### Add New Alerts

**Alert 1: High Queue Depth**
```yaml
Alert Name: ASTRA - Queue Depth High
Query: avg_over_time(astra_queue_depth[5m])
Condition: WHEN avg() IS ABOVE 50
For: 2m
Severity: Warning
Message: Queue depth >50 for 2min. Consider increasing ASTRA_MAX_INFLIGHT or lowering per-key rates.
```

**Alert 2: High Per-Key Block Rate**
```yaml
Alert Name: ASTRA - Per-Key Rate Limiting Active
Query: sum(rate(astra_limiter_per_key_blocked_total[5m]))
Condition: WHEN last() IS ABOVE 10
For: 2m
Severity: Info
Message: Per-key blocking >10 req/sec. Check if legitimate traffic or abuse.
```

**Alert 3: Low Allow Ratio (Fairness)**
```yaml
Alert Name: ASTRA - Low Allow Ratio
Query: |
  sum(rate(astra_limiter_per_key_allowed_total[5m])) 
  / 
  (sum(rate(astra_limiter_per_key_allowed_total[5m])) + sum(rate(astra_limiter_per_key_blocked_total[5m])))
Condition: WHEN last() IS BELOW 0.70
For: 5m
Severity: Warning
Message: <70% of requests allowed. Per-key limits may be too strict.
```

**Alert 4: High Queue Wait Time**
```yaml
Alert Name: ASTRA - High Queue Wait p95
Query: histogram_quantile(0.95, rate(astra_queue_wait_seconds_bucket[5m]))
Condition: WHEN last() IS ABOVE 2.0
For: 3m
Severity: Warning
Message: p95 queue wait >2s. System approaching capacity.
```

---

## 🧪 Acceptance Criteria Checklist

### Functional Tests
- [ ] **Health check** - `curl http://127.0.0.1:8080/v1/system/health` returns 200
- [ ] **Metrics visible** - `/metrics` shows `astra_limiter_per_key_*` and `astra_queue_*`
- [ ] **Per-key limiting** - Burst test shows ~120 OK, ~30 blocked (429)
- [ ] **Independent budgets** - Two different API keys don't interfere
- [ ] **Exempt paths** - Health/metrics/docs accessible without auth
- [ ] **No 5xx errors** - Burst test shows only 200 or 429, no crashes

### Metrics Validation
- [ ] `astra_queue_depth` - Shows current queue size (should be 0 at idle)
- [ ] `astra_queue_wait_seconds_count` - Increments with requests
- [ ] `astra_limiter_per_key_allowed_total{key_hash="..."}` - Increments per key
- [ ] `astra_limiter_per_key_blocked_total{key_hash="..."}` - Increments when limited

### Grafana Validation
- [ ] Dashboard imports without errors
- [ ] All 14 panels render (10 existing + 4 new)
- [ ] New panels show data:
  - Per-Key Block Rate
  - Allow/Block Fairness Ratio
  - Queue Depth
  - Queue Wait p95
- [ ] Alerts save without errors
- [ ] Alerts arm (green state)

### Performance Validation
- [ ] Burst test completes without backend crash
- [ ] llama.cpp remains responsive during burst
- [ ] Queue depth returns to 0 after burst
- [ ] No memory leaks (check Task Manager before/after)

### Documentation Validation
- [ ] `CAPACITY_MANAGEMENT_GUIDE.md` - Complete deployment guide exists
- [ ] `CAPACITY_IMPLEMENTATION_SUMMARY.md` - Quick reference exists
- [ ] `ROADMAP_A_TO_Z.md` - Updated with Phase 1 progress
- [ ] Unit tests documented and passing (12/12)

---

## 🔍 Troubleshooting

### Issue: "Per-key metrics not showing"
**Cause:** Backend not restarted after .env changes

**Fix:**
```powershell
# Stop backend (Ctrl+C)
# Restart:
.\.venv\Scripts\python.exe run_server.py

# Verify:
curl http://127.0.0.1:8080/metrics | Select-String "astra_limiter"
```

---

### Issue: "All requests get 429 immediately"
**Cause:** Per-key rate too low or bucket not refilling

**Fix:**
```powershell
# Check config
Get-Content .env | Select-String "ASTRA_PER_KEY"

# Increase rate:
(Get-Content .env) -replace 'ASTRA_PER_KEY_RATE=\d+', 'ASTRA_PER_KEY_RATE=300' | Set-Content .env

# Restart backend
```

---

### Issue: "Burst test shows no 429s"
**Cause:** Rate limit higher than test count, or backend not using new middleware

**Check middleware loaded:**
```powershell
# Look for "per_key_limiter_initialized" in logs
Get-Content logs\astra.log | Select-String "per_key_limiter"

# If not found, verify code changes:
Select-String -Path src\astra\security.py -Pattern "class PerKeyLimiter"
```

---

### Issue: "Grafana panels show 'No data'"
**Cause:** Prometheus not scraping, or metrics not being emitted

**Fix:**
```powershell
# 1. Check Prometheus is scraping:
curl http://localhost:9090/api/v1/targets

# 2. Verify ASTRA metrics endpoint:
curl http://127.0.0.1:8080/metrics | Measure-Object -Line
# Should show >100 lines

# 3. Send test traffic to generate metrics:
1..10 | % { curl http://127.0.0.1:8080/v1/system/health }
```

---

## 🎯 Expected Results Summary

### Before Deployment
```
# Metrics endpoint
astra_requests_total{...}
astra_request_duration_seconds{...}
astra_tokens_total{...}
# (No per-key or queue metrics)
```

### After Deployment
```
# New metrics added:
astra_queue_depth 0.0
astra_queue_wait_seconds_bucket{le="0.01"} 5.0
astra_queue_wait_seconds_bucket{le="0.025"} 10.0
...
astra_queue_wait_seconds_count 150.0
astra_queue_wait_seconds_sum 2.345

astra_limiter_per_key_allowed_total{key_hash="abc123..."} 120.0
astra_limiter_per_key_blocked_total{key_hash="abc123..."} 30.0
```

### Burst Test Output
```
Expected pattern:
....................  (First 20: all 200 OK)
....................
....................
....................
....................
....................  (120 total: bucket full)
XXXXXXXXXXXXXXXXXXXX  (Next 30: all 429 blocked)
XXXXXXXXXX

Final count:
  200 OK: ~120
  429 Blocked: ~30
  Other: 0
```

---

## 📝 Post-Deployment Tasks

### Immediate (Today)
- [ ] Run deployment script: `.\scripts\deploy_capacity_controls.ps1`
- [ ] Verify all acceptance criteria pass
- [ ] Import Grafana dashboard
- [ ] Configure 4 alerts
- [ ] Git commit changes

### This Week
- [ ] Run llama.cpp benchmark with 3 flag sets
- [ ] Document optimal flags in wiki/README
- [ ] Monitor alerts for false positives
- [ ] Schedule backup task (Windows Task Scheduler)
- [ ] Baseline load test (20 rps, 10min)

### Next Week (Directive 002)
- [ ] Implement SSE streaming endpoint
- [ ] Health drill-down (DB/LLM/ChromaDB status)
- [ ] Operator console planning
- [ ] Phase 1 gate criteria check

---

## 🎉 Success Declaration

**Directive 001 is COMPLETE when:**

✅ All acceptance criteria pass  
✅ Grafana dashboard imported + alerts configured  
✅ Burst test shows expected allow/block pattern  
✅ No 5xx errors during testing  
✅ llama.cpp benchmark baseline documented  
✅ Git commit pushed  
✅ Team walkthrough completed  

---

## 📚 Reference Documentation

| Document | Purpose |
|----------|---------|
| `CAPACITY_MANAGEMENT_GUIDE.md` | Full deployment guide with runbook |
| `CAPACITY_IMPLEMENTATION_SUMMARY.md` | Quick reference card |
| `ROADMAP_A_TO_Z.md` | Full A→Z roadmap with phases |
| `scripts/deploy_capacity_controls.ps1` | Automated deployment script |
| `tests/unit/test_per_key_limiter.py` | 6 unit tests for limiter |
| `tests/unit/test_queue_metrics.py` | 6 unit tests for metrics |

---

## 🚦 Next Directive

**Directive 002: SSE Streaming (Planned for Week 2)**
- Endpoint: `POST /v1/chat/stream`
- Response: `text/event-stream`
- Perceived latency improvement
- Real-time token delivery

**Directive 003: Chaos Drill (Week 2)**
- Simulate LLM timeout
- Validate circuit breaker
- Prove graceful degradation
- No 5xx crashes

---

**Status:** ✅ READY TO EXECUTE  
**Estimated Time:** 30-45 minutes  
**Next Action:** Run `.\scripts\deploy_capacity_controls.ps1`

🚀 **Let's ship it!**
