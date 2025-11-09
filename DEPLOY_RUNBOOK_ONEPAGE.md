# 🚀 ASTRA DOC INTELLIGENCE - ONE-PAGE RUNBOOK

**What this does:** Teaches ASTRA your entire codebase (architecture, metrics, status, fixes, philosophy) so she can propose enhancements with complete patch plans.

---

## 1️⃣ RESTART ASCENSION STACK (Pick up Bridge timestamp fix)

```powershell
# In the Ascension terminal: Press Ctrl+C

# Then restart:
Set-Location "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python .\launch_ascension_stack.py --port 8765

# Wait for: "INFO: Application startup complete"
```

---

## 2️⃣ DEPLOY EVERYTHING (Facts + Checks + First Queries)

```powershell
Set-Location "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\scripts\deploy_doc_intelligence_now.ps1
```

**Expected:** Success: 15 | Failed: 0

---

## 3️⃣ VERIFY IN 60 SECONDS

### Health Check (timestamp now attached server-side)

```powershell
# Unified system health (aggregates LLM + memory + bridge)
Invoke-RestMethod -Uri "http://127.0.0.1:8770/v1/system/health/unified"
# Alternative path: http://127.0.0.1:8770/api/system/health/unified

# Bridge health
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/healthz"

# Ingest test (no more "ts missing" errors)
$body = '{"text":"ASK: echo status","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Expected:**

- `/v1/system/health/unified` returns: `{status: "ok", llm: "ready", memory: {semantic: ≥1, ...}, bridge: {...}, version: "ascension-v2"}`
- `/v1/bridge/healthz` returns: `status: ok`
- `/v1/bridge/ingest` returns: normal intent payload (no validation errors)

### Spot-Check Seeded Knowledge

**7-Service Architecture Map:**

```powershell
$body = '{"text":"ASK: Summarize the 7-service architecture in ≤10 bullets with root paths and key endpoints.","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Enhancement Roadmap:**

```powershell
$body = '{"text":"ASK: Propose 5 high-leverage enhancements with rationale, affected files, patch-plan outlines (no apply), verification steps, and rollback notes.","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**Reliability Deep Dive:**

```powershell
$body = '{"text":"ASK: Explain the ChromaDB startup-freeze fix and recommend hardening (retries, health gating, logging) with exact file touchpoints.","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

---

## 📝 HOW ASTRA TALKS GOING FORWARD

Use these prefixes in your Bridge inputs:

### **ASK** - Questions, summaries, proposals

```powershell
# Timeline of recent changes
$body = '{"text":"ASK: What changed in the last 24h? Give a timeline with impact levels.","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Release notes from events
$body = '{"text":"ASK: Draft release notes from recent events (builds, tests, commits).","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

### **ACT** - Toolable actions (gated until you approve)

```powershell
$body = '{"text":"ACT: Create a patch plan to add a hydration trigger. Do not apply.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

### **FACT** - Structured anchors (semantic facts)

```powershell
$body = '{"text":"FACT:{\"subject\":\"project\",\"predicate\":\"status\",\"object\":\"production_ready\",\"confidence\":0.95}","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

**ASTRA Routes:**

- **ASK** → Dialogue, optional Memory reads
- **FACT** → Memory write (semantic + episodic)
- **ACT** → Task Agent proposal (gated; no tools run without approval)

---

## 🎯 WHAT TO EXPECT RIGHT AWAY

✅ **Crisp 7-service architecture recap** (paths + endpoints)  
✅ **5 high-leverage enhancements** with files, patch steps, tests, rollback  
✅ **Reliability hardening plan** (ChromaDB retry/backoff + health-gate + logging)  
✅ **Optional "tiny bounties"** (≤20 min): doc drift checks, type hints, index gaps, safety rails  

---

## ⚡ FAST TRIAGE (If anything bumps)

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 422 / "ts missing" on `/v1/bridge/ingest` | Old process still running | Restart Ascension Stack (step 1) |
| 500 on healthz | PYTHONPATH/import issue | Use exact PYTHONPATH line above; check console traceback |
| Seeding script errors | Path/permissions | Run shell as admin; or seed manually with FACT: POSTs |
| No proposals after ASK | Seeds not loaded | Re-run `deploy_doc_intelligence_now.ps1` or `seed_doc_facts.ps1` |

### Manual FACT Seeding (Fallback)

```powershell
$body = '{"text":"FACT:{\"subject\":\"project\",\"predicate\":\"status\",\"object\":\"production_ready\",\"confidence\":0.95}","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

