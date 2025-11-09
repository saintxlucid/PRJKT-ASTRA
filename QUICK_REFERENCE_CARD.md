# 🚀 ASTRA CORE v1.0.0 - QUICK REFERENCE CARD
**PRINT & POST NEAR WORKSTATION**

---

## 🟢 SYSTEM STATUS
```
✅ LLM Server:  http://127.0.0.1:8001
✅ API Server:  http://127.0.0.1:8080
✅ Health:      /v1/system/health
✅ Metrics:     /metrics
```

---

## 📊 30-MIN WATCH (Day-0)
```powershell
.\scripts\day0_watch.ps1     # Every 5-10 minutes
```

---

## 🎯 GOLDEN SIGNALS
- **p95:** ≤ 1.2s
- **p99:** ≤ 2.0s  
- **Cache:** 10% → 25-40%
- **Errors:** < 1%
- **Breaker:** CLOSED

---

## 🔖 TAG RELEASE (After 30min)
```powershell
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 – Production Ready"
git push origin v1.0.0
```

---

## 🚨 FAST TRIAGE

| Issue | Quick Fix |
|-------|-----------|
| **High latency** | Edit ship.ps1: `$Ctx = 65536` |
| **Low cache** | Edit .env: `CACHE_TTL_SECONDS=900` |
| **503 errors** | Check llama process, restart |
| **Disk full** | Run `wal_checkpoint.py` |

**Instant Rollback:**
```powershell
.\scripts\stop.ps1
git checkout v0.9.x
.\scripts\ship.ps1
```

---

## 📅 ROADMAP
- **T+30min:** Tag v1.0.0
- **Day-1:** Fix 3 tests → 49/49
- **Day-2:** Schedule WAL checkpoint
- **Days 3-7:** BGE-M3 A/B test
- **Week-2:** PII redaction, cache tuning
- **Month-1:** Full Phase-2 features

---

## 📞 QUICK COMMANDS
```powershell
# Health check
.\scripts\day0_watch.ps1

# Watch logs
Get-Content .\data\logs\astra.log -Wait

# Check metrics
curl http://127.0.0.1:8080/metrics

# Restart
.\scripts\stop.ps1
.\scripts\ship.ps1
```

---

## 📚 DOCS
- **LAUNCH_SUCCESS.md** - Full launch summary
- **POST_LAUNCH_ROADMAP.md** - 48h → Month-1 plan  
- **TRIAGE_CHEATSHEET.md** - Detailed troubleshooting
- **GO_LIVE_CHECKLIST.md** - Complete acceptance criteria

---

## 🎉 STATUS: PRODUCTION READY
**Launch Date:** October 16, 2025  
**Version:** v1.0.0  
**Uptime Target:** > 99%

**CONGRATULATIONS! ASTRA IS LIVE! 🚀**
