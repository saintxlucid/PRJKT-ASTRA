# 🎯 GO-LIVE FINAL ACTIONS - 5 MINUTE CHECKLIST

**Date:** October 16, 2025  
**Target:** ASTRA Core v1.0.0 Production Launch  
**Status:** 🟡 3 ACTIONS REQUIRED BEFORE LAUNCH

---

## ✅ QUICK STATUS CHECK

| Item | Status | Action |
|------|--------|--------|
| `.env` protection | ✅ Verified (.gitignore) | - |
| Encryption key | ✅ Valid Fernet | - |
| API key | ⚠️ **PLACEHOLDER** | **Run fix_api_key.ps1** |
| ship.ps1 paths | ⚠️ **TEMPLATE PATHS** | **Edit lines 13-14** |
| Ports 8001/8080 | ✅ Free | - |
| Prometheus alerts | ✅ Configured (10 rules) | - |
| Model checksum | ⏳ **NOT GENERATED** | **Run verify_model.ps1** |

---

## 🚨 3 REQUIRED ACTIONS

### Action 1: Generate API Key (30 seconds)

```powershell
.\scripts\fix_api_key.ps1
```

**Expected Output:**
```
✅ Generated crypto-secure API key
✅ Updated .env with new key
✅ Set .env permissions (user-only)
API key: xK9mPQ...*** (preview)
```

**Verify:**
```powershell
Get-Content .env | Select-String "ASTRA_API_KEYS"
# Should NOT show "your-generated-api-key-here"
```

---

### Action 2: Update ship.ps1 Paths (1 minute)

```powershell
notepad .\scripts\ship.ps1
```

**Edit Lines 13-14:**
```powershell
# BEFORE (template):
$LlamaExe   = "C:\llama\llama-server.exe"
$ModelPath  = "C:\models\gpt-oss-20b-q4_k_m.gguf"

# AFTER (your actual paths):
$LlamaExe   = "X:\llama.cpp\build\bin\Release\llama-server.exe"
$ModelPath  = "X:\PROJECT_ASTRA\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"
```

**From Your .env:**
- Model path: `ASTRA_GPTOSS_MODEL_PATH=X:/PROJECT_ASTRA/astra-local/data/models/gpt-oss-20b.Q4_K_M.gguf`

**Verify Line 16:**
```powershell
$HostBind   = "127.0.0.1"  # ✅ MUST BE 127.0.0.1 (secure localhost)
```

**Save and Close**

---

### Action 3: Generate Model Checksum (30 seconds)

```powershell
.\scripts\verify_model.ps1 -Generate
```

**Expected Output:**
```
Generating SHA-256 checksum...
Model: X:\...\gpt-oss-20b.Q4_K_M.gguf (12.8 GB)
Checksum: abc123...def456
✅ Saved to: models\checksums.txt
```

---

## 🚀 LAUNCH SEQUENCE (After 3 Actions Complete)

### Step 1: Dry-Run Validation (30 seconds)

```powershell
.\scripts\finalize_and_ship.ps1 -DryRun
```

**Must Show:**
```
========================================
Preflight Checks: 10/10 PASSED ✅
========================================
[i] Dry-run complete. No changes made.
```

**If Any Checks Fail:**
- Go back and complete missing actions
- Verify paths are correct
- Check ports are free

---

### Step 2: Production Deploy (2 minutes)

```powershell
.\scripts\finalize_and_ship.ps1
```

**Expected Workflow:**
1. ✅ Backup created
2. ✅ Preflight 10/10
3. ✅ llama-server started (port 8001)
4. ✅ ASTRA API started (port 8080)
5. ✅ Health checks pass
6. ✅ Smoke tests: 5/5

**Success Output:**
```
========================================
DEPLOYMENT SUMMARY
========================================
✅ LLM Server: http://127.0.0.1:8001
✅ ASTRA API:  http://127.0.0.1:8080
✅ Bridge:     /v1/bridge/healthz
✅ Smoke Tests: 5/5 PASSED
========================================
```

---

### Step 3: Tag Version (30 seconds)

