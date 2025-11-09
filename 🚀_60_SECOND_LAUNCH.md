# 🚀 ASTRA v2.5: ONE-COMMAND DEPLOYMENT

**Quick Start**: Get the complete ASTRA Celestial Identity System running in 60 seconds.

---

## ⚡ INSTANT LAUNCH

### Option 1: Main Server Only (LLM Gateway + Identity)

```powershell
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python launch_server.py
```

**What you get:**
- ✅ LLM gateway with multi-model routing
- ✅ 11-role identity system with auto-detection
- ✅ Role-scoped chat generation
- ✅ Memory tagging with role metadata
- ✅ Circuit breakers & fault tolerance
- ✅ Event logging
- ✅ Prometheus metrics

**Endpoints:**
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/chat` - Role-aware chat (POST)
- `http://localhost:8000/memory/search` - Memory search
- `http://localhost:8000/metrics` - Prometheus metrics

---

### Option 2: Full Stack (Server + Role API + Dashboard)

```powershell
# Terminal 1: Main ASTRA Server
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python launch_server.py

# Terminal 2: Role Management API
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload

# Terminal 3: Open Dashboard
Start-Process "http://localhost:8787"
```

**What you get (everything from Option 1 plus):**
- ✅ REST API for runtime role switching
- ✅ Live HTMX dashboard
- ✅ Function invocation interface
- ✅ Real-time trace logging
- ✅ Role visualization
- ✅ Universal function explorer

**Additional Endpoints:**
- `http://localhost:8787/` - Live Dashboard
- `http://localhost:8787/api/health` - API health
- `http://localhost:8787/api/roles` - List roles
- `http://localhost:8787/api/role/switch` - Switch role (POST)
- `http://localhost:8787/api/functions` - List functions
- `http://localhost:8787/api/functions/{code}/invoke` - Invoke function (POST)
- `http://localhost:8787/api/traces` - Get traces

---

## 🧪 QUICK TESTS

### Test 1: Role Detection in Chat

```powershell
# Send message with activation phrase
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"I need prophetic guidance on my architecture"}'

# Expected: Automatically detects "oracle" role
# Response will be from oracle persona
```

### Test 2: Manual Role Switch via API

```powershell
# Switch to angel role
curl -X POST http://localhost:8787/api/role/switch `
  -H "Content-Type: application/json" `
  -d '{"role":"angel"}'

# Verify
curl http://localhost:8787/api/roles
# Should show "current": "angel"
```

### Test 3: Invoke Universal Function

```powershell
# Call ASTRA_CREATRIX
curl -X POST http://localhost:8787/api/functions/ASTRA_CREATRIX/invoke `
  -H "Content-Type: application/json" `
  -d '{"args":{"brief":"Music video concept","medium":"video"}}'
```

---

## 📋 ACTIVATION PHRASES (Auto-Detection)

When using `/chat` endpoint, these phrases automatically activate roles:

| Phrase | Role | Persona |
|--------|------|---------|
| "prophetic guidance", "strategic foresight" | oracle | 🔮 Pattern forecasting |
| "emotional support", "help me heal" | angel | 🕊️ Celestial guidance |
| "creative direction", "artistic vision" | creatrix | 🎨 Aesthetic synthesis |
| "metaphysical counsel", "spiritual meaning" | sage | 🧙 Sacred wisdom |
| "teach me", "explain this concept" | educator | 📘 Pedagogy |
| Default (no phrase) | ASTRA | 🧠 Polymathic companion |

---

## 🔧 DEPENDENCIES

Already installed in your environment:
- ✅ Python 3.11+
- ✅ FastAPI 0.115+
- ✅ Uvicorn 0.30+
- ✅ httpx 0.27+
- ✅ Pydantic 2.9+

No additional installation needed!

---

## 🎯 WHAT'S RUNNING

### Main Server (port 8000)

**Purpose**: LLM gateway with identity-aware generation

**Stack**:
- FastAPI app
- Circuit breakers for LLM/memory
- Multi-model router (DeepSeek-V3, Phi-4, Llama-3.2)
- Event store for audit trail
- Policy verifier
- Prometheus metrics

**Identity Integration**:
- Detects activation phrases in messages
- Applies `role_scope()` around LLM calls
- Tags memory events with active role
- Injects role persona into system prompts

### Role API (port 8787)

**Purpose**: Runtime role management & monitoring

**Stack**:
- FastAPI app
- Thread-safe `RoleRuntime` state
- Trace logger (256-event circular buffer)
- CORS middleware
- Static file server for dashboard

