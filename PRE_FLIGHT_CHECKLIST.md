# PRE-FLIGHT CHECKLIST - 60-Second Sanity Check

**Before running `ship.ps1` or starting services manually**

---

## 🔒 SECURITY & NETWORK BINDING

### Choose Your Binding Strategy

**Local Development (Recommended):**
```powershell
# Use 127.0.0.1 (localhost only - no LAN exposure)
--host 127.0.0.1  # For both LLM and API
```

**Network Access (if needed for Electron on LAN):**
```powershell
# Use 0.0.0.0 (accessible from LAN)
--host 0.0.0.0  # Requires firewall rules
```

⚠️ **Default recommendation: Use `127.0.0.1` unless you need LAN access**

---

## ⚙️ .ENV ESSENTIALS

Create/verify `X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\.env`:

```ini
# LLM Backend (use 127.0.0.1 for local-only)
ASTRA_LLM_BASE_URL=http://127.0.0.1:8001/v1

# API Server Port
ASTRA_SERVER_PORT=8080

# Authentication (generate unique key)
ASTRA_API_KEYS=your-secure-api-key-here

# Encryption (generate once, keep secret)
ASTRA_ENCRYPTION_KEY=your-32-byte-base64-key-here

# Optional: Adjust rate limits
ASTRA_RATE_LIMIT_PER_MIN=120
ASTRA_CONCURRENCY_INFLIGHT=32
ASTRA_CONCURRENCY_QUEUE=64
```

**Generate keys:**
```powershell
# API Key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key (Fernet-compatible)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 🎮 VRAM REALITY CHECK

### Start Conservative, Scale Up

**CPU-Only (Safe Start):**
```powershell
--n-gpu-layers 0
--ctx-size 131072  # or 65536 if OOM
```

**GPU Acceleration (if CUDA build + sufficient VRAM):**
```powershell
# Start modest, increase gradually
--n-gpu-layers 20   # Try this first
--n-gpu-layers 35   # If no OOM
--ctx-size 131072   # Full context
```

**OOM Symptoms:**
- llama.cpp crashes
- "CUDA out of memory" errors
- System freezes

**OOM Fixes:**
1. Lower `--ctx-size` (131072 → 65536 → 32768)
2. Lower `--n-gpu-layers` (35 → 20 → 10 → 0)
3. Close other GPU apps
4. Use CPU-only mode (`--n-gpu-layers 0`)

---

## 🔥 FIREWALL RULES

### If Using `--host 0.0.0.0`

**Windows Firewall:**
```powershell
# Allow inbound on port 8001 (LLM)
New-NetFirewallRule -DisplayName "ASTRA LLM Server" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow

# Allow inbound on port 8080 (API)
New-NetFirewallRule -DisplayName "ASTRA API Server" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

### If Using `--host 127.0.0.1` (Recommended)
**No firewall rules needed** - localhost-only binding

---

## 🐍 PYTHON ENVIRONMENT

### Verify Virtual Environment

**Check if activated:**
```powershell
# Should show .venv path
python -c "import sys; print(sys.prefix)"
```

**Activate if needed:**
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\.venv\Scripts\Activate.ps1
```

**Verify dependencies:**
```powershell
# Check uvicorn installed
python -m pip show uvicorn

# Check fastapi installed
python -m pip show fastapi

# Install if missing
python -m pip install -r requirements.txt
```

---

## 📋 PRE-FLIGHT CHECKLIST

Before starting services:

- [ ] `.env` file exists with correct values
- [ ] API key generated and set in `.env`
- [ ] Encryption key generated and set in `.env`
- [ ] Decided on binding: `127.0.0.1` (local) or `0.0.0.0` (LAN)
- [ ] Firewall rules set (if using `0.0.0.0`)
- [ ] Python virtual environment activated
- [ ] uvicorn and fastapi installed
- [ ] Model file exists at specified path
- [ ] llama-server.exe exists at specified path
- [ ] Sufficient disk space (check `data/` directory)
- [ ] Ports 8001 and 8080 are free

**Check ports:**
```powershell
netstat -ano | findstr ":8001 :8080"
# Should return nothing if ports are free
```

---

## 🚀 START SERVICES (SECURE LOCAL BIND)

### Terminal 1 - llama.cpp LLM Server

```powershell
"C:\llama\llama-server.exe" `
  --model "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\models\gpt-oss-20b-q4_k_m.gguf" `
  --host 127.0.0.1 `
  --port 8001 `
  --ctx-size 131072 `
  --n-gpu-layers 0
```

**Wait for:** "HTTP server listening on 127.0.0.1:8001"

### Terminal 2 - ASTRA API Server

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python -m uvicorn src.astra.api.app:app --host 127.0.0.1 --port 8080 --log-level info
```

**Wait for:** "Uvicorn running on http://127.0.0.1:8080"

---

## ✅ VERIFY + TAG

### Run Go/No-Go Check
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
powershell -ExecutionPolicy Bypass -File .\scripts\deploy_go_nogo.ps1
```

**Expected:** 5-7 checks pass → GO decision

### Tag Release (if green)
```powershell
git add .
git commit -m "Production v1.0.0 - Deployment system complete"
git tag -a v1.0.0 -m "ASTRA Core v1.0 - Production Ready"
git push origin v1.0.0
```

---

## 📊 30-MINUTE WATCHLIST (Golden Signals)

### Targets After Deployment

