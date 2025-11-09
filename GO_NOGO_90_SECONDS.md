# 🚨 90-SECOND GO/NO-GO DEPLOYMENT CHECKLIST

**Run this immediately before deployment. ETA: 90 seconds.**

---

## 🔴 BLOCKERS FOUND - NO-GO

### ❌ CRITICAL: Missing ASTRA_API_KEYS in .env

**Issue:** `.env` file does not contain `ASTRA_API_KEYS` variable (REQUIRED for API authentication)

**Fix (30 seconds):**
```powershell
# Generate API key
python -c "import secrets; print('ASTRA_API_KEYS=' + secrets.token_urlsafe(32))"

# Copy output and add to .env file manually
# OR append directly:
python -c "import secrets; print('ASTRA_API_KEYS=' + secrets.token_urlsafe(32))" >> .env
```

**Verify:**
```powershell
Select-String -Path .env -Pattern "ASTRA_API_KEYS"
```

---

### ⚠️ WARNING: .env has ASTRA_SERVER_HOST=0.0.0.0

**Issue:** `.env` configured with `ASTRA_SERVER_HOST=0.0.0.0` (exposes API to LAN)

**Status:** ✅ **FIXED** - Changed to `127.0.0.1` (localhost-only)

**Verify:**
```powershell
Select-String -Path .env -Pattern "ASTRA_SERVER_HOST"
```

**Expected:** `ASTRA_SERVER_HOST=127.0.0.1`

---

### ⚠️ WARNING: Git not initialized

**Issue:** `git status` shows "No commits yet" - repository not initialized

**Impact:** Cannot tag v1.0.0 release until first commit made

**Fix (30 seconds):**
```powershell
git init
git add .
git commit -m "ASTRA Core v1.0.0 - Initial production release"
```

---

### ⚠️ INFO: Placeholder paths in ship.ps1

**Issue:** `scripts\ship.ps1` still has placeholder paths that need updating

**Current (lines 13-14):**
```powershell
$LlamaExe   = "C:\llama\llama-server.exe"         # <- change if different
$ModelPath  = "C:\models\gpt-oss-20b-q4_k_m.gguf"  # <- change if different
```

**Action:** Update these paths to your actual locations before running `ship.ps1`

---

## ✅ PASSING CHECKS

### ✅ .env file exists
- Location: `X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\.env`
- Size: 91 lines
- Contains: `ASTRA_ENCRYPTION_KEY` ✓

### ✅ .env excluded from git
- Created: `.gitignore` with proper exclusions
- `.env` will NOT be committed ✓
- `data/`, `*.gguf`, `models/` excluded ✓

### ✅ ship.ps1 uses consistent binding
- `$HostBind = "127.0.0.1"` (line 16) ✓
- Both LLM and API use same variable ✓
- Secure localhost-only default ✓

### ✅ Desktop configs point to localhost:8080
- `astra-desktop-simple/config.json`: `"apiUrl": "http://localhost:8080"` ✓
- `astra-os/src/config.ts`: `API_URL = "http://localhost:8080"` ✓

### ✅ Context size is sane
- ship.ps1: `$Ctx = 131072` ✓
- Fallback noted: "if OOM, try 65536" ✓

### ✅ Prometheus alerts configured
- Location: `ops/prometheus/astra_alerts.yml` ✓
- 9 base alerts + 1 cache efficiency alert ✓
- Target: Prometheus scraping `127.0.0.1:8080/metrics` ✓

### ✅ Production hardening complete
- Circuit breaker: `src/astra/infrastructure/llm/circuit_breaker.py` ✓
- Semantic cache: `src/astra/infrastructure/cache/semantic_cache.py` ✓
- Enhanced metrics: 7 new metric types ✓
- WAL checkpoint script: `scripts/wal_checkpoint.py` ✓

---

## 🎯 REQUIRED ACTIONS BEFORE GO

### 1. Add ASTRA_API_KEYS to .env (30 sec)
```powershell
python -c "import secrets; print('ASTRA_API_KEYS=' + secrets.token_urlsafe(32))" >> .env
```

### 2. Initialize git repository (30 sec)
```powershell
git init
git add .
git commit -m "ASTRA Core v1.0.0 - Initial production release"
```

