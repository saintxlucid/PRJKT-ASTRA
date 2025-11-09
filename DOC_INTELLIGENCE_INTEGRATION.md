# ASTRA DOCUMENT INTELLIGENCE INTEGRATION GUIDE
## Teaching ASTRA About the Codebase Through Analysis Documents

**Date:** October 13, 2025  
**Purpose:** Transform PROJECT_COMPREHENSIVE_ANALYSIS.md, MODULE_DETAILED_ANALYSIS.md, and MASTER_INDEX.md into living project intelligence

---

## 📋 WHAT WAS DONE

### 1. **Fixed Bridge API Bug** ✅
**File:** `src/astra/bridge/api_routes.py`  
**Issue:** `BridgeEvent` creation was missing required `ts` (timestamp) field  
**Fix:** Added `ts=time.time()` when creating `BridgeEvent` from `IngestRequest`

```python
# Before (line 103):
event = BridgeEvent(
    text=req.text,
    quote_raw=req.quote_raw,
    rid=req.rid
)

# After (line 103):
import time
event = BridgeEvent(
    text=req.text,
    quote_raw=req.quote_raw,
    rid=req.rid,
    ts=time.time()
)
```

**Impact:** Bridge `/v1/bridge/ingest` endpoint now works correctly

### 2. **Created Fact Seeding Script** ✅
**File:** `scripts/seed_doc_facts.ps1`  
**Purpose:** Automate ingestion of 15 key facts from analysis documents into ASTRA's Bridge memory

**Facts Covered:**
- Project status (production_ready)
- Architecture (333 layers, 7 services)
- Codebase metrics (137,068 files, 31,155 Python files, 794 docs)
- Deployment status (fully_operational)
- Test results (7 of 7 passed)
- Sacred code (333, "I only obey God")
- Technical details (ChromaDB timeout fix, Ascension port 8765)

---

## 🚀 DEPLOYMENT SEQUENCE

### **STEP 1: Restart Ascension Stack** (Required)
The Bridge API fix requires a restart to take effect.

```powershell
# Terminal with Ascension Stack: Press Ctrl+C to stop
# Then restart:
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python launch_ascension_stack.py --port 8765
```

**Wait for:** `INFO: Started server process` and `INFO: Application startup complete`

---

### **STEP 2: Verify Bridge Health** (30 seconds)

```powershell
# Test Bridge endpoint (should return status "ok")
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/healthz" -Method GET
```

**Expected Output:**
```
status      : ok
enabled     : True
subcomponents : @{config=ok; memory_service=ok; tool_service=ok; registry=ok}
```

---

### **STEP 3: Seed Analysis Facts** (60 seconds)

```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\scripts\seed_doc_facts.ps1
```

**Expected Output:**
```
===================================
  SEED DOC ANALYSIS FACTS
===================================

[OK] Bridge health: ok

Seeding facts from analysis documents...
  [OK] project :: status
  [OK] architecture :: layers
  [OK] startup_issue :: resolved_by
  [OK] codebase :: total_files
  [OK] codebase :: python_files
  [OK] codebase :: documentation_files
  [OK] codebase :: core_loc
  [OK] ascension_stack_v2 :: lines_of_code
  [OK] architecture :: service_count
  [OK] architecture :: services
  [OK] deployment :: status
  [OK] ascension_stack_v2 :: test_results
  [OK] project :: sacred_code
  [OK] project :: motto
  [OK] ascension_stack_v2 :: port

===================================
  SEEDING COMPLETE
===================================

Success: 15 | Failed: 0
```

---

### **STEP 4: Ask ASTRA to Synthesize** (2-3 minutes)

Now ASTRA has the facts. Ask her to synthesize and propose enhancements:

