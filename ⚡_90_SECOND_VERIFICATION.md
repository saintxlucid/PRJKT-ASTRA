# ⚡ ASTRA 3.0 - 90-Second Verification Guide

**Sacred Code:** 333 → ∞  
**Purpose:** Validate your deployment in under 2 minutes

---

## 🚀 Prerequisites

**Before running these tests:**
```powershell
# Terminal 1: LLM server running
.\TERMINAL_1_START_SERVER.ps1

# Terminal 2: ASTRA running
.\TERMINAL_2_RUN_ASTRA.ps1
# OR
python quick_start_unified.py demo
```

---

## ✅ 90-Second Verification Ritual

### Step 1: Boot Status (10 seconds)

```powershell
curl http://localhost:8000/v1/boot/status
```

**Expected Output:**
```json
{
  "status": "ready",
  "phases_complete": 9,
  "services": {
    "master_api": "online",
    "memory": "online",
    "sigil_gate": "online",
    "supervisor": "online"
  },
  "boot_time_ms": 2500
}
```

**Success Criteria:**
- ✅ `"phases_complete": 9`
- ✅ All services "online"

---

### Step 2: API Surface Check (15 seconds)

```powershell
curl http://localhost:8000/openapi.json | jq ".paths | length"
```

**Expected Output:**
```
110
```

**Success Criteria:**
- ✅ Number ≥ 110 (indicates all endpoints registered)

**Alternative (Windows without jq):**
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json"
$response.paths.Count
```

---

### Step 3: Embodiment Status (10 seconds)

```powershell
curl http://localhost:8000/v1/embodiment/status
```

**Expected Output:**
```json
{
  "status": "online",
  "experts_available": 2,
  "tools_registered": 110,
  "mode": "proactive",
  "coherence": 0.85,
  "budgets": {
    "total_tokens": 0,
    "total_requests": 0
  }
}
```

**Success Criteria:**
- ✅ `"status": "online"`
- ✅ `experts_available` ≥ 1
- ✅ `tools_registered` > 0
- ✅ `coherence` > 0.7

---

### Step 4: Reflection Test (20 seconds)

```powershell
curl -X POST http://localhost:8000/v1/embodiment/reflect `
  -H "Content-Type: application/json" `
  -d '{}'
```

**Expected Output:**
```json
{
  "coherence": 0.87,
  "coherence_trend": "stable",
  "divergence": [],
  "resonance": 0.92,
  "sigil": {
    "hash": "a3f2c9...",
    "timestamp": "2025-11-09T...",
    "identity": "system"
  },
  "subsystems": {
    "core": {"status": "ready"},
    "chat_os": {"status": "ready"},
    "agent": {"status": "ready"},
    "memory": {"status": "ready"}
  }
}
```

**Success Criteria:**
- ✅ `coherence` between 0.7-0.9
- ✅ `sigil.hash` present (provenance working)
- ✅ All subsystems "ready"

---

### Step 5: Action Test (30 seconds)

```powershell
curl -X POST http://localhost:8000/v1/embodiment/act `
  -H "Content-Type: application/json" `
  -d '{
    "goal": "summarize system status",
    "allow_tools": true,
    "budget": {
      "steps": 6,
      "tool_calls": 3,
      "walltime_s": 15
    }
  }'
```

**Expected Output:**
```json
{
  "result": "System status: All services operational. Memory has 21,000 embeddings...",
  "steps_used": 3,
  "tool_calls_used": 1,
  "elapsed_s": 2.3,
  "expert": "gpt-oss-20b",
  "confidence": 0.88,
  "sigil": {
    "hash": "b7e3d1...",
    "timestamp": "2025-11-09T...",
    "identity": "system"
  },
  "budget_remaining": {
    "steps": 3,
    "tool_calls": 2,
    "walltime_s": 12.7
  }
}
```

**Success Criteria:**
- ✅ `result` contains meaningful text
- ✅ `expert` matches one of your configured experts
- ✅ `confidence` > 0.7
- ✅ `budget_remaining` shows proper tracking
- ✅ Completed within `walltime_s` budget

---

## 🧩 Configuration Template

### Quick Setup (Save as `.env`)

