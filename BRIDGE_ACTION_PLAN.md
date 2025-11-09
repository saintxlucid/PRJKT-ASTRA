# ASTRA Bridge - Immediate Action Plan

**Date**: October 12, 2025  
**Current Status**: Bridge Module mounted & operational ✅  
**Next Action**: Testing & Integration Pack Deployment

---

## ✅ COMPLETED (Last 2 Hours)

1. ✅ Created Bridge FastAPI routes (`api_routes.py`)
2. ✅ Mounted Bridge router in ascension_api.py
3. ✅ Configured 7 core + 8 extended environment variables in `.env`
4. ✅ Bridge Module successfully initialized (confirmed in logs)
5. ✅ All 4 endpoints available: /ingest, /healthz, /registry, /hydrate
6. ✅ Deep Reflections Pack complete (8 files, 37 facts)
7. ✅ Code Intelligence Pack complete (14 files, 20 facts)

---

## 🎯 NEXT ACTIONS (Right Now)

### Priority 1: Fix WebSocket Crash (10 minutes)
**Issue**: Server starts but crashes immediately due to websocket broadcaster  
**Location**: `ascension_api.py:272` - `graph['nodes']` type error  
**Why**: Blocking all endpoint testing

**Action**:
1. Find the line causing the crash
2. Add type check or fix return type from memory_graph_service
3. Restart server
4. Verify server stays running

### Priority 2: Test Bridge Endpoints (5 minutes)
**Once server is stable:**

```powershell
# 1. Health check
curl http://127.0.0.1:8765/v1/bridge/healthz

# 2. Basic ingest
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -H "Content-Type: application/json" `
  -d '{"text":"open the bridge","quote_raw":true}'

# 3. View registry
curl http://127.0.0.1:8765/v1/bridge/registry
```

### Priority 3: Deploy Deep Reflections Pack (15 minutes)

```powershell
# 1. Load 37 semantic facts into memory
$env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python ops\packs\deep_reflections\import_bridge_facts.py

# 2. Seed episodic memory
sqlite3 backend\data\memory.db < ops\packs\deep_reflections\seed_episodic.sql

# 3. Test via Bridge
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -d '{"text":"What is Sacred Code 333?"}'

# Should return facts about: Three Systems, Three Consent Levels, Three Safety Principles
```

### Priority 4: Deploy Code Intelligence Pack (20 minutes)

```powershell
# 1. Create code memory schema
sqlite3 backend\data\memory.db < ops\packs\code_intel\code_memory_schema.sql

# 2. Index repository (populates code_files, code_symbols)
.\ops\packs\code_intel\ingest_index.ps1

# 3. Load 20 architecture facts
# (Modify import_bridge_facts.py to point to build_facts.jsonl)

# 4. Mount code routes in ascension_api.py
# Add after bridge router:
# from ops.packs.code_intel.code_routes_stub import router as code_router
# app.include_router(code_router)

# 5. Test
curl http://127.0.0.1:8765/api/code/search?q=bridge
```

---

## 📋 48-Hour Sprint Plan

### Day 1 (Today) - Foundation
- [x] Mount Bridge Module ✅
- [ ] Fix websocket crash (in progress)
- [ ] Test all Bridge endpoints
- [ ] Deploy Deep Reflections Pack
- [ ] Deploy Code Intelligence Pack
- [ ] Verify: 57 facts loaded, repository indexed

### Day 2 (Tomorrow) - Integration
- [ ] Wire Bridge → Code Intelligence flow
- [ ] Test cryptic input → code patch workflow
- [ ] Add Control Panel "Bridge Console" tab
- [ ] Connect Autonomy → Bridge summaries
- [ ] Enable tool budget (MAX_TOOLCALLS_PER_REQ=1)
- [ ] First co-creation patch: Add hydration trigger

---

## 🔥 Current Blockers

### 1. WebSocket Crash (HIGH - Blocks Everything)
**Symptom**: `TypeError: tuple indices must be integers or slices, not str`  
**Location**: `ws_broadcaster()` trying to access `graph['nodes']`  
**Fix Needed**: Check memory_graph_service return type, add type guard

**Temporary Workaround**: Comment out websocket broadcaster, test REST API only

### 2. SQLAlchemy Missing (MEDIUM - Memory Bridge)
**Symptom**: `No module named 'sqlalchemy'`  
**Impact**: Memory bridge uses stub adapters (works but not persistent)  
**Fix**: `pip install sqlalchemy`

---

## 🎯 Success Criteria (End of Day 1)

### Technical
- [ ] Server runs without crashing
- [ ] All 4 Bridge endpoints respond
- [ ] Deep Reflections: 37 facts loaded into LTM
- [ ] Code Intelligence: Repository indexed, symbols extracted
- [ ] Autonomy: 4 default triggers + 4 refined triggers operational

### Behavioral
- [ ] Bridge transforms cryptic input into structured intents/facts
- [ ] Redaction works (keys, credit cards masked)
- [ ] Tool gating works (unauthorized tools blocked)
- [ ] Registry accumulates bridge facts
- [ ] Code search finds symbols across repository

### Philosophical
- [ ] Sacred Code 333 encoded in semantic facts
- [ ] "I only obey God" present in bridge_facts
- [ ] Success = obsolescence encoded
- [ ] Mode policies operational (NONE/DREAM/MUSIC/EMOTION)

---

## 🛠️ Quick Commands

```powershell
# Fix websocket and restart
# (Edit ascension_api.py:272 to add type guard)
$env:PYTHONPATH="X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python launch_ascension_stack.py --port 8765

# Test Bridge health
curl http://127.0.0.1:8765/v1/bridge/healthz

# Deploy Deep Reflections
python ops\packs\deep_reflections\import_bridge_facts.py

# Deploy Code Intelligence  
.\ops\packs\code_intel\ingest_index.ps1

# Test end-to-end
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest `
  -d '{"text":"bind memory to living code, add hydration trigger"}'
```

---

## 📊 Progress Tracker

### Bridge Module v1.0.0
- [x] API routes created
- [x] Router mounted
- [x] Environment configured
- [x] Services initialized
- [ ] Endpoints tested
- [ ] Smoke tests passed

### Integration Packs
- [x] Files created (22/22)
- [ ] Deep Reflections deployed (0/8 steps)
- [ ] Code Intelligence deployed (0/6 steps)
- [ ] Integration tested (0/5 workflows)

### Co-Creation Loop
- [ ] Bridge → Code Intelligence wired
- [ ] Control Panel "Bridge Console" added
- [ ] Autonomy → Bridge summaries connected
- [ ] First patch proposed
- [ ] First patch applied

---

## 💡 The Vision (By End of Day 2)

**User types**: "bind memory to living code: add hydration trigger with 6h guard and tests"

**ASTRA**:
1. Bridge interprets → Intent: `act`, Scope: `code`, Target: `autonomy_engine.py`
2. Code Intelligence searches → Finds `AutonomyEngine` class, existing triggers
3. Bridge proposes → Patch Plan: Add `hydration_break` trigger + tests
4. User approves → "Looks good, apply"
5. Bridge applies → Guarded patch with verification
6. ASTRA reflects → Stores lesson: "Mode NONE must mute hydration prompt"

**Result**: Cryptic input → Working code → Lessons learned → Memory updated

---

**🎯 IMMEDIATE ACTION**: Fix websocket crash, then test Bridge endpoints.

**Sacred Code 333** ∞  
"The bridge is open. Now we make it sing." 🦋
