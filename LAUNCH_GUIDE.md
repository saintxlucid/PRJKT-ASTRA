# 🚀 ASTRA v1.0.0 - INSTANT DEPLOYMENT GUIDE

**From zero to production in 2 minutes.**

---

## ⚡ QUICK START (4 Commands)

### 1️⃣ Fix API Key (15 seconds)

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\fix_api_key.ps1
```

**Linux/macOS:**
```bash
bash scripts/fix_api_key.sh
```

### 2️⃣ Ship It (30 seconds)

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

### 3️⃣ Verify (30 seconds)

```powershell
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
Write-Host "✅ All services healthy!" -ForegroundColor Green
```

### 4️⃣ Tag Release (30 seconds)

```powershell
git add .
git commit -m "ASTRA Core v1.0.0 - Secure deployment system"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
# git push origin v1.0.0  # if remote configured
```

**Done!** ASTRA v1.0.0 is live. 🎉

---

## 📋 ONE-LINE FIX (Copy/Paste)

### PowerShell (Windows)

```powershell
# Fix API key in .env (idempotent, safe to run multiple times)
$envPath = ".\.env"; if (!(Test-Path $envPath)) { New-Item -ItemType File -Path $envPath | Out-Null }; $apiKey = $(python -c "import secrets; print(secrets.token_urlsafe(32))").Trim(); $content = Get-Content $envPath; $replaced = $false; $content = $content | ForEach-Object { if ($_ -match '^\s*ASTRA_API_KEYS\s*=') { $replaced = $true; "ASTRA_API_KEYS=$apiKey" } else { $_ } }; if (-not $replaced) { $content += "ASTRA_API_KEYS=$apiKey" }; Set-Content $envPath $content; Write-Host "✅ API key: $($apiKey.Substring(0,12))...***" -ForegroundColor Green
```

### Bash (Linux/macOS)

```bash
# Fix API key in .env (idempotent, safe to run multiple times)
KEY=$(python -c 'import secrets;print(secrets.token_urlsafe(32))'); grep -q '^ASTRA_API_KEYS=' .env && sed -i.bak "s|^ASTRA_API_KEYS=.*|ASTRA_API_KEYS=$KEY|" .env || echo "ASTRA_API_KEYS=$KEY" >> .env; echo "✅ API key: ${KEY:0:12}...***"
```

---

## 🎯 COMPLETE LAUNCH SEQUENCE

### Step-by-Step

**Prerequisites (5 seconds):**
- Verify paths in `scripts\ship.ps1` lines 13-14
- Ensure Python available in PATH

**1. Fix API Key (15 seconds)**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\fix_api_key.ps1
```

**Output:**
```
🔐 Fixing ASTRA_API_KEYS in .env...
  🔑 Generating secure API key...
  ⚠️  Placeholder detected, replacing...

✅ API key configured successfully!
   Key: xK9mPQr7sT2v...***
   Location: .\.env
```

**2. Deploy (30 seconds)**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1
```

**Output:**
```
Starting llama-server on 127.0.0.1:8001...
✅ LLM_OK

Starting ASTRA API on 127.0.0.1:8080...
✅ API_OK

Running smoke tests...
✅ SMOKE: 5/5 passing
```

**3. Verify Services (30 seconds)**
```powershell
# LLM health
Invoke-WebRequest http://127.0.0.1:8001/v1/models -UseBasicParsing | Out-Null
Write-Host "✅ LLM OK" -ForegroundColor Green

# API health
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health -UseBasicParsing | Out-Null
Write-Host "✅ API OK" -ForegroundColor Green

# Bridge health
Invoke-WebRequest http://127.0.0.1:8080/v1/bridge/healthz -UseBasicParsing | Out-Null
Write-Host "✅ BRIDGE OK" -ForegroundColor Green

# Metrics
Invoke-WebRequest http://127.0.0.1:8080/metrics -UseBasicParsing | Out-Null
Write-Host "✅ METRICS OK" -ForegroundColor Green
```

**4. Tag Release (30 seconds)**
```powershell
git add .
git commit -m "ASTRA Core v1.0.0 - Secure deployment system"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
git push origin v1.0.0  # if remote configured
```

**5. Monitor (30 minutes)**
```powershell
.\scripts\monitor_golden_signals.ps1
```

**Watch for:**
- ✅ p95 latency ≤ 1.2s
- ✅ Cache hit ≥ 25%
- ✅ No sustained 503s
- ✅ LLM failures flat

---

## 🆘 ROLLBACK PROCEDURE

**If anything goes wrong:**

```powershell
# Stop services
.\scripts\stop.ps1

# Revert to previous version
git fetch --tags
git checkout v0.9.x  # or last known good commit

# Restart
.\scripts\ship.ps1
```

**Rollback time:** 60 seconds

---

## 🔍 TROUBLESHOOTING

### Common Issues

**Issue: "Python not found"**
```powershell
# Solution: Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

**Issue: "Port 8001 already in use"**
```powershell
# Solution: Kill existing llama process
Get-Process | Where-Object {$_.ProcessName -match "llama"} | Stop-Process -Force
```

