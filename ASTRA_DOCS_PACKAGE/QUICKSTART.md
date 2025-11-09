[← Docs Home](DOCUMENTATION_INDEX.md) | [Quick Start](QUICKSTART.md) | [Deployment](DEPLOYMENT_GUIDE_CONSOLIDATED.md) | [Architecture](ARCHITECTURE_PRODUCTION.md)

---

# 🚀 ASTRA - 5-Minute Quick Start

Get ASTRA running in 5 minutes with zero configuration.

---

## ⚡ Option 1: One-Click Launch (Recommended)

**Windows:**
```powershell
# Double-click this file:
X:\PROJECT_ASTRA\astra-launcher\LAUNCH_ASTRA.bat
```

**Or from command line:**
```powershell
cd X:\PROJECT_ASTRA
.\astra-launcher\LAUNCH_ASTRA.bat
```

**What it does:**
1. ✅ Checks if backend is running
2. ✅ Auto-starts backend if needed
3. ✅ Opens desktop app
4. ✅ Done!

---

## 🔧 Option 2: Manual Start

### Step 1: Start LLM Server (Terminal 1)

```powershell
cd X:\PROJECT_ASTRA
.\scripts\start_gptoss_server.ps1
```

**Wait for:** `"HTTP server listening"` message (~30 seconds)

### Step 2: Start ASTRA Backend (Terminal 2)

```powershell
cd X:\PROJECT_ASTRA
.\.venv\Scripts\python.exe run_server.py
```

**Wait for:** `"Application startup complete"` message

### Step 3: Verify Everything Works

```powershell
# Check LLM server
curl http://localhost:8001/health

# Check ASTRA backend
curl http://localhost:8080/v1/system/health

# Expected: {"status":"healthy","llm_healthy":true,"database_connected":true}
```

---

## 🎯 Your First API Call

### 1. Create a Conversation

```powershell
$conv = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/v1/conversations/" `
  -ContentType "application/json" `
  -Body '{"title":"My First Chat"}'

$convId = $conv.id
Write-Host "Conversation ID: $convId" -ForegroundColor Green
```

### 2. Send a Message

```powershell
$body = @{
    conversation_id = $convId
    message = "Hello ASTRA! What can you do?"
    use_memory = $true
} | ConvertTo-Json

$response = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/v1/chat/" `
  -ContentType "application/json" `
  -Body $body

Write-Host "ASTRA:" $response.message -ForegroundColor Cyan
```

### 3. Continue the Conversation

```powershell
$body = @{
    conversation_id = $convId
    message = "Tell me more about your memory capabilities"
    use_memory = $true
} | ConvertTo-Json

$response = Invoke-RestMethod -Method POST -Uri "http://localhost:8080/v1/chat/" `
  -ContentType "application/json" `
  -Body $body

Write-Host "ASTRA:" $response.message -ForegroundColor Cyan
```

---

## 📚 Useful Endpoints

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /v1/system/health` | Check system status | `curl http://localhost:8080/v1/system/health` |
| `GET /v1/system/version` | Get version info | `curl http://localhost:8080/v1/system/version` |
| `GET /v1/conversations/` | List conversations | `curl http://localhost:8080/v1/conversations/` |
| `GET /docs` | Interactive API docs | Open http://localhost:8080/docs in browser |
| `GET /metrics` | Prometheus metrics | `curl http://localhost:8080/metrics` |

---

## 🔍 Troubleshooting (30 seconds)

### ❌ LLM not responding?

**Check status:**
```powershell
curl http://localhost:8001/health
```

**If offline, restart:**
```powershell
.\scripts\start_gptoss_server.ps1
```

**Common causes:**
- Model not loaded (needs ~12GB disk space)
- Port 8001 in use
- Out of memory (needs ~8GB RAM free)

---

### ❌ Port 8080 in use?

**Change port in `.env`:**
```bash
ASTRA_SERVER_PORT=8081
```

