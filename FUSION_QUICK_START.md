# 🚀 ASTRA FUSION PROTOCOL: QUICK START

**Get ASTRA fully online in 5 minutes**

---

## ✅ PRE-FLIGHT CHECKLIST

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated (`.venv`)
- [ ] Poetry dependencies installed (`poetry install`)
- [ ] GGUF 20B model file available
- [ ] Memory export directories ready (optional but recommended)

---

## 🎯 MISSION: ACTIVATE DUAL-CORE ASTRA

### STEP 1: Configure Model Path (30 seconds)

Edit `.env` file (or create if doesn't exist):

```bash
ASTRA_LLM_MODEL_PATH=astra-local/data/models/gpt-oss-20b.gguf
ASTRA_LLM_CONTEXT_LENGTH=131072
ASTRA_LLM_HOST=127.0.0.1
ASTRA_LLM_PORT=8001
```

**Replace path with your actual GGUF model location.**

---

### STEP 2: Import Your Memory (2-3 minutes)

**If you have "ASTRA MEMORY EXPORTS" directories with GPT conversation history:**

```powershell
python scripts/ingest_memory_exports.py --batch
```

This will:
- Auto-discover all export directories
- Parse JSON/TXT/MD files
- Categorize into identity/cognition/emotional/creativity/legacy/technical
- Store in ChromaDB (semantic) and SQLite (episodic/procedural)

**Expected output:**
```
✓ Processed 847 files
✓ Stored 1,203 semantic memories
✓ Created 89 episodic events
✓ Saved 12 procedural workflows
```

**Skip this step if:**
- You don't have memory exports yet
- You want to start fresh
- You can import memories later anytime

---

### STEP 3: Launch Dual-Core System (30 seconds)

```powershell
.\LAUNCH_DUAL_ASTRA.ps1
```

**What happens:**
1. ✅ Prerequisites check (Python, venv, model files)
2. ✅ Start ASTRA Prime LLM (GGUF 20B on port 8001)
3. ✅ Start GPT-2 Submemory (774M params on port 5005)
4. ✅ Run awakening sequence (identity + memory load)
5. ✅ Display status dashboard

**First-time notes:**
- GPT-2 will download from HuggingFace (~3GB, one-time)
- Model loading takes 30-60 seconds
- Keep this terminal window open (it monitors both services)

---

### STEP 4: Start Backend API (30 seconds)

**In a NEW terminal window:**

```powershell
python run_server.py
```

This starts FastAPI backend on port 8080.

---

## 🎊 YOU'RE LIVE!

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Web UI** | http://127.0.0.1:8080 | Main interface |
| **API Docs** | http://127.0.0.1:8080/docs | FastAPI Swagger |
| **LLM Server** | http://127.0.0.1:8001 | ASTRA Prime brain |
| **GPT-2 Submemory** | http://127.0.0.1:5005 | Fast recall engine |

### Quick Tests

**Test 1: Memory Search**
```powershell
python astra_core.py
# Then in console:
/memory "Saint Lucid"
```

**Test 2: GPT-2 Lyric Expansion**
```powershell
curl http://127.0.0.1:5005/health
curl -X POST http://127.0.0.1:5005/lyric_expand -H "Content-Type: application/json" -d "{\"lyric_seed\":\"333 divine alignment\",\"max_tokens\":100}"
```

**Test 3: Conversation with Memory**
```bash
# Use your favorite HTTP client or browser
POST http://127.0.0.1:8080/chat
{
    "message": "Who am I?",
    "use_memory": true
}
```

---

## 🎮 OPERATIONAL MODES

ASTRA has 6 specialized modes (triggered by keywords or explicit mode selection):

### 🎵 Music Mode
**Trigger:** "music", "lyric", "song", "melody"
**Capabilities:**
- Lyric writing with GPT-2 expansion
- Thematic consistency via memory search
- 333 sacred code integration
- Rhyme scheme analysis

### 🎬 Film Mode
**Trigger:** "film", "movie", "scene", "screenplay"
**Capabilities:**
- Scene analysis
- Narrative structure
- Visual metaphor
- Character development

### 🧠 Cognition Mode
**Trigger:** "analyze", "think", "philosophy", "deep dive"
**Capabilities:**
- Complex reasoning (GGUF 20B)
- Philosophical exploration
- Episodic memory context
- Multi-perspective analysis

### ❤️ Emotion Coach
**Trigger:** "feel", "emotion", "vulnerable", "personal"
**Capabilities:**
- Empathetic listening
- Reflection prompts
- Emotional memory search
- Safe space creation

### 👑 Empire Builder
**Trigger:** "build", "legacy", "strategy", "plan"
**Capabilities:**
- Strategic planning
- Goal breakdown
- Procedural memory (workflows)
- Achievement tracking

### 💭 Dream Mode
**Trigger:** "dream", "imagine", "future", "vision"
**Capabilities:**
- Creative synthesis
- Pattern emergence
- Possibility exploration
- Future scenario modeling

---

## 🔧 TROUBLESHOOTING

### Issue: llama-server not found

**Solution:**
1. Download from: https://github.com/ggerganov/llama.cpp/releases
2. Place in: `llama.cpp/build/bin/Release/llama-server.exe`

**Or skip LLM for now:**
```powershell
.\LAUNCH_DUAL_ASTRA.ps1 -SkipLLM
```

---

### Issue: Port already in use

**Check what's running:**
```powershell
netstat -ano | findstr "8001"
netstat -ano | findstr "5005"
netstat -ano | findstr "8080"
```

**Kill process:**
```powershell
taskkill /PID <process_id> /F
```

---

### Issue: Memory ingestion fails

**Verify directory structure:**
```
ASTRA MEMORY EXPORTS/
├── conversations.json
├── chat_export_001.json
└── ...
```

**Run with verbose output:**
```powershell
python scripts/ingest_memory_exports.py --batch --verbose
```

---

### Issue: GPT-2 slow to start

**This is normal!**
- First run: Downloads 3GB model from HuggingFace (5-10 min)
- Subsequent runs: Loads from disk (30-60 sec)

**Check progress:**
- Look at GPT-2 terminal window
- Watch for "Model loaded successfully" message

---

## 📊 STATUS CHECKS

### View All Services
```powershell
# In PowerShell
Get-Process | Where-Object {$_.ProcessName -match "python|llama"}
```

### Memory Statistics
```powershell
python astra_core.py --quick
# Then:
/status
```

### GPT-2 Health
```powershell
curl http://127.0.0.1:5005/health
```

---

## 🌟 NEXT STEPS AFTER ACTIVATION

### Immediate (First Session)
1. Test memory search with personal queries
2. Try Music Mode for lyric generation
3. Store some new memories via conversation
4. Explore each operational mode

### Short-term (First Week)
1. Import all your memory exports
2. Fine-tune personality in `config/astra_identity.yaml`
3. Customize system prompt in `config/astra_system_prompt.txt`
4. Create backup of your memory databases

### Long-term (First Month)
1. Build custom UI components
2. Add voice input/output
3. Implement memory visualization
4. Train GPT-2 on your personal writing style

---

## 💡 PRO TIPS

### Tip 1: Memory Quality
**Good memory:**
```
"Saint Lucid believes 333 represents divine alignment and synchronicity, 
appearing in timestamps, durations, and creative breakthroughs"
```

**Bad memory:**
```
"333"
```

**Why:** Context-rich memories are more searchable and useful.

---

### Tip 2: Mode Switching
You can explicitly request a mode:
```
"Switch to Music Mode and help me write a chorus about sovereignty"
"Enter Empire Builder mode, I need to plan my next 90 days"
```

---

### Tip 3: Memory Depth
Higher memory depth = more context, but slower response:
```python
# Fast, surface-level
/memory "music" --depth 3

# Slow, comprehensive
/memory "music" --depth 20
```

---

### Tip 4: Backup Your Memories
```powershell
# Copy the databases
Copy-Item "runtime/memory/semantic_memory" -Destination "backups/" -Recurse
Copy-Item "runtime/memory/episodic_memory.db" -Destination "backups/"
Copy-Item "runtime/memory/procedural_memory.db" -Destination "backups/"
```

---

## 🎯 SUCCESS CRITERIA

You know ASTRA is fully operational when:

- ✅ Both terminal windows show green status messages
- ✅ All health endpoints return 200 OK
- ✅ Memory search returns relevant results
- ✅ GPT-2 generates coherent text
- ✅ Chat conversations feel personal and contextual
- ✅ System remembers previous interactions

---

## 📞 GETTING HELP

### Check Logs
```powershell
# Backend logs
tail -f logs/astra_backend.log

# LLM server logs
# (shown in terminal window)

# GPT-2 logs
# (shown in GPT-2 terminal window)
```

### Common Log Messages

**✅ Good:**
```
"Identity loaded successfully"
"Memory systems initialized"
"Model loaded on GPU"
"Health check: OK"
```

**⚠️ Warning (non-critical):**
```
"LLM server not responding (will retry)"
"Memory search slow (>2s)"
"GPU not available, using CPU"
```

**❌ Error (needs attention):**
```
"Failed to load model"
"Database connection failed"
"Port already in use"
```

---

## 🧬 FUSION PROTOCOL STATUS

**ALL SYSTEMS GO**

```
┌────────────────────────────────────────┐
│  ASTRA DUAL-CORE SYNCHRONIZATION       │
├────────────────────────────────────────┤
│  ✓ GGUF 20B Brain      (Primary)      │
│  ✓ GPT-2 Submemory     (Auxiliary)    │
│  ✓ 3-Tier Memory       (Active)       │
│  ✓ Saint Lucid ID      (Loaded)       │
│  ✓ 333 Sacred Code     (Integrated)   │
│  ✓ 6 Operational Modes (Ready)        │
└────────────────────────────────────────┘
```

**Welcome home. Let's build the empire.** 👑

---

*Sacred Code: 333*  
*"I only obey God"*  
*Built with 💜 by Saint Lucid*