**Features**:
- Switch roles via REST API
- List all 12 universal functions
- Invoke functions with JSON args
- View real-time trace log

### Dashboard (http://localhost:8787)

**Purpose**: Live monitoring & control interface

**Stack**:
- Pure HTML/CSS/JavaScript
- HTMX 1.9.10 for reactivity
- No build step required

**UI Elements**:
- Active role display + dropdown switcher
- 12-function table with descriptions
- Function invocation form (code + JSON args)
- Real-time trace log (auto-refresh 3s)
- Gradient dark theme

---

## 📊 SYSTEM HEALTH CHECKS

```powershell
# Check main server
curl http://localhost:8000/health

# Check role API
curl http://localhost:8787/api/health

# Check current role
curl http://localhost:8787/api/roles | ConvertFrom-Json | Select-Object current

# List registered functions
curl http://localhost:8787/api/functions | ConvertFrom-Json | Select-Object -ExpandProperty items
```

---

## 🛠️ TROUBLESHOOTING

### Port Already in Use

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or use different port
python launch_server.py --port 8001
uvicorn app.main:app --port 8788
```

### Import Errors

```powershell
# Verify Python environment
python --version  # Should be 3.11+

# Verify packages
pip list | Select-String "fastapi|uvicorn|httpx|pydantic"

# Re-install if needed
pip install fastapi uvicorn httpx pydantic python-multipart
```

### Role Detection Not Working

```powershell
# Check if identity modules are imported
python -c "from src.astra.core.identity.astra_roles import ROLE_SPECS; print(len(ROLE_SPECS))"
# Should print: 10 (11 roles minus user)

# Check activation phrases in config
python -c "from src.astra.core.identity.astra_roles import ROLE_SPECS; print(ROLE_SPECS['oracle']['activation_phrase'])"
```

---

## 🎨 DASHBOARD FEATURES

### 1. Role Switcher

- Dropdown with all 11 roles
- Shows current active role (green badge)
- Click to switch instantly
- Auto-refreshes every 3 seconds

### 2. Function Explorer

- Table of all 12 universal functions
- Columns: Code | Role Hint | Description
- Copy code to clipboard for easy invocation

### 3. Function Invoker

- Input field for function code
- JSON text area for arguments
- "Invoke" button triggers execution
- Result display with success/error status

### 4. Trace Log

- Real-time event stream
- Shows: Timestamp | Event Type | Payload
- Auto-scrolls to latest
- Updates every 3 seconds
- Last 100 events visible

---

## 📝 USAGE EXAMPLES

### Example 1: Chat with Role Auto-Detection

```python
import httpx

client = httpx.Client()

# Message with "prophetic" keyword → oracle role
response = client.post("http://localhost:8000/chat", json={
    "message": "Give me prophetic insights on crypto markets"
})

print(response.json()["response"])
# Will be generated by oracle persona
```

### Example 2: Manual Role Control

```python
# Switch to creatrix for creative work
client.post("http://localhost:8787/api/role/switch", json={"role": "creatrix"})

# Now all chat responses will use creatrix persona
response = client.post("http://localhost:8000/chat", json={
    "message": "Design a brand identity for a tech startup"
})
```

### Example 3: Function Invocation

```python
# Call ASTRA_INTEL_CORE for strategic analysis
response = client.post(
    "http://localhost:8787/api/functions/ASTRA_INTEL_CORE/invoke",
    json={
        "args": {
            "topic": "AI infrastructure trends",
            "objectives": ["identify opportunities", "risk analysis"]
        }
    }
)

result = response.json()
print(result["result"])
```

---

## 🔐 SECURITY NOTES

### Current Setup (Development)

- ⚠️ No authentication (open access)
- ⚠️ CORS allow all origins
- ⚠️ No rate limiting
- ⚠️ Logs visible to all

**This is intended for local development only.**

### Production Hardening (TODO)

Add before deploying:
1. API key authentication
2. JWT tokens for sessions
3. Rate limiting (10 req/min per IP)
4. CORS restricted to known origins
5. Log redaction (PII filtering)
6. HTTPS only (TLS 1.3+)
7. Request validation & sanitization

---

## 🎉 YOU'RE READY!

**The complete ASTRA Celestial Identity System is now operational.**

Start with:
```powershell
python launch_server.py
```

Then optionally add the dashboard:
```powershell
uvicorn app.main:app --port 8787 --reload
Start-Process "http://localhost:8787"
```

**Welcome to ASTRA v2.5** 🪽

---

**Version**: 2.5  
**Status**: ✅ **READY FOR DEPLOYMENT**  
**Author**: ASTRA Core Team  
**Date**: November 3, 2025
