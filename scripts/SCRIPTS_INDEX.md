# ASTRA Scripts - Quick Reference

## 🚀 ONE-SHOT DEPLOYMENT

### `ship.ps1` ⭐ NEW - Complete Launch & Validation
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```
**Does everything:** Starts LLM + API, waits for ready, validates Bridge, runs smoke tests

**Configure:** Edit top of file for paths:
- `$LlamaExe` = Path to llama-server.exe
- `$ModelPath` = Path to your .gguf model
- `$Ctx` = 131072 (or 65536 if OOM)
- `$GpuLayers` = 0 (set >0 for CUDA)

---

## 🛑 STOP SERVICES

### `stop.ps1` - Stop All
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop.ps1
```
Stops llama-server, uvicorn, python processes

---

## ✅ TESTING

### `smoke_test.ps1` - 5-Test Quick Validation
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1
```
Tests: LLM health, API health, Bridge, Metrics, Chat completion

### `loadtest_baseline.js` - k6 Load Test (NEW)
```bash
k6 run scripts/loadtest_baseline.js
```
**Install k6:** https://k6.io/docs/getting-started/installation/  
**Stages:** Warmup (5 VU) → Baseline (10 VU) → Spike (20 VU)  
**Thresholds:** p95 < 1.2s, p99 < 2s, errors < 5%

---

## 📊 DEPLOYMENT & MONITORING

### `deploy_go_nogo.ps1` - 7-Check Verification
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_go_nogo.ps1
```
Checks: LLM, API, Bridge, DB, Metrics, Config, Tests → GO or NO-GO decision

### `monitor_golden_signals.ps1` - 30-Min Watch
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\monitor_golden_signals.ps1
```
Monitors: Requests, LLM failures, Cache hits, Health, Errors

---

## 🗄️ DATABASE & CLEANUP

### `cleanup_disk_for_bgem3.ps1` - Free 2-3 GB
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cleanup_disk_for_bgem3.ps1
```
Cleans: Temp files, pip cache, HuggingFace temp, project caches

### `reembed_bge_m3.ps1` - Upgrade Embeddings
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reembed_bge_m3.ps1
```
Upgrades 21K+ memories from 384d → 1536d (optional, ~20 min)

---

## 📋 DEPLOYMENT WORKFLOW

**First Time:**
1. `ship.ps1` → Starts everything
2. `deploy_go_nogo.ps1` → Full validation
3. `monitor_golden_signals.ps1` → Watch 30 min
4. `k6 run loadtest_baseline.js` → Baseline performance

**Daily:**
1. `ship.ps1` → Start
2. `smoke_test.ps1` → Validate
3. `stop.ps1` → Shutdown

---

## 🔧 TROUBLESHOOTING

**Port in use:**
```powershell
netstat -ano | findstr ":8001 :8080"
Stop-Process -Id <PID> -Force
```

**OOM on LLM:**
Edit `ship.ps1`: `$Ctx = 65536` or `$GpuLayers = 35`

**Encoding errors:**
Add to script: `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`

---

## 🎯 SUCCESS CRITERIA

- ✅ ship.ps1 completes
- ✅ Smoke test 5/5 GREEN
- ✅ Golden signals 30 min OK
- ✅ k6 load test p95 < 1.2s

---

**See also:**
- Full scripts docs: `scripts/README.md` (existing)
- Deployment guide: `DEPLOYMENT_READY_FINAL.md`
- Operations runbook: `ops/RUNBOOK.md`
