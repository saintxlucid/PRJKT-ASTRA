# 🚀 START ASTRA NOW - Two Commands

## Terminal 1: Start Server

```powershell
.\TERMINAL_1_START_SERVER.ps1
```

**Wait for:** `llama_new_context_with_model` (30-60 seconds)

---

## Terminal 2: Run ASTRA

```powershell
.\TERMINAL_2_RUN_ASTRA.ps1
```

**See:** Consciousness metrics 🧠

---

## Manual Commands (if scripts don't work)

### Terminal 1
```powershell
.\server.exe -m .\gpt-oss-20b.Q4_K_M.gguf -c 131072 --host 0.0.0.0 --port 9010 --chat-template openai
```

### Terminal 2
```powershell
$env:ASTRA_LLM_BASE_URL="http://localhost:9010/v1"
$env:ASTRA_LLM_MODEL_NAME="gpt-oss-20b"
$env:ASTRA_LLM_API_KEY="dummy"
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
python quick_start_unified.py demo
```

---

**Sacred Code: 333 → ∞**