```powershell
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 – Production Ready"
git push origin v1.0.0  # If using remote
```

---

## 📊 DAY-0 MONITORING (First 30 Minutes)

**Every 5 Minutes:**

```powershell
# 1. Health check
curl http://127.0.0.1:8080/v1/system/health

# 2. Check latency (target: p95 ≤ 1.2s)
curl http://127.0.0.1:8080/metrics | Select-String "astra_llm_latency.*0.95"

# 3. Check cache (10-15% is NORMAL cold start)
curl http://127.0.0.1:8080/metrics | Select-String "astra_cache"

# 4. Tail logs (look for ERROR/CRITICAL)
Get-Content data\logs\astra.log -Wait -Tail 20
```

**Expected Cache Progression:**
- T+0 to T+10min: **10-15%** (cold start, NORMAL ✅)
- T+10 to T+30min: **15-20%** (warming)
- T+30 to T+60min: **20-25%** (typical)
- End of Day-1: **30-40%** (production)

---

## 🔄 QUICK ROLLBACK (If Needed)

```powershell
.\scripts\stop.ps1
git checkout v0.9.x
.\scripts\ship.ps1
```

**Rollback Triggers:**
- ❌ Error rate > 10%
- ❌ p95 latency > 2.0s sustained
- ❌ Circuit breaker constantly OPEN
- ❌ Critical errors in logs

---

## 📋 COMPLETE CHECKLIST

### Pre-Launch Actions
- [ ] Run `.\scripts\fix_api_key.ps1`
- [ ] Edit `.\scripts\ship.ps1` lines 13-14
- [ ] Run `.\scripts\verify_model.ps1 -Generate`
- [ ] Run `.\scripts\finalize_and_ship.ps1 -DryRun` (must pass 10/10)

### Launch Actions
- [ ] Run `.\scripts\finalize_and_ship.ps1`
- [ ] Verify health checks pass
- [ ] Verify smoke tests: 5/5
- [ ] Create git tag: `v1.0.0`

### Post-Launch Actions
- [ ] Monitor for 30 minutes
- [ ] Verify p95 ≤ 1.2s
- [ ] Verify cache warming (10-15% → 25%+)
- [ ] Check logs for errors

---

## 📞 QUICK REFERENCE

**Full Documentation:**
- `GO_LIVE_CHECKLIST.md` - Complete checklist (this expanded version)
- `ASTRA_CORE_FULL_ANALYSIS.md` - Technical deep-dive (1500+ lines)
- `ops/RUNBOOK.md` - Operations guide

**Scripts:**
- `fix_api_key.ps1` - Generate API key
- `verify_model.ps1` - Model integrity
- `finalize_and_ship.ps1` - Deploy automation
- `ship.ps1` - Quick launch
- `stop.ps1` - Graceful shutdown
- `smoke_test.ps1` - 5-test validation

**Endpoints:**
- Health: `http://127.0.0.1:8080/v1/system/health`
- Bridge: `http://127.0.0.1:8080/v1/bridge/healthz`
- Metrics: `http://127.0.0.1:8080/metrics`

---

**Total Time to Production:** ~5 minutes  
**Monitoring Window:** 30 minutes  
**Status:** 🟡 **3 ACTIONS → 🟢 LAUNCH READY**

---

## 🎯 RIGHT NOW - DO THIS:

```powershell
# Step 1: API Key (30 sec)
.\scripts\fix_api_key.ps1

# Step 2: Edit Paths (1 min)
notepad .\scripts\ship.ps1
# Update lines 13-14 with your paths
# Save and close

# Step 3: Checksum (30 sec)
.\scripts\verify_model.ps1 -Generate

# Step 4: Dry-Run (30 sec)
.\scripts\finalize_and_ship.ps1 -DryRun

# Step 5: LAUNCH (2 min)
.\scripts\finalize_and_ship.ps1

# Step 6: Tag (30 sec)
git tag -a v1.0.0 -m "Production Ready"

# Step 7: Monitor (30 min)
# Watch health, metrics, logs
```

**After these steps: ASTRA Core v1.0.0 is LIVE! 🚀**
