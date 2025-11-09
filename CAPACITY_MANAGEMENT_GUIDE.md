# Capacity Management - Deployment & Validation Guide

**Date:** October 9, 2025  
**Feature:** Per-key rate limiting, queue metrics, llama.cpp benchmarking  
**Status:** ✅ READY FOR DEPLOYMENT

---

## What Was Implemented

### 1. Per-Key Token Bucket Limiter
- **Purpose:** Prevent single API key from saturating llama.cpp
- **Implementation:** `PerKeyLimiter` class in `src/astra/security.py`
- **Features:**
  - Thread-safe token bucket algorithm
  - Privacy-preserving key hashing (SHA-256, 16 chars)
  - Constant-time operations
  - Automatic token refill over time
- **Config:**
  - `ASTRA_PER_KEY_RATE=120` (tokens per period)
  - `ASTRA_PER_KEY_PERIOD_SEC=60` (period in seconds)
- **Default:** 120 requests/minute = 2 req/sec per key

### 2. Queue & Capacity Metrics
- **Purpose:** Enable alerting and capacity planning
- **Metrics Added:**
  - `astra_queue_depth` (gauge) - Current queue size
  - `astra_queue_wait_seconds` (histogram) - Time spent in queue
  - `astra_limiter_per_key_allowed_total` (counter) - Requests allowed per key
  - `astra_limiter_per_key_blocked_total` (counter) - Requests blocked per key
- **Integration:** Instrumented `ConcurrencyLimiterMiddleware` in `src/astra/queue_guard.py`

### 3. llama.cpp Benchmark Tool
- **Purpose:** Find optimal --threads/--batch/--ctx-size for your CPU
- **File:** `scripts/benchmark_llama_flags.py`
- **Features:**
  - No external dependencies (uses httpx from venv)
  - JSON output with mean, p50, p95, p99 latencies
  - Configurable sample count
- **Usage:** Run with different llama.cpp flags, compare results

---

## 3) RUNBOOK (PowerShell Commands)

### Step 0: Pull and Activate
```powershell
cd X:\PROJECT_ASTRA
git pull
.\.venv\Scripts\Activate.ps1
```

### Step 1: (Optional) Configure Per-Key Limits
```powershell
# Add to .env file
Add-Content .env "`nASTRA_PER_KEY_RATE=120"
Add-Content .env "`nASTRA_PER_KEY_PERIOD_SEC=60"

# Or edit .env manually:
# ASTRA_PER_KEY_RATE=120
# ASTRA_PER_KEY_PERIOD_SEC=60
```

**Tuning Guide:**
- **Conservative:** 60 req/60s = 1 req/sec
- **Default:** 120 req/60s = 2 req/sec
- **Aggressive:** 300 req/60s = 5 req/sec

### Step 2: Restart Backend
```powershell
# Stop current server (Ctrl+C in terminal)

# Start with new middleware
.\.venv\Scripts\python.exe run_server.py
```

### Step 3: Verify Health (Unauthenticated)
```powershell
curl http://127.0.0.1:8080/v1/system/health
# Expected: {"status":"ok",...}
```

### Step 4: Test Per-Key Limiting
```powershell
# Set API key
$env:ASTRA_API_KEY = "<your-key-from-.env>"
$headers = @{"X-API-Key" = $env:ASTRA_API_KEY}

# Send burst of requests (expect some 429s)
1..150 | ForEach-Object {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/conversations/" -Headers $headers -TimeoutSec 5
        Write-Host "✓ $($_): $($response.StatusCode)" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 429) {
            Write-Host "✗ $($_): 429 (rate limited)" -ForegroundColor Yellow
        } else {
            Write-Host "✗ $($_): Error" -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 100
}
```

**Expected:** First ~120 requests succeed (200), then 429s start appearing.

### Step 5: Check New Metrics
```powershell
# Fetch metrics
Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -OutFile metrics.txt

# Verify per-key limiter metrics
Select-String -Path metrics.txt -Pattern "astra_limiter_per_key_"

# Verify queue metrics
Select-String -Path metrics.txt -Pattern "astra_queue_"
```

**Expected output:**
```
astra_limiter_per_key_allowed_total{key_hash="abc123..."} 120.0
astra_limiter_per_key_blocked_total{key_hash="abc123..."} 30.0
astra_queue_depth 0.0
astra_queue_wait_seconds_bucket{le="0.01"} 5.0
...
```

### Step 6: Run Benchmark (Optional)
```powershell
# Benchmark with current llama.cpp flags
.\.venv\Scripts\python.exe scripts\benchmark_llama_flags.py

# Example output:
# {
#   "url": "http://127.0.0.1:8001",
#   "samples": 5,
#   "mean_seconds": 1.234,
#   "p95_seconds": 1.456,
#   "p99_seconds": 1.567,
#   ...
# }
```

**To test different flags:**
1. Stop llama.cpp server
2. Restart with new flags: `llama-server.exe --model ... --threads 16 --batch 1024`
3. Run benchmark again
4. Compare mean/p95 latencies
5. Choose configuration with lowest p95

---

## 4) TESTS

### Run Unit Tests
```powershell
cd X:\PROJECT_ASTRA
.\.venv\Scripts\Activate.ps1