### 3. Update ship.ps1 paths (30 sec)
Edit `scripts\ship.ps1` lines 13-14 with your actual paths:
```powershell
$LlamaExe   = "X:\your\actual\path\llama-server.exe"
$ModelPath  = "X:\your\actual\path\gpt-oss-20b-q4_k_m.gguf"
```

---

## 🚀 AFTER FIXES - DEPLOYMENT SEQUENCE

### Quick backup (15 sec)
```powershell
New-Item -ItemType Directory -Force -Path .\backup
Compress-Archive -Path .\.env, .\data\ -DestinationPath ".\backup\astra_pre_v1_$(Get-Date -Format yyyyMMdd_HHmmss).zip"
```

### Ship it (automated)
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

**Expected output:**
- ✅ LLM_OK (llama-server on 127.0.0.1:8001)
- ✅ API_OK (ASTRA API on 127.0.0.1:8080)
- ✅ BRIDGE_OK (/v1/bridge/healthz)
- ✅ SMOKE: 5/5 tests passing

### Tag release (30 sec)
```powershell
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 - Production Ready"
git push origin v1.0.0  # if you have remote configured
```

### Monitor golden signals (30 min)
```powershell
.\scripts\monitor_golden_signals.ps1
```

**SLO targets:**
- p95 latency ≤ 1.2s
- LLM failures flat
- Cache hit ≥ 25%
- No sustained 503s

---

## 🔒 SECURITY VERIFICATION

✅ **Binding:** 127.0.0.1 (localhost-only, no LAN exposure)  
✅ **Encryption:** Fernet key present in .env  
⚠️ **API Keys:** MISSING - Must add before deployment  
✅ **Rate Limits:** 30 req/5s configured  
✅ **Sensitive files:** Excluded from git (.env, data/, *.gguf)

---

## 📋 CURRENT STATUS

| Check | Status |
|-------|--------|
| .env exists | ✅ |
| .env has ASTRA_ENCRYPTION_KEY | ✅ |
| .env has ASTRA_API_KEYS | ❌ **MISSING** |
| .env not in git | ✅ |
| Binding 127.0.0.1 | ✅ |
| ship.ps1 paths valid | ⚠️ **NEEDS UPDATE** |
| Desktop configs localhost:8080 | ✅ |
| Git initialized | ❌ **NO COMMITS** |
| Prometheus alerts ready | ✅ |
| Production hardening | ✅ |

---

## 🏁 GO/NO-GO DECISION

**VERDICT: NO-GO** ❌

**Blockers:**
1. Missing `ASTRA_API_KEYS` in .env (CRITICAL)
2. Git not initialized (prevents tagging)
3. ship.ps1 paths need verification (CRITICAL)

**ETA to GO:** 90 seconds (fix all 3 items above)

---

## 🆘 QUICK ROLLBACK (IF NEEDED)

```powershell
# Stop services
powershell -ExecutionPolicy Bypass -File .\scripts\stop.ps1

# Restore backup
Expand-Archive -Path ".\backup\astra_pre_v1_YYYYMMDD_HHMMSS.zip" -DestinationPath .\ -Force

# Restart
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

---

**⏱️ Total time to fix blockers: 90 seconds**  
**🎯 After fixes: Ready for production deployment**

---

## 📝 NICE-TO-HAVE IMPROVEMENTS (POST-DEPLOY)

### Disable docs in production
Edit `src/astra/api/app.py`:
```python
app = FastAPI(
    docs_url=None,      # Disable /docs
    redoc_url=None,     # Disable /redoc
    # ... rest of config
)
```

### Schedule WAL checkpoint (weekly)
```powershell
schtasks /create /tn "ASTRA WAL Checkpoint" /tr "python X:\PROJECT_ASTRA_1.0\scripts\wal_checkpoint.py" /sc weekly /d SUN /st 03:00
```

### Load test baseline
```bash
k6 run scripts/loadtest_baseline.js
```

**Targets:** p95 < 1.2s, errors < 5%, cache hit ≥ 25%

---

**END OF 90-SECOND GO/NO-GO CHECK**
