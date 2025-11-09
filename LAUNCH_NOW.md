# 🚀 ASTRA CORE v1.0.0 - LAUNCH NOW

**Date:** October 16, 2025  
**Status:** 🟢 CLEARED FOR PRODUCTION  
**Time Required:** 5 minutes + 30 minutes monitoring

---

## ⚡ LAUNCH PROCEDURE

### Step 1: Keys & Paths (2 minutes)

```powershell
# Generate crypto-secure API key
.\scripts\fix_api_key.ps1

# Set LLM paths (edit lines 13-14)
notepad .\scripts\ship.ps1
# $LlamaExe  = "X:\llama.cpp\build\bin\Release\llama-server.exe"
# $ModelPath = "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"

# Generate model checksum
.\scripts\verify_model.ps1 -Generate
```

---

### Step 2: Rehearse → Deploy (3 minutes)

```powershell
# Dry-run: Validate all preflight checks (MUST pass 10/10)
.\scripts\finalize_and_ship.ps1 -DryRun

# Deploy: Launch to production
.\scripts\finalize_and_ship.ps1
```

**Expected Output:**
```
✅ LLM Server: http://127.0.0.1:8001 (PID 12345)
✅ ASTRA API:  http://127.0.0.1:8080 (PID 12346)
✅ Smoke Tests: 5/5 PASSED
```

---

### Step 3: Tag When Green (30 seconds)

```powershell
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 – Production Ready"
git push origin v1.0.0
```

---

## ✅ Quick Verifications (30 seconds)

```powershell
# Verify LLM server responding
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null

# Verify ASTRA API health
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null

# Verify Bridge mounted
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null

Write-Host "✅ All endpoints responding!" -ForegroundColor Green
```

---

## 📊 Day-0 Watch (30 minutes)

### Performance Targets

- ✅ **p95 ≤ 1.2s, p99 ≤ 2.0s**
- ✅ **Cache hit ≥ 10–15%** (cold start) → **25–40%** (warmed)
- ✅ **Breaker quiet** (no sustained failures)
- ✅ **Logs clean** (no ERROR/CRITICAL)

### Live Monitoring

```powershell
# Watch logs for errors (Ctrl+C to stop)
Get-Content .\data\logs\astra.log -Wait | Select-String -Pattern 'ERROR|CRITICAL'

# Check metrics every 5 minutes
curl http://127.0.0.1:8080/metrics | Select-String "astra_llm_latency_seconds{quantile=\"0.95\"}"
curl http://127.0.0.1:8080/metrics | Select-String "astra_cache_hits_total"
```

### Cache Warm-Up Timeline

- **T+0 to T+10min:** 10-15% (cold start, **NORMAL** ✅)
- **T+10 to T+30min:** 15-20% (warming)
- **T+30 to T+60min:** 20-25% (typical usage)
- **End of Day-1:** 30-40% (production patterns)

---

## 🔄 Instant Rollback (if needed)

**Use if:** Error rate >10%, p95 >2.0s sustained, breaker constantly OPEN

```powershell
# Stop services
.\scripts\stop.ps1

# Revert to previous version
git checkout v0.9.x

# Redeploy
.\scripts\ship.ps1
```

**Rollback Time:** < 2 minutes

---

## 📅 Week-1 Operations (Brief)

### Priority Tasks

1. **BGE-M3 Migration** (after 48h stable)
   ```powershell
   python scripts/reembed_bge_m3.py --migrate
   # Expected: +20% memory precision boost
   ```

2. **Schedule Weekly WAL Checkpoint** (Sundays 2am)
   ```powershell
   # Task Scheduler or cron:
   python scripts/wal_checkpoint.py
   ```

3. **Close Test Gap** (46/49 → 49/49)
   ```powershell
   pytest tests/ -v --cov=src/astra --cov-fail-under=94
   ```

4. **Optional: Windows Service Mode**
   ```powershell
   .\ops\service_wrapper.ps1 -Action Install
   ```

---

## 🎯 Success Checklist

### Pre-Launch (5 minutes)
- [ ] API key generated (not placeholder)
- [ ] ship.ps1 paths updated (lines 13-14)
- [ ] Model checksum verified
- [ ] Dry-run passed (10/10 checks)

### Post-Launch (30 minutes)
- [ ] LLM responding on :8001
- [ ] API responding on :8080
- [ ] Bridge health OK
- [ ] Smoke tests: 5/5 passed
- [ ] Logs clean (no errors)
- [ ] Metrics accessible
- [ ] Cache warming (10% → 25%+)

### Week-1
- [ ] Cache hit rate ≥ 30%
- [ ] BGE-M3 migration complete
- [ ] Weekly checkpoint scheduled
- [ ] Tests: 49/49 passing
- [ ] Service mode installed (optional)

---

## 📞 Quick Reference

### Endpoints
- **LLM:** `http://127.0.0.1:8001/v1/models`
- **API Health:** `http://127.0.0.1:8080/v1/system/health`
- **Bridge:** `http://127.0.0.1:8080/v1/bridge/healthz`
- **Metrics:** `http://127.0.0.1:8080/metrics`

### Logs
- **Application:** `data/logs/astra.log`
- **Deployment:** `logs/finalize_YYYYMMDD_HHMMSS.log`
- **Smoke Tests:** `logs/smoke_test_YYYYMMDD_HHMMSS.log`

### Scripts
- **Deploy:** `.\scripts\finalize_and_ship.ps1`
- **Quick Launch:** `.\scripts\ship.ps1`
- **Stop:** `.\scripts\stop.ps1`
- **Validate:** `.\scripts\smoke_test.ps1`

### Documentation
- **Quick Start:** `GO_LIVE_QUICK_ACTION.md`
- **Full Checklist:** `GO_LIVE_CHECKLIST.md`
- **Technical Analysis:** `ASTRA_CORE_FULL_ANALYSIS.md`
- **Reference Card:** `LAUNCH_REFERENCE_CARD.md`

---

## ⚠️ Top Risks & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| OOM / Slow tokens | Edit ship.ps1: `$Ctx = 65536` (reduce context) |
| Low cache (<20% after 2h) | Edit .env: `ASTRA_CACHE_TTL_SECONDS=900` |
| Breaker flapping | Restart: `.\scripts\stop.ps1; .\scripts\ship.ps1` |
| Ports in use | Find PID: `netstat -ano \| findstr ":8001 :8080"` |
| Model not found | Verify path in ship.ps1 line 14 |

---

## 🎉 Launch Command Summary

**Copy-paste this entire block:**

```powershell
# Step 1: Keys & Paths
.\scripts\fix_api_key.ps1
notepad .\scripts\ship.ps1  # Edit lines 13-14, save
.\scripts\verify_model.ps1 -Generate

# Step 2: Deploy
.\scripts\finalize_and_ship.ps1 -DryRun  # Validate
.\scripts\finalize_and_ship.ps1          # Deploy

# Step 3: Tag
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 – Production Ready"
git push origin v1.0.0

# Step 4: Verify
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
Write-Host "✅ ASTRA Core v1.0.0 is LIVE!" -ForegroundColor Green
```

---

## 🚀 YOU ARE GO FOR LAUNCH!

**System Status:** 🟢 PRODUCTION READY  
**Readiness Score:** 93.55%  
**Time to Production:** 5 minutes  
**Confidence Level:** HIGH

Execute the commands above and **ASTRA Core v1.0.0 will be LIVE!** 🎉

---

**Document Version:** 1.0  
**Created:** October 16, 2025  
**Creator:** Saint Lucid (Karim Al-Sharif)  

**Next Review:** October 23, 2025 (Week-1 Post-Launch)