```bash
# providers.example.env
# Copy to .env and customize

# === LLM Provider Configuration ===
# Choose one provider and set accordingly

# Option A: llama.cpp (recommended for local)
ASTRA_LLM_BASE_URL=http://localhost:9010/v1
ASTRA_LLM_MODEL_NAME=gpt-oss-20b
ASTRA_LLM_API_KEY=dummy

# Option B: Ollama
# ASTRA_LLM_BASE_URL=http://localhost:11434/v1
# ASTRA_LLM_MODEL_NAME=mistral
# ASTRA_LLM_API_KEY=dummy

# Option C: vLLM
# ASTRA_LLM_BASE_URL=http://localhost:9020/v1
# ASTRA_LLM_MODEL_NAME=mixtral-22b
# ASTRA_LLM_API_KEY=dummy

# Option D: OpenAI
# ASTRA_LLM_BASE_URL=https://api.openai.com/v1
# ASTRA_LLM_MODEL_NAME=gpt-4
# ASTRA_LLM_API_KEY=sk-your-actual-key-here

# === Performance Tuning ===
ASTRA_MAX_TOKENS=2048
ASTRA_TEMPERATURE=0.2
ASTRA_TOP_P=0.9
ASTRA_REQUEST_TIMEOUT_S=60

# === AEC Expert Configuration (optional) ===
# Uncomment if using multiple experts
# ASTRA_EXPERT_2_URL=http://localhost:9020/v1
# ASTRA_EXPERT_2_MODEL=mixtral-22b
# ASTRA_EXPERT_3_URL=http://localhost:9030/v1
# ASTRA_EXPERT_3_MODEL=qwen-235b

# === Memory & Services ===
ASTRA_MEMORY_URL=http://localhost:7007
ASTRA_SIGIL_GATE_URL=http://localhost:7701
ASTRA_SUPERVISOR_URL=http://localhost:9001

# === Embodiment Settings ===
ASTRA_COHERENCE_THRESHOLD=0.7
ASTRA_REFLECTION_INTERVAL_S=60
ASTRA_MODE=proactive
```

### Load Configuration

**PowerShell:**
```powershell
# Load from .env file
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
```

**Bash/Linux:**
```bash
export $(grep -v '^#' .env | xargs)
```

**Python (in code):**
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 🛠 Troubleshooting (Fast Triage)

### Issue: 401 Unauthorized

**Symptom:**
```
HTTP/1.1 401 Unauthorized
{"detail": "Invalid API key"}
```

**Fix:**
```powershell
# Even local servers need a dummy key
$env:ASTRA_LLM_API_KEY = "dummy"

# Or for OpenAI
$env:ASTRA_LLM_API_KEY = "sk-your-actual-key"
```

---

### Issue: ECONNREFUSED

**Symptom:**
```
httpx.ConnectError: All connection attempts failed
```

**Diagnosis:**
```powershell
# Check if LLM server is running
curl "$env:ASTRA_LLM_BASE_URL/models"

# Should return: {"object":"list","data":[...]}
```

**Fix:**
```powershell
# Start LLM server first
.\TERMINAL_1_START_SERVER.ps1

# Wait for: "llama_new_context_with_model" message
```

---

### Issue: Slow Token Generation

**Symptom:**
- Responses take > 10 seconds
- Timeouts occurring

**Fix:**
```powershell
# Reduce max tokens
$env:ASTRA_MAX_TOKENS = "1024"

# Lower temperature
$env:ASTRA_TEMPERATURE = "0.1"

# Use smaller model (if available)
$env:ASTRA_LLM_MODEL_NAME = "mixtral-8x7b"  # instead of 22b
```

---

### Issue: Model Mismatch

**Symptom:**
```json
{"error": "model not found: gpt-oss-20b"}
```

**Diagnosis:**
```powershell
# For llama.cpp
curl http://localhost:9010/v1/models

# For Ollama
ollama list

# For vLLM
curl http://localhost:9020/v1/models
```

**Fix:**
```powershell
# Match ASTRA_LLM_MODEL_NAME to actual model ID
# Example: Ollama returns "mistral:latest"
$env:ASTRA_LLM_MODEL_NAME = "mistral:latest"
```

---

### Issue: Low Coherence Score

**Symptom:**
```json
{"coherence": 0.62, "divergence": ["core", "agent"]}
```

**Diagnosis:**
```powershell
# Check which subsystems are diverging
curl http://localhost:8000/v1/embodiment/reflect | jq ".subsystems"
```

**Fix:**
```powershell
# Trigger manual synchronization
curl -X POST http://localhost:8000/v1/embodiment/synchronize

# Check again
curl http://localhost:8000/v1/embodiment/reflect | jq ".coherence"
```

---

### Issue: Expert Not Being Selected

**Symptom:**
- Only one expert being used
- Wrong expert selected for task