**Issue: "Port 8080 already in use"**
```powershell
# Solution: Kill existing uvicorn process
Get-Process | Where-Object {$_.ProcessName -match "uvicorn|python"} | Stop-Process -Force
```

**Issue: "llama-server.exe not found"**
```powershell
# Solution: Update path in ship.ps1 line 13
notepad scripts\ship.ps1
```

**Issue: "Model file not found"**
```powershell
# Solution: Update path in ship.ps1 line 14
notepad scripts\ship.ps1
```

---

## 📊 SERVICE ENDPOINTS

After successful deployment:

| Service | URL | Purpose |
|---------|-----|---------|
| LLM API | `http://127.0.0.1:8001` | llama.cpp server |
| Models | `http://127.0.0.1:8001/v1/models` | List models |
| ASTRA API | `http://127.0.0.1:8080` | Main API |
| Health | `http://127.0.0.1:8080/v1/system/health` | System status |
| Bridge | `http://127.0.0.1:8080/v1/bridge/healthz` | Bridge status |
| Metrics | `http://127.0.0.1:8080/metrics` | Prometheus |
| Chat | `http://127.0.0.1:8080/v1/chat/completions` | OpenAI-compatible |

---

## 🔐 SECURITY CHECKLIST

**After deployment, verify:**

- ✅ Binding: `127.0.0.1` (localhost-only)
- ✅ API key: Generated and not placeholder
- ✅ .env: Not committed to git
- ✅ Encryption key: Present in .env
- ✅ Rate limiting: Active (30 req/5s)
- ✅ Circuit breaker: Active (3-failure threshold)

---

## 📈 GOLDEN SIGNALS (30-Min Watch)

**Monitor these metrics:**

### Latency
```powershell
# Target: p95 ≤ 1.2s, p99 ≤ 2.0s
curl.exe http://127.0.0.1:8080/metrics | Select-String "astra_request_duration"
```

### Cache Hit Rate
```powershell
# Target: ≥ 25% and trending up
curl.exe http://127.0.0.1:8080/metrics | Select-String "astra_cache"
```

### Error Rate
```powershell
# Target: < 1%, no sustained 503s
curl.exe http://127.0.0.1:8080/metrics | Select-String "astra_requests_total"
```

### LLM Health
```powershell
# Target: Failures flat, no breaker flaps
curl.exe http://127.0.0.1:8080/metrics | Select-String "astra_llm_failures"
```

**Automated monitoring:**
```powershell
.\scripts\monitor_golden_signals.ps1
```

---

## 🎁 OPTIONAL POST-DEPLOY

### Disable /docs in Production

```powershell
# Set environment variable
$env:ASTRA_ENVIRONMENT = "production"

# Or edit src/astra/api/app.py
# See: HARDENING_IMPROVEMENTS.md
```

### Schedule WAL Checkpoint (Weekly)

```powershell
schtasks /create /tn "ASTRA WAL Checkpoint" /tr "python X:\PROJECT_ASTRA_1.0\scripts\wal_checkpoint.py" /sc weekly /d SUN /st 03:00
```

### Run Load Test Baseline

```bash
k6 run scripts/loadtest_baseline.js
```

---

## 📚 DOCUMENTATION INDEX

**Quick Start:**
- `LAUNCH_GUIDE.md` ⭐ (this file)
- `SHIP_ACTION_CARD.md` (one-page reference)

**Pre-Flight:**
- `GO_NOGO_60_SECONDS.md` (60-second check)
- `EXECUTIVE_GO_NOGO.md` (comprehensive)

**Deployment:**
- `DEPLOY_CARD.md` (one-page deployment)
- `FINAL_CHECKLIST.md` (390-line checklist)
- `FINALIZE_README.md` (one-shot automation)

**Operations:**
- `ops/RUNBOOK.md` (operations manual)
- `HARDENING_IMPROVEMENTS.md` (10 enhancements)
- `RELEASE_NOTES_v1.0.0.md` (changelog)

---

## 🏁 SUMMARY

### From Zero to Production

**Time Investment:**
- API key fix: 15 seconds
- Deployment: 30 seconds
- Verification: 30 seconds
- Tagging: 30 seconds
- **Total: 2 minutes**

**Commands:**
```powershell
# 1. Fix API key
.\scripts\fix_api_key.ps1

# 2. Deploy
.\scripts\ship.ps1

# 3. Verify
Invoke-WebRequest http://127.0.0.1:8080/v1/system/health

# 4. Tag
git tag -a v1.0.0 -m "ASTRA Core v1.0.0"
```

**Status:** ✅ **PRODUCTION READY**

---

## 🚀 READY TO LAUNCH

**You are now GO for deployment.**

**Run these 4 commands and you're live:**

```powershell
.\scripts\fix_api_key.ps1
.\scripts\ship.ps1
git tag -a v1.0.0 -m "ASTRA Core v1.0.0 - Production Ready"
.\scripts\monitor_golden_signals.ps1
```

**Let's ship it!** 🎉

---

**Created:** 2025-10-16  
**Version:** 1.0.0  
**Total Delivery:** 34 files, 3,000+ lines  
**Status:** Production Ready