| Metric | Target | Alert If |
|--------|--------|----------|
| **p95 Latency** | ≤1.2s | >1.2s for 5 min |
| **LLM Failures** | Steady/near-zero | >5 in 5 min |
| **Cache Hit Rate** | ≥25% → 40% | <20% for 30 min |
| **Queue Depth** | <10 | >50 for 5 min |
| **Error Logs** | 0 sustained | Any ERROR/CRITICAL |

**Monitor:**
```powershell
.\scripts\monitor_golden_signals.ps1
```

---

## 🔧 QUICK TRIAGE MAP

### 503 Errors from Circuit Breaker
**Symptoms:** API returns 503, circuit breaker open  
**Causes:** LLM server down or overloaded  
**Fixes:**
1. Verify llama.cpp is running: `curl http://127.0.0.1:8001/v1/models`
2. Reduce RPS (lower concurrent requests)
3. Increase circuit breaker cooldown (edit `circuit_breaker.py`)
4. Enable semantic cache to reduce LLM calls

### High Latency (p95 >1.2s)
**Symptoms:** Slow responses, timeout warnings  
**Causes:** Large context, many memories, slow LLM  
**Fixes:**
1. Lower `--ctx-size` (131072 → 65536)
2. Raise cache TTL (5min → 30min in `semantic_cache.py`)
3. Trim retrieved memories (reduce top_k in memory queries)
4. Enable GPU layers if available
5. Reduce max_tokens in requests

### Out of Memory (OOM)
**Symptoms:** llama.cpp crashes, CUDA errors, system freeze  
**Causes:** Too many GPU layers, too large context  
**Fixes:**
1. Lower `--n-gpu-layers` (35 → 20 → 10 → 0)
2. Lower `--ctx-size` (131072 → 65536 → 32768)
3. Use CPU-only: `--n-gpu-layers 0`
4. Close other GPU applications
5. Restart llama.cpp with new settings

### Desktop UI Can't Connect
**Symptoms:** "Connection refused", "ERR_CONNECTION_REFUSED"  
**Causes:** Wrong URL, firewall, binding mismatch  
**Fixes:**
1. Verify API is running: `curl http://localhost:8080/v1/system/health`
2. Check desktop config points to `http://localhost:8080`
3. If using `127.0.0.1` binding, desktop must use `localhost` or `127.0.0.1`
4. If using `0.0.0.0` binding, desktop can use machine IP
5. Check firewall rules (if needed)

### Cache Not Working
**Symptoms:** Low cache hit rate (<10%), all requests slow  
**Causes:** Cache not initialized, TTL too short  
**Fixes:**
1. Verify cache imported: Check `src/astra/infrastructure/cache/__init__.py`
2. Check cache TTL: Should be 300s (5min) minimum
3. Verify semantic cache in use (check logs)
4. Warm cache with common queries

### Bridge Health Check Fails
**Symptoms:** `/v1/bridge/healthz` returns 404 or error  
**Causes:** Bridge router not mounted  
**Fixes:**
1. Verify router mount in `src/astra/api/app.py` line 146
2. Restart API server
3. Check imports at top of `app.py`

---

## 📝 CONFIGURATION TEMPLATES

### .env Template (Complete)
```ini
# === LLM Backend ===
ASTRA_LLM_BASE_URL=http://127.0.0.1:8001/v1
ASTRA_LLM_TIMEOUT=120
ASTRA_LLM_MAX_RETRIES=3

# === API Server ===
ASTRA_SERVER_HOST=127.0.0.1
ASTRA_SERVER_PORT=8080

# === Security ===
ASTRA_API_KEYS=your-api-key-here
ASTRA_ENCRYPTION_KEY=your-encryption-key-here

# === Rate Limiting ===
ASTRA_RATE_LIMIT_PER_MIN=120
ASTRA_CONCURRENCY_INFLIGHT=32
ASTRA_CONCURRENCY_QUEUE=64

# === Database ===
ASTRA_DB_PATH=data/astra.db

# === Memory ===
ASTRA_MEMORY_TOP_K=10
ASTRA_MEMORY_THRESHOLD=0.7

# === Logging ===
ASTRA_LOG_LEVEL=INFO
ASTRA_LOG_PATH=data/logs/astra.log
```

### ship.ps1 Configuration (Secure)
Edit these lines at top of `scripts/ship.ps1`:

```powershell
$LlmPort    = 8001
$ApiPort    = 8080
$LlamaExe   = "C:\llama\llama-server.exe"     # Your path
$ModelPath  = "C:\models\gpt-oss-20b-q4_k_m.gguf"  # Your path
$Ctx        = 131072   # Or 65536 if OOM
$GpuLayers  = 0        # Start with 0, increase if GPU available
```

**Change host binding:**
```powershell
# In Start-Llama function (line 36):
"--host",  "127.0.0.1",  # Use 0.0.0.0 only if needed

# In Start-Astra function - update $AstraCmd (line 17):
$AstraCmd = "python -m uvicorn src.astra.api.app:app --host 127.0.0.1 --port $ApiPort --log-level info"
```

---

## ✅ READY TO DEPLOY

Once all checklist items are complete:

```powershell
# Option 1: Automated (recommended)
powershell -ExecutionPolicy Bypass -File .\scripts\ship.ps1

# Option 2: Manual (see Terminal 1 & 2 commands above)
```

**Expected:** All services start, smoke test passes, ready to tag v1.0.0

---

**Last updated:** October 16, 2025  
**See also:** `DEPLOYMENT_READY_FINAL.md`, `scripts/SCRIPTS_INDEX.md`