**Then restart backend:**
```powershell
.\.venv\Scripts\python.exe run_server.py
```

---

### ❌ "Database is locked" error?

**Quick fix:**
```powershell
# Restart backend (releases locks)
# Press Ctrl+C in backend terminal, then:
.\.venv\Scripts\python.exe run_server.py
```

**Permanent fix:**
Add to `.env`:
```bash
ASTRA_DATABASE_POOL_SIZE=20
ASTRA_DATABASE_MAX_OVERFLOW=40
```

---

### ❌ API returns 401 Unauthorized?

**If API key auth is enabled, add header:**
```powershell
$headers = @{
    "X-API-Key" = $env:ASTRA_API_KEY
}

curl -H "X-API-Key: $env:ASTRA_API_KEY" http://localhost:8080/v1/system/health
```

**Or temporarily disable auth:**
Remove `ASTRA_API_KEY` from `.env` and restart.

---

### ❌ Slow responses or timeouts?

**Check reasoning mode:**
```bash
# In .env, try lower mode:
ASTRA_LLM_REASONING_MODE=low  # Instead of medium/high
```

**Reduce context window:**
```bash
ASTRA_LLM_CONTEXT_LENGTH=65536  # Instead of 131072
```

**Restart both servers after config changes.**

---

## 🎓 Next Steps

### Explore the API
Open **Swagger UI**: http://localhost:8080/docs

Interactive documentation with "Try it out" buttons!

### Read Full Documentation
- **README.md** - Overview and features
- **ARCHITECTURE.md** - System design
- **DEPLOYMENT_STATUS.md** - Current status and progress
- **CHECKLIST.md** - Detailed setup guide

### Run Tests
```powershell
cd X:\PROJECT_ASTRA
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### Monitor Performance
```powershell
# Prometheus metrics
curl http://localhost:8080/metrics

# Health check
curl http://localhost:8080/v1/system/health | ConvertFrom-Json
```

---

## 💡 Pro Tips

### Desktop Shortcut
1. Right-click `LAUNCH_ASTRA.bat`
2. Send to → Desktop (create shortcut)
3. Rename to "ASTRA"

### Environment Variables
Create `.env` file for custom settings:
```bash
ASTRA_SERVER_PORT=8080
ASTRA_LLM_REASONING_MODE=medium
ASTRA_LLM_TEMPERATURE=0.35
ASTRA_API_KEY=your-secret-key-here
```

### Check Logs
```powershell
# Backend logs (structured JSON)
tail -f logs/astra.log

# Or view in terminal where you started run_server.py
```

### Memory Stats
```powershell
$health = Invoke-RestMethod http://localhost:8080/v1/system/health
$health.memory_stats
# Shows: total_memories, collection_name, embedding_model
```

---

## 🚨 Getting Help

**Issues?** Check these in order:

1. ✅ LLM server running? `curl http://localhost:8001/health`
2. ✅ Backend running? `curl http://localhost:8080/v1/system/health`
3. ✅ Correct ports? Check `.env` and firewall
4. ✅ Enough resources? 8GB RAM free, 15GB disk space
5. ✅ Recent changes? Restart both servers

**Still stuck?** Check full documentation:
- `CHECKLIST.md` - Step-by-step troubleshooting
- `DEPLOYMENT_STATUS.md` - Known issues and fixes
- `docs/RUNBOOK.md` - Operational procedures (if created)

---

## 🎯 Success!

If you see this, you're ready:

```json
{
  "status": "healthy",
  "llm_healthy": true,
  "database_connected": true,
  "memory_stats": {
    "total_memories": 21,
    "collection_name": "astra_memory"
  }
}
```

**Welcome to ASTRA!** 🚀

You now have a production-grade AI assistant with:
- ✅ Semantic memory (RAG)
- ✅ 128K token context
- ✅ Streaming responses
- ✅ Conversation history
- ✅ Production monitoring

**Ready to chat!** Use the API examples above or open http://localhost:8080/docs

---

*Last updated: October 9, 2025*