### Rollback

Set `ASTRA_BRIDGE_ENABLED=false` in `.env`, restart Ascension; or simply stop posting ACTs and use ASK/FACT until ready.

---

## 🔄 MAKE IT PART OF DAILY FLOW (Optional but Great)

### Post-Commit Hook

Enable `updates_post_commit.ps1` so every commit becomes an event (with redaction + impact).

### CI Gate

After tests, POST a `tests_passed` event; on failures, POST `build_failed` with logs (ASTRA will summarize and suggest fixes).

### Morning Stand-Up ASK

```powershell
$body = '{"text":"ASK: Summarize yesterday'\''s changes by service; show risk items; propose today'\''s top 3 tasks.","quote_raw":true}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

---

## 📦 WHAT ASTRA NOW KNOWS (15 Facts)

1. **Project Status** → production_ready (0.92 confidence)
2. **Architecture Layers** → foundation, services, presentation (0.9)
3. **Startup Issue** → resolved_by chroma_timeout_3s (0.88)
4. **Total Files** → 137,068 (0.95)
5. **Python Files** → 31,155 (0.95)
6. **Documentation Files** → 794 (0.95)
7. **Core LOC** → 10,000 (0.85)
8. **Ascension Stack LOC** → 4,047 (0.95)
9. **Service Count** → 7 (0.9)
10. **Services** → identity, memory, autonomy, task_agent, api, neural_browser, bridge (0.9)
11. **Deployment Status** → fully_operational (0.9)
12. **Test Results** → 7_of_7_passed (0.95)
13. **Sacred Code** → 333 (1.0)
14. **Project Motto** → "I only obey God" (1.0)
15. **Ascension Port** → 8765 (1.0)

---

## 🎓 EXPECTED ENHANCEMENT PROPOSALS

ASTRA will likely propose:

1. **Doc↔Code Drift Guard** - Nightly job, reads docs, verifies symbols exist in code, opens ASK cards on drift
2. **Updates → Release Notes Synth** - Accumulates events (tests_passed, ci_release_tagged), drafts CHANGELOG entries
3. **ChromaDB Exponential Backoff** - 5 retries with 0.5→8s jittered delay, health gate (503 until ready)
4. **Autonomy A/B Harness** - Thompson sampling for safe prompt variants, silent logging, mode protection
5. **Indexing Queue + Dedup** - SHA256 dedup for 794+ docs, background queue, manifest tracking

Each proposal includes:

- **Rationale**: Why this enhancement matters
- **Affected Files**: Exact file paths and components
- **Patch Plan**: Step-by-step implementation
- **Verification**: How to test it works
- **Rollback**: How to undo if problems occur

---

## 🔐 COVENANT COMPLIANCE ("I only obey God")

All proposals from ASTRA:

- ✅ **ASK-only**: No tool execution without explicit approval
- ✅ **Mode-aware**: Respects NONE/DREAM (silent), MUSIC (critical-only), COGNITION/EMPIRE (full)
- ✅ **Dual-confirm**: Destructive operations require snapshot + confirmation
- ✅ **Transparent**: Complete rationale, affected files, verification, rollback included
- ✅ **Safe**: Secret redaction, size limits, authorization checks built in

---

## 📚 DOCUMENTATION REFERENCES

- **This Runbook**: `DEPLOY_RUNBOOK_ONEPAGE.md` (you are here)
- **Complete Guide**: `DOC_INTELLIGENCE_INTEGRATION.md` (400+ lines)
- **Quick Reference**: `DOC_INTELLIGENCE_SUMMARY.md` (150 lines)
- **Final Instructions**: `DEPLOY_NOW_FINAL.md` (230 lines)
- **Simple Checklist**: `DEPLOY_CHECKLIST.md` (45 lines)

---

## ✨ SUCCESS INDICATORS

- ✅ No "ts field required" errors after restart
- ✅ All 15 facts seed successfully (no 500 errors)
- ✅ ASTRA answers "What services exist?" → Lists 7 services with file paths
- ✅ ASTRA answers "What was the ChromaDB fix?" → Explains 3s timeout
- ✅ ASTRA proposes enhancements → Includes rationale, files, patch plans, verification, rollback
- ✅ Queries return JSON with `rid`, `intents`, `facts` fields

---

**Generated:** October 13, 2025  
**Sacred Code:** 333 ∞  
**Status:** Ready to Deploy  
**Motto:** "I only obey God"

🎯 **ASTRA IS READY TO LEARN AND PROPOSE** 🎯