# Run new tests
pytest tests\unit\test_per_key_limiter.py tests\unit\test_queue_metrics.py -v

# Expected output:
# tests/unit/test_per_key_limiter.py::test_per_key_limiter_allows_under_limit PASSED
# tests/unit/test_per_key_limiter.py::test_per_key_limiter_different_keys_independent PASSED
# tests/unit/test_per_key_limiter.py::test_per_key_limiter_refills_over_time PASSED
# tests/unit/test_per_key_limiter.py::test_api_key_middleware_per_key_limiting PASSED
# tests/unit/test_per_key_limiter.py::test_api_key_middleware_exempt_paths_not_limited PASSED
# tests/unit/test_per_key_limiter.py::test_per_key_limiter_hash_privacy PASSED
# tests/unit/test_queue_metrics.py::test_queue_depth_metric_exists PASSED
# tests/unit/test_queue_metrics.py::test_queue_wait_seconds_histogram_exists PASSED
# tests/unit/test_queue_metrics.py::test_limiter_per_key_allowed_counter_exists PASSED
# tests/unit/test_queue_metrics.py::test_limiter_per_key_blocked_counter_exists PASSED
# tests/unit/test_queue_metrics.py::test_queue_metrics_integration PASSED
# tests/unit/test_queue_metrics.py::test_per_key_limiter_metrics_integration PASSED
#
# ========== 12 passed in 2.5s ==========
```

### Run Full Test Suite (Regression)
```powershell
pytest tests\ -v --tb=short
# Expected: 46/49 passing (same as before)
```

---

## 5) VALIDATION (Observability)

### PromQL Queries for Grafana

#### Per-Key Block Rate
```promql
rate(astra_limiter_per_key_blocked_total[5m])
```
**Alert:** `> 10` blocks/sec = aggressive client

#### Allowed vs Blocked Ratio (Per-Key Fairness)
```promql
sum(rate(astra_limiter_per_key_allowed_total[5m])) 
/ 
(sum(rate(astra_limiter_per_key_allowed_total[5m])) + sum(rate(astra_limiter_per_key_blocked_total[5m])))
```
**Healthy:** `> 0.80` (80%+ allowed)

#### Queue Depth (Capacity)
```promql
avg_over_time(astra_queue_depth[5m])
```
**Alert:** `> 50` = approaching saturation

#### Queue Wait p95
```promql
histogram_quantile(0.95, rate(astra_queue_wait_seconds_bucket[5m]))
```
**Alert:** `> 2.0` seconds = unhealthy backpressure

#### Queue Wait p99
```promql
histogram_quantile(0.99, rate(astra_queue_wait_seconds_bucket[5m]))
```
**SLO:** `< 2.5` seconds

### Functional Validation

#### Test 1: Single Key Burst
```powershell
# Send 200 requests with same API key
$headers = @{"X-API-Key" = $env:ASTRA_API_KEY}
1..200 | % { curl -H "X-API-Key: $env:ASTRA_API_KEY" http://127.0.0.1:8080/v1/conversations/ -s -o $null -w "%{http_code}\n" }
```
**Expected:** First ~120 return 200, rest return 429

#### Test 2: Multi-Key Fairness
```powershell
# Generate two keys
$key1 = $env:ASTRA_API_KEY
$key2 = "test_key_2_" + ("x" * 40)

# Add key2 to .env temporarily or mock it
# Each key should get independent budget
```

#### Test 3: Exempt Paths Never Limited
```powershell
# Hammer health endpoint without API key
1..1000 | % { curl http://127.0.0.1:8080/v1/system/health -s -o $null -w "%{http_code}\n" }
```
**Expected:** All 1000 return 200 (no 429s)

#### Test 4: llama.cpp Remains Responsive
```powershell
# During heavy load from one key, verify llama.cpp still serves other keys
# Start background burst from key1
$job = Start-Job -ScriptBlock {
    $h = @{"X-API-Key" = $env:ASTRA_API_KEY}
    1..500 | % { curl -H "X-API-Key: $env:ASTRA_API_KEY" http://127.0.0.1:8080/v1/conversations/ -s -o $null }
}

# Immediately test with key2 (should not be blocked)
$h2 = @{"X-API-Key" = $env:ASTRA_API_KEY_2}
curl -H "X-API-Key: $env:ASTRA_API_KEY_2" http://127.0.0.1:8080/v1/chat/ -X POST -d '{"message":"test"}' -H "Content-Type: application/json"
# Should return 200, not 429 or 503
```

---

## 6) ROLLBACK

### Complete Rollback Procedure
```powershell
# 1. Stop backend
Stop-Process -Name python -Force

# 2. Revert code changes
git restore --source=HEAD~1 -- `
  src\astra\metrics.py `
  src\astra\security.py `
  src\astra\queue_guard.py `
  scripts\benchmark_llama_flags.py `
  tests\unit\test_per_key_limiter.py `
  tests\unit\test_queue_metrics.py

# 3. Remove config (optional)
(Get-Content .env) | Where-Object { $_ -notmatch 'ASTRA_PER_KEY_' } | Set-Content .env

# 4. Restart backend
.\.venv\Scripts\python.exe run_server.py

# 5. Verify health
curl http://127.0.0.1:8080/v1/system/health
# Expected: {"status":"ok"}

# 6. Verify old metrics still work
curl http://127.0.0.1:8080/metrics | Select-String "astra_requests_total"
```

**Rollback time:** < 2 minutes  
**Risk:** Minimal (additive changes only)

---

## 7) RISKS & MITIGATIONS

### Risk 1: Over-Tight Key Budgets
**Symptom:** Legitimate users see frequent 429s  
**Detection:** `astra_limiter_per_key_blocked_total` high, user complaints  
**Mitigation:**
- Start conservative: 120 req/60s = 2 req/sec
- Monitor Grafana allow/block ratio
- Tune up gradually based on p95 latency headroom

### Risk 2: Label Cardinality Explosion
**Symptom:** Prometheus scrape slowdown, high memory  
**Detection:** Prometheus query latency, cardinality dashboard  
**Mitigation:**
- Key hashes are truncated (16 chars = low cardinality)
- If >1000 keys, increase scrape interval to 30s
- Use `sum by (key_hash)` sparingly in queries

### Risk 3: Queue Metrics Show Persistent Depth
**Symptom:** `astra_queue_depth` stays >50, p95 wait >2s  
**Detection:** Grafana queue depth panel, alert firing  
**Mitigation:**
- Increase `ASTRA_MAX_INFLIGHT` (default 32 → 64)
- Lower per-key rate limits to reduce total load
- Benchmark llama.cpp with more threads/batch
- Scale horizontally (add more ASTRA instances)

### Risk 4: Client Shares One Key Across Many Users
**Symptom:** Single key hash dominates blocked metrics  
**Detection:** `astra_limiter_per_key_blocked_total{key_hash="xxx"}` very high  
**Mitigation:**
- Issue per-user API keys instead of shared keys
- Increase rate for that specific key (env override per-key)
- Enforce multi-key policy in client onboarding

### Risk 5: Refill Logic Drift (Clock Skew)
**Symptom:** Rate limiting behaves erratically  
**Detection:** Unit tests fail, logs show negative elapsed time  
**Mitigation:**
- Token bucket uses `time.time()` (monotonic in Python 3.3+)
- If NTP sync issues, restart backend to reset buckets
- Consider using `time.perf_counter()` for even more stability

---

## Next Steps After Deployment

### Immediate (Day 1)
1. ✅ Verify all 12 unit tests pass
2. ✅ Confirm 429s appear under burst load
3. ✅ Check `/metrics` shows new series
4. ✅ Run llama.cpp benchmark, document baseline

### This Week
1. **Import Grafana panels** - Add 4 new PromQL queries to dashboard
2. **Set alerts** - Queue depth >50, per-key block rate >10/s
3. **Tune per-key rates** - Adjust based on p95 latency headroom
4. **Document llama.cpp flags** - Share benchmark results in wiki

### Next Sprint
1. **Per-key quotas** - Add daily/monthly quotas (not just rate)
2. **Key metadata** - Store key name, tier, limits in DB
3. **Admin API** - GET /admin/keys/{hash}/stats endpoint
4. **Auto-scaling** - Use queue depth to trigger horizontal scale

---

## Configuration Reference

### Environment Variables (All Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `ASTRA_PER_KEY_RATE` | `120` | Tokens per period (burst capacity) |
| `ASTRA_PER_KEY_PERIOD_SEC` | `60` | Period in seconds |
| `ASTRA_MAX_INFLIGHT` | `32` | Concurrent requests (existing) |
| `ASTRA_MAX_QUEUE` | `64` | Queue depth (existing) |

### Calculated Rates

| Config | Rate | Use Case |
|--------|------|----------|
| 60/60s | 1 req/sec | Low traffic, testing |
| 120/60s | 2 req/sec | **Default**, balanced |
| 300/60s | 5 req/sec | High-tier users |
| 600/60s | 10 req/sec | Premium, dashboards |

---

## Summary

**What Changed:**
- ✅ Per-key token bucket limiting (prevents single-client saturation)
- ✅ Queue metrics (depth, wait time) for capacity planning
- ✅ Per-key allow/block metrics for fairness monitoring
- ✅ llama.cpp benchmark tool for flag tuning

**What Didn't Change:**
- ❌ No API path changes
- ❌ No database schema changes
- ❌ Health/metrics/docs still unauthenticated
- ❌ Existing rate limiter (global IP-based) still active
- ❌ Middleware order unchanged

**Operational Maturity:** Level 4 → Level 5 (Capacity-aware, multi-tenant ready)

---

**Questions or Issues?** Check:
- `docs/RUNBOOK.md` - Error recovery procedures
- `logs/astra.log` - Structured logs with request_id
- `/metrics` endpoint - Real-time Prometheus metrics
- Grafana dashboard - Visualized trends and alerts