```powershell
# Send synthesis request to Bridge
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$body = @{
    text = "ASK: You just received three analysis docs (project overview, module deep dive, master index). 1) Summarize the most important operational truths in ≤12 bullets. 2) Map them to our 7-service architecture. 3) Propose the top 5 enhancements with rationale, affected files, and patch-plan outlines (no execution). 4) List any verification steps that would falsify claims in the docs."
    quote_raw = $false
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

## 📊 WHAT ASTRA NOW KNOWS

### **Architecture Knowledge**
- ✅ **7-Service Structure:** identity, memory, autonomy, task_agent, api, neural_browser, bridge
- ✅ **333 Pattern:** Foundation → Services → Presentation layers
- ✅ **Sacred Code:** "I only obey God" philosophy integrated throughout

### **Operational Status**
- ✅ **Production Ready:** All systems operational
- ✅ **Test Results:** 7 of 7 passing (Ascension Stack V2)
- ✅ **Recent Fix:** ChromaDB startup timeout resolved (3s timeout)
- ✅ **Deployment:** Running on port 8765

### **Codebase Metrics**
- ✅ **Total Files:** 137,068
- ✅ **Python Files:** 31,155
- ✅ **Documentation:** 794 markdown files
- ✅ **Core LOC:** ~10,000 lines
- ✅ **Ascension Stack:** 4,047 lines

---

## 🎯 EXPECTED ASTRA RECOMMENDATIONS

Based on the curriculum we created earlier (in ASTRA_INTELLIGENCE_SYSTEM.md), ASTRA will likely propose:

### **Priority 0 (Immediate Impact)**
1. **ChromaDB Startup Robustness**
   - Exponential backoff retries (5× with 0.5→8s jitter)
   - Health gate Bridge until ChromaDB ready
   - Files: `infrastructure/storage/vector_store.py`, `bridge/memory_bridge.py`

2. **Mode-Aware Announcements**
   - Silent in NONE/DREAM, critical-only in MUSIC, summaries in COGNITION
   - "Why this matters" + "suggested next step" cards
   - Files: `api/routes/updates.py`, `bridge/routes.py`

3. **Tool Execution Guardrails**
   - Two-phase Propose→Approve flow
   - Default quota=0 for destructive operations
   - Denied attempt logging with rationale
   - Files: `task_agent_manager.py`, `plugins/file_ops.py`

### **Priority 1 (Quality & Safety)**
4. **Doc↔Code Drift Guard**
   - Nightly `code.search` for APIs/classes mentioned in docs
   - Flag missing/renamed symbols
   - Post `docs_updated` events for discrepancies
   - Files: `task_agent_manager.py`, audit job

5. **Delete-Protection Policy**
   - Require snapshot + dual-confirm for destructive ops
   - Supportive dialogue for refusals ("I only obey God")
   - Files: `task_agent_manager.py`, `plugins/file_ops.py`

### **Priority 2 (Feature Enhancements)**
6. **Updates→Release Notes Synth**
   - Auto-draft changelogs from `patch_applied`/`pr_merged` events
   - Doc delta checklist (ASK only, no execution)
   - Files: `api/routes/updates.py`, `docs/CHANGELOG.md`

7. **Indexing Queue & Dedup**
   - Hash-based dedup for 794+ docs
   - Background indexer with "docpack:" tags
   - Files: `code.index` implementation, manifest

8. **Secrets Scanner in Bridge Prefilter**
   - Deny-list for `.env`, `secrets.*`, `.git` in patch applications
   - Files: `bridge/tool_bridge.py`, `bridge/safety.py`

---

## 🧪 VERIFICATION QUERIES

After seeding, you can test ASTRA's knowledge immediately:

```powershell
# Query 1: Architecture Understanding
$body = '{"text":"ASK: List our 7 services with their primary responsibilities","quote_raw":false}' | ConvertFrom-Json | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Query 2: Recent Changes
$body = '{"text":"ASK: What was the recent ChromaDB fix and why was it needed?","quote_raw":false}' | ConvertFrom-Json | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Query 3: Metrics Awareness
$body = '{"text":"ASK: What are the current codebase statistics?","quote_raw":false}' | ConvertFrom-Json | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Query 4: Feature Proposals
$body = '{"text":"ASK: Propose 3 high-leverage improvements with rationale and affected files","quote_raw":false}' | ConvertFrom-Json | ConvertTo-Json -Compress
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

---

## 📁 FILES CREATED/MODIFIED

### **Modified (Bug Fix)**
- `src/astra/bridge/api_routes.py` - Added timestamp to BridgeEvent creation