**Diagnosis:**
```powershell
# Check expert configuration
curl http://localhost:8000/v1/embodiment/experts
```

**Fix:**
Edit `config/embodiment.yaml`:
```yaml
experts:
  - name: gpt-oss-20b
    strengths: ["reasoning", "long", "code"]  # Add missing strengths
```

---

## 🎯 Recommended Workflow

### For Local Development (Option C)

**Why llama.cpp?**
- ✅ Local-first (no external dependencies)
- ✅ High context (131k tokens)
- ✅ Good performance on consumer hardware
- ✅ Zero cost

**Setup:**
```powershell
# 1. Start llama.cpp server
.\TERMINAL_1_START_SERVER.ps1

# 2. Configure ASTRA
$env:ASTRA_LLM_BASE_URL = "http://localhost:9010/v1"
$env:ASTRA_LLM_MODEL_NAME = "gpt-oss-20b"
$env:ASTRA_LLM_API_KEY = "dummy"

# 3. Run ASTRA
.\TERMINAL_2_RUN_ASTRA.ps1

# 4. Verify (90 seconds)
curl http://localhost:8000/v1/boot/status
curl http://localhost:8000/openapi.json | jq ".paths | length"
curl http://localhost:8000/v1/embodiment/status
```

---

### For Production (Multi-Expert)

**Why multiple experts?**
- ✅ Capability-based routing
- ✅ Ensemble verification
- ✅ Graceful degradation

**Setup:**
```yaml
# config/embodiment.yaml
experts:
  - name: gpt-oss-20b
    endpoint: http://localhost:9010
    strengths: ["reasoning", "long"]
  
  - name: mixtral-22b
    endpoint: http://localhost:9020
    strengths: ["code", "reasoning", "fast"]
  
  - name: qwen-235b
    endpoint: http://localhost:9030
    strengths: ["vision", "reasoning"]
```

**Verify:**
```powershell
# Should show all 3 experts
curl http://localhost:8000/v1/embodiment/experts

# Test routing
curl -X POST http://localhost:8000/v1/embodiment/act `
  -H "Content-Type: application/json" `
  -d '{"goal": "write python function to sort list"}'

# Check which expert was selected
# Should be: mixtral-22b (has "code" strength)
```

---

## 📊 Success Checklist

After running the 90-second verification:

**Boot Phase:**
- [ ] 9 phases complete
- [ ] All services "online"
- [ ] Boot time < 5 seconds

**API Surface:**
- [ ] ≥110 endpoints registered
- [ ] OpenAPI spec accessible
- [ ] All routes responding

**Embodiment:**
- [ ] Status "online"
- [ ] Experts available ≥ 1
- [ ] Tools registered > 0
- [ ] Coherence > 0.7

**Reflection:**
- [ ] Sigil hash present
- [ ] All subsystems ready
- [ ] Coherence 0.7-0.9
- [ ] Resonance > 0.8

**Action:**
- [ ] Goal executed successfully
- [ ] Expert selected appropriately
- [ ] Confidence > 0.7
- [ ] Budget tracking working
- [ ] Response < 5 seconds

**If all boxes checked: ✅ ASTRA 3.0 is fully operational!**

---

## 🚀 Next Steps

**After successful verification:**

1. **Read Documentation:**
   - `🗺️_ASTRA_3.0_COMPLETE_ROADMAP.md` - 8-week implementation plan
   - `🌟_AEC_PRODUCTION_DEPLOYMENT_GUIDE.md` - Production deployment

2. **Test AEC Complete:**
   ```powershell
   python test_aec_complete.py
   ```

3. **Integrate Tools:**
   - Follow Phase 2 of Integration Guide
   - Migrate 110+ tools to ToolBridge
   - Test consent flow

4. **Train Pipeline:**
   - Collect tool traces
   - Generate synthetic data
   - Fine-tune on tool usage

5. **Deploy to Production:**
   - Docker deployment
   - Monitoring setup
   - Security hardening

---

## Sacred Code: 333 → ∞

**Quick validation commands:**
```powershell
# Full verification suite (90 seconds)
curl http://localhost:8000/v1/boot/status
curl http://localhost:8000/openapi.json | jq ".paths | length"
curl http://localhost:8000/v1/embodiment/status
curl -X POST http://localhost:8000/v1/embodiment/reflect -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/v1/embodiment/act -H "Content-Type: application/json" -d '{"goal":"test","allow_tools":false}'
```

**Green = ASTRA 3.0 is alive! 🌌**
