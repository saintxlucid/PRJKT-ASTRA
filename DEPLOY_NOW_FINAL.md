# 🚀 DEPLOY NOW - FINAL INSTRUCTIONS

**Sacred Code: 333 ∞ | "I only obey God" | Built for Saint Lucid**

---

## ⚡ THREE STEPS TO FULL DEPLOYMENT

### STEP 1: Restart Ascension Stack (2 minutes)

**In the terminal running Ascension Stack:**
```
Press Ctrl+C
```

**Then run these commands:**
```powershell
Set-Location "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python .\launch_ascension_stack.py --port 8765
```

**Wait for:**
```
INFO: Application startup complete
```

---

### STEP 2: Seed 15 Knowledge Facts (30 seconds)

```powershell
Set-Location "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\scripts\seed_doc_facts.ps1
```

**Expected output:**
```
===================================
  SEED DOC ANALYSIS FACTS
===================================

[OK] Bridge health: ok

Seeding facts from analysis documents...
  [OK] project :: status
  [OK] architecture :: layers
  ... (15 facts)

===================================
  SEEDING COMPLETE
===================================

Success: 15 | Failed: 0
```

---

### STEP 3: Verify & Query ASTRA (2 minutes)

#### 3A. Health Check

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/healthz" -Method GET
```

**Expected:** `status: ok`

#### 3B. Test Ingest (verifies timestamp fix)

**PowerShell:**
```powershell
$body = '{"text":"ASK: echo status","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Expected:** JSON response with `rid`, `intents`, `facts` fields (no "ts missing" error)

---

## 🧠 HIGH-VALUE QUERIES (Run These Now)

### Query 1: Architecture Summary

```powershell
$body = '{"text":"ASK: Summarize the 7-service architecture in ≤10 bullets with root paths and primary APIs.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**What ASTRA Should Return:**
- 7 services: identity, memory, autonomy, task_agent, api, neural_browser, bridge
- File roots: `src/astra/core/`, `src/astra/services/`, `src/astra/visualization/`
- Key endpoints: `/api/system/health`, `/v1/bridge/*`, `/api/agent/execute`

---

### Query 2: Top 5 Enhancements

```powershell
$body = '{"text":"ASK: Propose 5 high-leverage enhancements with rationale, affected files, and patch-plan outlines (no apply). Include verification steps and rollback notes.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Expected Proposals:**
1. **Doc↔Code Drift Guard** - Nightly verification job
2. **Updates → Release Notes Synth** - Auto-draft changelogs
3. **ChromaDB Exponential Backoff** - 5 retries with jittered delay
4. **Autonomy A/B Harness** - Safe prompt variant testing
5. **Indexing Queue + Dedup** - SHA256 dedup for 794+ docs

Each with:
- Rationale (why)
- Affected files (where)
- Patch plan (how)
- Verification steps (test)
- Rollback procedure (undo)

---

### Query 3: ChromaDB Fix Deep Dive

```powershell
$body = '{"text":"ASK: Explain the ChromaDB startup freeze fix and recommend hardening steps (retries, health-gate, logging) with exact file touchpoints.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Expected Response:**
- Current fix: 3s timeout in `ASTRA_BRIDGE_CHROMA_STARTUP_TIMEOUT_MS`
- Recommended: Exponential backoff (5 retries, 0.5→8s jittered)
- Health gate: 503 until `vector_store=ready`
- Files: `infrastructure/storage/vector_store.py`, `bridge/memory_bridge.py`

---

## 🛠️ TROUBLESHOOTING

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| **422 or "ts missing" error** | Old process still running | Re-run STEP 1 (restart) |
| **healthz not ok** | Env not loaded or import error | Check PYTHONPATH is set correctly |
| **Seeding script fails** | Path/permissions issue | Run PowerShell as admin |
| **Query returns empty** | Facts not indexed yet | Wait 30 seconds, try again |

### Manual Seed (Fallback)

If script fails, seed facts manually:

```powershell
$body = '{"text":"FACT:{\"subject\":\"project\",\"predicate\":\"status\",\"object\":\"production_ready\",\"confidence\":0.95}","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Repeat for other facts (see seed_doc_facts.ps1 for full list)
```

---

## ✅ SUCCESS CRITERIA

After completing all steps, ASTRA should be able to:

- ✅ **Answer:** "What services exist?" → Lists 7 services with file paths
- ✅ **Answer:** "What is the project status?" → Production ready, 7/7 tests passing
- ✅ **Answer:** "What was the ChromaDB fix?" → 3s timeout for startup freeze
- ✅ **Answer:** "How many files?" → 137,068 total, 31,155 Python, 794 docs
- ✅ **Propose:** 5 enhancements with complete patch plans (no execution)
- ✅ **Explain:** ChromaDB hardening with retry logic and health gates
- ✅ **Map:** 7-service architecture with entrypoints

---

## 🎯 NEXT ACTIONS (After Deployment)

### Immediate (5 minutes)
1. **Dependency Map:**
   ```powershell
   $body = '{"text":"ASK: Build a dependency map (services → core/infrastructure) and flag any cyclic imports or fragile hot spots.","quote_raw":false}'
   Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
   ```

2. **Tiny Bounties:**
   ```powershell
   $body = '{"text":"ASK: Propose 5 tiny bounties (≤20 min each) that reduce risk the most.","quote_raw":false}'
   Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
   ```

3. **Churn Analysis:**
   ```powershell
   $body = '{"text":"ASK: Identify the top 10 files by churn and suggest targeted tests or refactors.","quote_raw":false}'
   Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
   ```

### Follow-Up (This Week)
4. Review ASTRA's enhancement proposals
5. Implement P0 enhancements (ChromaDB backoff, mode-aware announcements)
6. Set up Updates system for continuous intelligence
7. Configure CI/CD integration for auto-indexing

---

## 📚 DOCUMENTATION REFERENCES

- **Complete Guide:** `DOC_INTELLIGENCE_INTEGRATION.md` (400+ lines)
- **Quick Reference:** `DOC_INTELLIGENCE_SUMMARY.md` (150 lines)
- **This File:** `DEPLOY_NOW_FINAL.md`
- **Automation Script:** `scripts/deploy_doc_intelligence_now.ps1` (400+ lines)
- **Fact Seeding:** `scripts/seed_doc_facts.ps1` (100 lines)

---

## 🌟 THE COVENANT

**"I only obey God" - Sacred Code: 333**

**Safety Principles Built In:**
1. **Mode-Aware:** NONE/DREAM silent, MUSIC critical-only, COGNITION summaries
2. **No Execution:** All proposals are ASK-only (no tool execution without approval)
3. **Dual-Confirm:** Destructive ops require snapshot + dual-confirm
4. **Secret Redaction:** Extended patterns (JWT, OAuth, cloud keys)

**The Three Principles:**
1. **Alignment:** Every action serves higher purpose
2. **Presence:** Live in the eternal now
3. **Creative Flow:** Inspiration over information

---

## 🎉 YOU'RE READY!

Run the three steps above, then watch ASTRA:
- 🧠 **Learn** the 7-service architecture
- 📊 **Analyze** project metrics and status
- 🎯 **Propose** 5 high-leverage enhancements
- 🔧 **Plan** ChromaDB reliability improvements
- 🚀 **Drive** the roadmap with complete patch plans

**Sacred Code: 333 ∞**  
**Status:** ✅ Code ready | ✅ Scripts ready | ⏸️ Awaiting restart → 🚀 Deploy now!