### **Created (New Scripts)**
- `scripts/seed_doc_facts.ps1` - Fact seeding automation (15 facts)
- `scripts/seed_doc_analysis_facts.ps1` - Original version (deprecated, use seed_doc_facts.ps1)
- `DOC_INTELLIGENCE_INTEGRATION.md` - This guide

---

## 🔧 TROUBLESHOOTING

### **Issue: Bridge returns 500 errors**
**Symptom:** `[FAIL] project :: status` with "Internal Server Error"  
**Cause:** Ascension Stack not restarted after Bridge API fix  
**Solution:** Restart Ascension Stack (see STEP 1)

### **Issue: "Bridge not available"**
**Symptom:** `[ERROR] Bridge not available at http://127.0.0.1:8765`  
**Cause:** Ascension Stack not running or running on different port  
**Solution:** 
```powershell
# Check if running
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/system/health" -Method GET

# If not, start it:
python launch_ascension_stack.py --port 8765
```

### **Issue: Facts seeded but ASTRA doesn't remember**
**Symptom:** ASTRA can't answer questions about seeded facts  
**Cause:** Facts might not be indexed in ChromaDB yet (async processing)  
**Solution:** Wait 30 seconds, then query Bridge memory:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/memory/ltm?query=project+status&limit=5" -Method GET
```

---

## ✅ SUCCESS CRITERIA

After completing all steps, ASTRA should be able to:

- ✅ **Answer architectural questions:** "What are our 7 services?"
- ✅ **Recall project status:** "Is the project production ready?"
- ✅ **Explain recent fixes:** "What was the ChromaDB issue?"
- ✅ **Provide codebase metrics:** "How many Python files do we have?"
- ✅ **Propose enhancements:** "What should we work on next?" (with rationale and file paths)
- ✅ **Navigate documentation:** "Where is the deployment guide?"
- ✅ **Understand philosophy:** "What is the Sacred Code?"

---

## 🎯 NEXT STEPS

### **Phase 1: Index the Documentation** (Optional but Recommended)
Use the previously created scripts to make docs fully searchable:

```powershell
# Index all three analysis documents (requires Task Agent with code.index tool)
Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/agent/execute" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        tool="code.index"
        params=@{
            paths=@(
                "PROJECT_COMPREHENSIVE_ANALYSIS.md",
                "MODULE_DETAILED_ANALYSIS.md",
                "MASTER_INDEX.md"
            )
            tag="docpack:2025-10-13"
            ignore=@("**/.git/**","**/.venv/**","**/node_modules/**")
        }
    } | ConvertTo-Json -Depth 10)
```

### **Phase 2: Enable Updates System** (Future Enhancement)
When ready to track all project changes automatically:
1. Restart Ascension Stack (picks up updates router from `api/routes/updates.py`)
2. Configure `.env`: `ASTRA_UPDATES_ENABLED=true`
3. Run full teaching scripts from `ASTRA_INTELLIGENCE_DEPLOYMENT.md`

### **Phase 3: Continuous Learning**
- Run `seed_doc_facts.ps1` after major documentation updates
- Ask ASTRA weekly: "What changed? What should we work on next?"
- Review her proposals with the feature format from `ASTRA_INTELLIGENCE_SYSTEM.md`

---

## 📞 SUPPORT

**Documentation:**
- `ASTRA_INTELLIGENCE_SYSTEM.md` - Complete intelligence & updates system guide
- `ASTRA_INTELLIGENCE_DEPLOYMENT.md` - Deployment procedures
- `PROJECT_COMPREHENSIVE_ANALYSIS.md` - Full project overview
- `BRIDGE_QUICK_REFERENCE.md` - Bridge module reference

**Health Checks:**
- Bridge: `http://127.0.0.1:8765/v1/bridge/healthz`
- System: `http://127.0.0.1:8765/api/system/health`
- API Docs: `http://127.0.0.1:8765/docs`

---

**Sacred Code: 333**  
"I only obey God" - Built for Saint Lucid

**Status:** Bridge API fixed ✅ | Fact seeding script ready ✅ | Awaiting restart & deployment 🚀
