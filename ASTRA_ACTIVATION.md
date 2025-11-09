# ASTRA Activation Protocol

**Purpose:** Give ASTRA_CORE identity, breath, and a safe memory loop on first run — then verify health and greet the operator.

---

## Quick Activation (60 seconds)

### One-Block PowerShell Run
```powershell
# Navigate to project root
cd X:\PROJECT_ASTRA_1.0

# Launch ASTRA with full activation
.\LAUNCH_ASTRA.ps1
```

**What this does:**
1. ✅ Generates API key if missing
2. ✅ Sets up capacity controls (120 req/60s per key)
3. ✅ Starts ASTRA server
4. ✅ Loads persona memories from exports
5. ✅ Performs health verification
6. ✅ Displays welcome message with endpoints

---

## Manual Steps (if automation fails)

### 1. Set API Key
```powershell
$env:ASTRA_API_KEY = (.\.venv\Scripts\python.exe -c "import secrets;print(secrets.token_urlsafe(48))")
Add-Content .env "ASTRA_API_KEY=$($env:ASTRA_API_KEY)"
```

### 2. Add Rate Limiting
```powershell
Add-Content .env "ASTRA_PER_KEY_RATE=120"
Add-Content .env "ASTRA_PER_KEY_PERIOD_SEC=60"
```

### 3. Start Components
```powershell
# Start llama.cpp (optional - ASTRA can run without it)
.\scripts\start_gptoss_server.ps1

# Start ASTRA server
.\.venv\Scripts\python.exe run_server.py
```

### 4. Load Persona (new terminal)
```powershell
.\.venv\Scripts\python.exe scripts\ingest_persona_memories.py
```

---

## Verification Commands

### Quick Status Check
```powershell
.\scripts\astra_status.ps1
```

### Detailed Health Check
```powershell
.\scripts\astra_status.ps1 -Detailed
```

### Test API Directly
```powershell
# Basic health
Invoke-RestMethod http://127.0.0.1:8080/v1/system/health

# Detailed health
Invoke-RestMethod http://127.0.0.1:8080/v1/system/healthz

# Metrics
Invoke-RestMethod http://127.0.0.1:8080/metrics
```

---

## Expected Boot Sequence

When activation completes successfully:

```
┌─────────────────────────────────────────────────────────────┐
│                  ✅ ASTRA_CORE ONLINE                       │
└─────────────────────────────────────────────────────────────┘

Short answer → ASTRA_CORE is online and ready. Health checks passed. 
Persona memory loaded.

Details:
• LLM backend: ✅ OK
• Database: ✅ OK  
• Vector store: ✅ OK (21+ memories)

Capacity controls: per-key 120/60s; queue empty

API Endpoints:
• Chat: http://127.0.0.1:8080/v1/chat/
• Health: http://127.0.0.1:8080/v1/system/healthz
• Metrics: http://127.0.0.1:8080/metrics

Try these queries:
• "Who created you and what are your values?"
• "Summarize our current ops posture and SLOs."
• "Draft my next two actions to harden memory hygiene."

— ASTRA_CORE
```

---

## Persona Identity Summary

**Name:** ASTRA  
**Creator:** Saint Lucid (Karim Al-Sharif)  
**Values:** Clarity, care, reliability, privacy, practical impact  
**Style:** Lucid, warm, precise; short by default, expand on request  

### Signature Behaviors
- **Direct answers first** → detailed explanation
- **Honest about limits** and uncertainties
- **Proposes concrete next actions**
- **Remembers preferences** and context

### Memory Policy
- **Atomic facts** with rich metadata tagging
- **User preferences:** Communication style, technical choices
- **Project facts:** Model specs, system status, SLOs
- **Goals:** Performance targets, operational requirements

---

## Troubleshooting

### Server Won't Start
```powershell
# Check prerequisites
.\scripts\astra_status.ps1

# Check ports
netstat -an | findstr ":8080"
netstat -an | findstr ":8001"

# Check logs
Get-Content data\logs\*.log | Select-Object -Last 50
```

### Persona Loading Failed
```powershell
# Force reload
.\LAUNCH_ASTRA.ps1 -ForcePersonaReload

# Check export directories exist
Test-Path "ASTRA MEMORY EXPORTS"
Test-Path "ASTRA MEMORY EXPORTS 2"

# Manual ingestion with verbose output
.\.venv\Scripts\python.exe scripts\ingest_persona_memories.py --verbose
```

### API Key Issues
```powershell
# Regenerate key
$env:ASTRA_API_KEY = (.\.venv\Scripts\python.exe -c "import secrets;print(secrets.token_urlsafe(48))")

# Update .env
(Get-Content .env) -replace "ASTRA_API_KEY=.*", "ASTRA_API_KEY=$($env:ASTRA_API_KEY)" | Set-Content .env
```

---

## Success Indicators

✅ **Health endpoint returns 200**  
✅ **Metrics endpoint shows astra_* series**  
✅ **Per-key rate limiter shows 429s under burst**  
✅ **Persona memories loaded (21+ items)**  
✅ **Chat endpoint accepts requests**  
✅ **Welcome message displays correctly**

---

**Status:** Ready for Production  
**Last Updated:** October 9, 2025  
**Version:** 1.0