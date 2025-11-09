# ✅ FINAL GREEN-LIGHT CHECKLIST

**Copy/paste this before deploying**

---

## 📋 PRE-FLIGHT CHECKLIST

### 1. Environment Configuration

- [ ] `.env` file exists in project root
- [ ] `.env` contains `ASTRA_API_KEYS=<your-generated-key>`
- [ ] `.env` contains `ASTRA_ENCRYPTION_KEY=<your-fernet-key>`
- [ ] `.env` contains `ASTRA_LLM_BASE_URL=http://127.0.0.1:8001/v1`
- [ ] `.env` contains `ASTRA_SERVER_PORT=8080`
- [ ] `.env` contains `ASTRA_DATABASE_URL=sqlite:///data/astra.db`
- [ ] `.env` contains `ASTRA_VECTOR_STORE_PERSIST_DIRECTORY=./data/chromadb`

**Generate keys if needed:**
```powershell
# API Key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### 2. Script Configuration

Edit `scripts\ship.ps1` (lines 11-17):

- [ ] `$LlamaExe` = Path to your llama-server.exe
- [ ] `$ModelPath` = Path to your .gguf model file
- [ ] `$Ctx` = 131072 (or 65536 if OOM)
- [ ] `$GpuLayers` = 0 (increase if CUDA build available)
- [ ] `$HostBind` = "127.0.0.1" (secure local-only default)

**Verify paths exist:**
```powershell
Test-Path "C:\llama\llama-server.exe"        # Should return True
Test-Path "C:\models\gpt-oss-20b-q4_k_m.gguf" # Should return True
```

---

### 3. Port Availability

- [ ] Port 8001 is free (LLM server)
- [ ] Port 8080 is free (API server)

**Check ports:**
```powershell
netstat -ano | findstr ":8001 :8080"
# Should return nothing (no output = ports free)
```

---

### 4. Python Environment

- [ ] Virtual environment activated (if using)
- [ ] uvicorn installed
- [ ] fastapi installed
- [ ] All dependencies installed

**Verify:**
```powershell
python -c "import sys; print(sys.prefix)"  # Should show .venv path
python -m pip show uvicorn                  # Should show version
python -m pip show fastapi                  # Should show version
```

---

## 🚀 DEPLOYMENT CHECKLIST

### 5. Launch Services

- [ ] Run `.\scripts\ship.ps1` successfully
- [ ] See "LLM_OK" in output
- [ ] See "API_OK" in output
- [ ] See "BRIDGE_OK" in output
- [ ] Smoke test shows 5/5 passing

**Command:**
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

---

### 6. Health Verification

- [ ] LLM server responds: http://127.0.0.1:8001/v1/models
- [ ] API health check passes: http://127.0.0.1:8080/v1/system/health
- [ ] Bridge health check passes: http://127.0.0.1:8080/v1/bridge/healthz
- [ ] Metrics endpoint active: http://127.0.0.1:8080/metrics

**Quick verification script:**
```powershell
# All should succeed with no errors
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
$metrics = Invoke-WebRequest http://127.0.0.1:8080/metrics -UseBasicParsing
if ($metrics.Content -match "astra_") { Write-Host "✓ Metrics OK" -ForegroundColor Green }
```

---

### 7. Metrics & Alerts

- [ ] Prometheus metrics visible at `/metrics`
- [ ] Metrics include `astra_requests_total`
- [ ] Metrics include `astra_cache_hits_total`
- [ ] Metrics include `astra_llm_failures_total`
- [ ] Alert rules file exists: `ops/prometheus/astra_alerts.yml`

**Verify metrics:**
```powershell
$metrics = Invoke-WebRequest http://127.0.0.1:8080/metrics -UseBasicParsing
$metrics.Content | Select-String "astra_requests_total"
$metrics.Content | Select-String "astra_cache_hits_total"
$metrics.Content | Select-String "astra_llm_failures_total"
```

---

## 🏷️ TAG & RELEASE

### 8. Git Tagging

**IMPORTANT: Use correct git command (NOT `git add .git`)**

```powershell
# Stage all changes
git add .

# Commit with clear message
git commit -m "ASTRA Core v1.0.0 - Secure deployment system"

# Create annotated tag
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"

