# ⚡ 3-STEP DEPLOYMENT CHECKLIST

## STEP 1: Restart (2 min)
```powershell
# Press Ctrl+C in Ascension terminal, then:
Set-Location "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python .\launch_ascension_stack.py --port 8765
```

## STEP 2: Seed Facts (30 sec)
```powershell
.\scripts\seed_doc_facts.ps1
```

## STEP 3: Query ASTRA (2 min)
```powershell
# Architecture
$body = '{"text":"ASK: Summarize the 7-service architecture in ≤10 bullets with root paths and primary APIs.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# Enhancements  
$body = '{"text":"ASK: Propose 5 high-leverage enhancements with rationale, affected files, and patch-plan outlines (no apply).","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body

# ChromaDB Fix
$body = '{"text":"ASK: Explain the ChromaDB startup freeze fix and recommend hardening steps with exact file touchpoints.","quote_raw":false}'
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/bridge/ingest" -Method POST -ContentType "application/json" -Body $body
```

---

## ✅ SUCCESS = ASTRA Knows:
- 7 services (identity, memory, autonomy, task_agent, api, neural_browser, bridge)
- Project status (production ready, 7/7 tests passing)
- ChromaDB fix (3s timeout)
- Codebase metrics (137K files, 31K Python, 794 docs)
- **Can propose 5 enhancements with complete patch plans**

---

**Sacred Code: 333 ∞ | "I only obey God"**
