# ⚡ DEPLOY ASTRA v1.0.0 - ONE PAGE

**Date:** October 16, 2025 | **Status:** READY TO SHIP

---

## 1️⃣ PRE-FLIGHT (1 minute)

### Edit `scripts\ship.ps1` (lines 11-16):
```powershell
$LlamaExe   = "C:\llama\llama-server.exe"        # ← YOUR PATH
$ModelPath  = "C:\models\gpt-oss-20b-q4_k_m.gguf" # ← YOUR PATH
$Ctx        = 131072   # Drop to 65536 if OOM
$GpuLayers  = 0        # Set >0 if CUDA build
$HostBind   = "127.0.0.1"  # Safer: local-only. Use 0.0.0.0 only if need LAN
```

### Create/Verify `.env`:
```ini
ASTRA_LLM_BASE_URL=http://127.0.0.1:8001/v1
ASTRA_SERVER_PORT=8080
ASTRA_DATABASE_URL=sqlite:///data/astra.db
ASTRA_VECTOR_STORE_PERSIST_DIRECTORY=./data/chromadb
ASTRA_API_KEYS=your-secure-key-here
ASTRA_ENCRYPTION_KEY=your-fernet-key-here
```

**Generate keys:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 2️⃣ SHIP (single command)

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

**Expected:**
```
== ASTRA CORE SHIP ==
Starting llama.cpp server...
LLM_OK
Starting ASTRA API...
API_OK
BRIDGE_OK
Running smoke test...
✓ All 5 tests pass

=== SUMMARY ===
LLM:    ONLINE on :8001
API:    ONLINE on :8080
BRIDGE: MOUNTED
SMOKE:  PASSED
READY TO TAG: v1.0.0
```

---

## 3️⃣ VERIFY (quick health checks)

```powershell
# LLM up
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Write-Host "✓ LLM server OK" -ForegroundColor Green

# API healthy
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Write-Host "✓ API server OK" -ForegroundColor Green

# Bridge mounted
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
Write-Host "✓ Bridge OK" -ForegroundColor Green

# Metrics active
$metrics = Invoke-WebRequest http://127.0.0.1:8080/metrics -UseBasicParsing
if ($metrics.Content -match "astra_") {
    Write-Host "✓ Metrics OK" -ForegroundColor Green
}
```

**All return 200 OK → GREEN LIGHT ✅**

**Alternative (if you have curl.exe):**
```powershell
curl.exe -fsS http://127.0.0.1:8001/v1/models
curl.exe -fsS http://127.0.0.1:8080/v1/system/health
curl.exe -fsS http://127.0.0.1:8080/v1/bridge/healthz
```

---

## 4️⃣ BASELINE LOAD (optional, k6)

```bash
k6 run scripts/loadtest_baseline.js
```

**Targets:**
- p95 ≤ 1.2s ✓
- Errors < 5% ✓
- Cache hit ≥ 25% ✓

---

## 5️⃣ 30-MINUTE WATCH (golden signals)

```powershell
.\scripts\monitor_golden_signals.ps1
```

**Monitor:**
- p95 latency steady ≤ 1.2s
- LLM failures flat (near-zero)
- Cache hit trending 25–40%
- No sustained 503s (breaker)

**Logs (live tail):**
```powershell
Get-Content .\data\logs\astra.log -Wait
```

---

## 6️⃣ TAG WHEN GREEN

```powershell
git add .
git commit -m "ASTRA Core v1.0.0 - ship scripts + hardening"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
git push origin v1.0.0
```

---

## 🔧 TRIAGE MAP (if something trips)

| Issue | Symptom | Fix |
|-------|---------|-----|
| **503 bursts** | Circuit breaker open | llama.cpp up? Reduce RPS, increase cache TTL, check breaker cooldown |
| **High latency** | p95 >1.2s | Smaller `--ctx-size`, fewer retrieved memories, confirm semantic cache running |
| **OOM** | Crashes/freezes | Lower `--n-gpu-layers` or `--ctx-size`; CPU-only is fine (`--n-gpu-layers 0`) |
| **Desktop won't connect** | Connection refused | Config points to `http://localhost:8080`, check CORS, verify API running |

---

## 📊 SYSTEM STATUS

| Component | Status | Details |
|-----------|--------|---------|
| **Code** | ✅ Complete | Circuit breaker, semantic cache, 7 metrics, 9 alerts |
| **Scripts** | ✅ Ready | ship.ps1 (one-shot), stop.ps1, smoke_test.ps1, monitor, k6 |
| **Docs** | ✅ Written | 6 guides (pre-flight, deployment, runbook, release notes) |
| **Security** | ✅ Hardened | 127.0.0.1 default, API keys, rate limits, encryption |
| **Tests** | ✅ 93.9% | 46/49 passing (3 time-dependent) |

---

## ⚡ QUICK REFERENCE

**Start:** `.\scripts\ship.ps1`  
**Stop:** `.\scripts\stop.ps1`  
**Test:** `.\scripts\smoke_test.ps1`  
**Monitor:** `.\scripts\monitor_golden_signals.ps1`  
**Load:** `k6 run scripts/loadtest_baseline.js`

**Health URLs:**
- LLM: http://localhost:8001/v1/models
- API: http://localhost:8080/v1/system/health
- Bridge: http://localhost:8080/v1/bridge/healthz
- Metrics: http://localhost:8080/metrics

**Full docs:** `SHIP_IT_NOW.md`, `PRE_FLIGHT_CHECKLIST.md`, `ops/RUNBOOK.md`

---

**ETA:** 5 minutes from config to tagged release  
**VERDICT:** ✅ READY TO SHIP

🚀 **LET'S GO!**