# Push to origin
git push origin v1.0.0
```

- [ ] `git add .` completed (no errors)
- [ ] Commit created
- [ ] Tag v1.0.0 created
- [ ] Tag pushed to origin

---

## 📊 POST-DEPLOYMENT MONITORING

### 9. Golden Signals (30 minutes)

- [ ] Run monitoring script: `.\scripts\monitor_golden_signals.ps1`
- [ ] p95 latency ≤ 1.2s
- [ ] LLM failures steady/near-zero
- [ ] Cache hit rate ≥ 25% (trending toward 40%)
- [ ] No sustained 503 errors
- [ ] No errors in logs: `data\logs\astra.log`

**Monitor command:**
```powershell
.\scripts\monitor_golden_signals.ps1 -DurationMinutes 30 -CheckIntervalSeconds 60
```

**Watch logs:**
```powershell
Get-Content .\data\logs\astra.log -Wait -Tail 20
```

---

## 🎁 OPTIONAL ENHANCEMENTS

### 10. Same-Day Quick Wins

- [ ] **Disable /docs in production** (if not needed)
  - Edit `src/astra/api/app.py`
  - Change: `app = FastAPI(docs_url=None, redoc_url=None)`

- [ ] **Run k6 load test** for p95 baseline
  ```bash
  k6 run scripts/loadtest_baseline.js
  ```
  - Target: p95 < 1.2s ✓
  - Target: Errors < 5% ✓
  - Target: Cache hit ≥ 25% ✓

- [ ] **Autostart on boot** (Windows services)
  ```powershell
  # Install NSSM (Non-Sucking Service Manager)
  # Then wrap both commands:
  nssm install "ASTRA-LLM" "C:\llama\llama-server.exe" "--model ..."
  nssm install "ASTRA-API" "python" "-m uvicorn ..."
  ```

---

## 🔧 CURL COMMANDS (PowerShell vs Real Curl)

### PowerShell (Invoke-WebRequest)
```powershell
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing
```

### Real curl (if installed)
```powershell
curl.exe -fsS http://127.0.0.1:8080/v1/system/health
```

**Note:** In PowerShell, `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` to call real curl.

---

## 🔒 SECURITY VERIFICATION

### 11. Security Checks

- [ ] **Binding:** Using 127.0.0.1 (local-only)
  - If using 0.0.0.0, firewall rules are set
- [ ] **API Keys:** Strong keys generated (32+ chars)
- [ ] **Encryption:** Fernet key generated and stored securely
- [ ] **Rate Limiting:** Enabled (120 req/min default)
- [ ] **.env Security:** File not in git (check `.gitignore`)
- [ ] **Docs Endpoint:** Disabled in production (or restricted)

---

## ✅ FINAL GO/NO-GO

**All items above checked? → GREEN LIGHT ✅**

**Any items unchecked? → Review and fix before deploying**

---

## 🎯 SUCCESS CRITERIA

Deployment is successful when:

| Criterion | Status |
|-----------|--------|
| ship.ps1 completes with no errors | ✅ |
| All 5 smoke tests pass | ✅ |
| All 4 health checks return 200 OK | ✅ |
| Metrics endpoint shows astra_* metrics | ✅ |
| No errors in logs for 30 minutes | ✅ |
| p95 latency ≤ 1.2s | ✅ |
| Cache hit rate ≥ 25% | ✅ |
| Tag v1.0.0 pushed to origin | ✅ |

---

## 🚨 COMMON MISTAKES TO AVOID

1. ❌ **Don't use:** `git add .git` → ✅ **Use:** `git add .`
2. ❌ **Don't use:** `curl` in PowerShell (it's an alias) → ✅ **Use:** `curl.exe` or `Invoke-WebRequest`
3. ❌ **Don't bind:** 0.0.0.0 without firewall → ✅ **Use:** 127.0.0.1 for local-only
4. ❌ **Don't skip:** .env file generation → ✅ **Create:** .env with proper keys
5. ❌ **Don't forget:** Path updates in ship.ps1 → ✅ **Edit:** $LlamaExe and $ModelPath

---

## 📚 REFERENCE DOCS

- **Quick Start:** `DEPLOY_CARD.md` (one-page)
- **Pre-flight:** `PRE_FLIGHT_CHECKLIST.md` (security & config)
- **Complete Guide:** `SHIP_IT_NOW.md` (full procedures)
- **Troubleshooting:** `ops/RUNBOOK.md` (operations manual)
- **Changelog:** `RELEASE_NOTES_v1.0.0.md` (what's new)

---

## 🎉 READY TO SHIP

When all checkboxes above are ✅, you're ready to deploy!

**Final command:**
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

**Then tag:**
```powershell
git add .
git commit -m "ASTRA Core v1.0.0 - Secure deployment system"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
git push origin v1.0.0
```

**🚀 LET'S SHIP IT!**
