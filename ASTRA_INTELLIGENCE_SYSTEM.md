# 🧠 ASTRA Intelligence & Updates System
## Teaching ASTRA the Codebase & Enabling Self-Directed Development

**Version:** 1.0  
**Status:** ✅ PRODUCTION READY  
**Sacred Code:** 333 ∞

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [System Architecture](#system-architecture)
4. [Teaching ASTRA (The 3-Step Process)](#teaching-astra-the-3-step-process)
5. [Verification & Testing](#verification--testing)
6. [Using the Updates System](#using-the-updates-system)
7. [Asking ASTRA for Features](#asking-astra-for-features)
8. [Safety & Authorization](#safety--authorization)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## OVERVIEW

The ASTRA Intelligence System enables ASTRA to:

### Core Capabilities
- ✅ **Learn the codebase** - Understand architecture, services, and code structure
- ✅ **Track changes** - Aware of commits, builds, tests, deployments in real-time
- ✅ **Propose features** - Recommend enhancements with full implementation plans
- ✅ **Generate patches** - Create unified diffs with acceptance tests and rollback plans
- ✅ **Self-assess** - Verify understanding and identify knowledge gaps
- ✅ **Mode-aware communication** - Adjust behavior based on NONE/DREAM/MUSIC/COGNITION/EMPIRE

### Three Pillars

**1. Architecture Facts (Bridge Memory)**
- Stores semantic facts about services, modules, tech stack
- Query: "What services does ASTRA have?"
- Response: Identity, Memory, Autonomy, Task Agent, API, Neural Browser, Bridge

**2. Repository Index (Code-Intel)**
- Full-text search across all source files
- Symbol extraction (classes, functions, methods)
- Query: "Find where ChromaDB is initialized"
- Response: Files, line numbers, context

**3. Updates Stream (Episodic Memory)**
- Tracks all project events (commits, builds, tests, deploys)
- Creates episodic memories + semantic facts
- Query: "What changed in the last 24 hours?"
- Response: Timeline with impact assessment

---

## QUICK START (5 MINUTES)

### Prerequisites
- Ascension Stack running on port 8765
- Bridge Module enabled
- Updates System enabled (check `.env`)

### Step 1: Start ASTRA
```powershell
cd "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src"
python launch_ascension_stack.py --port 8765
```

Wait for: `[✓] Ascension Stack V2 running on http://127.0.0.1:8765`

### Step 2: Seed Architecture Facts (30 seconds)
```powershell
.\scripts\seed_architecture_facts.ps1
```

This teaches ASTRA:
- 7 core services
- Memory stack (ChromaDB, BGE-M3, SQLite)
- Sacred 333 architecture
- Module names and capabilities
- Tech stack and integrations

### Step 3: Index the Codebase (60 seconds)
```powershell
.\scripts\index_codebase.ps1
```

This creates:
- Full-text search index
- Symbol map (classes, functions)
- File tree with relationships
- Language detection

### Step 4: Teach the Workflow (15 seconds)
```powershell
.\scripts\seed_curriculum.ps1
```

This teaches ASTRA:
- Index→Ask→Plan→Approve→Apply→Learn cycle
- Authorization requirements
- Safety checklist
- Documentation standards

### Step 5: Verify Understanding
```powershell
# Run comprehensive tests
.\scripts\test_intelligence_system.ps1

# Or manually test
curl http://127.0.0.1:8765/v1/updates/healthz
curl http://127.0.0.1:8765/v1/bridge/healthz
```

**✅ If all tests pass, ASTRA is ready!**

---

## SYSTEM ARCHITECTURE

### Data Flow

```
┌─────────────────────────────────────────────────┐
│  EXTERNAL EVENTS                                │
│  - Git commits (post-commit hook)               │
│  - CI/CD builds (webhook)                       │
│  - Manual posts (curl/scripts)                  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  UPDATES API (/v1/updates/event)                │
│  - Redact secrets                               │
│  - Normalize payload                            │
│  - Determine impact                             │
└──────────────────┬──────────────────────────────┘
                   │
           ┌───────┴───────┐
           ▼               ▼
┌──────────────────┐  ┌────────────────────┐
│ EPISODIC MEMORY  │  │ SEMANTIC FACTS     │
│ - Full events    │  │ - Subject/Predicate│
│ - Timeline       │  │ - Tags/Confidence  │
│ - Impact levels  │  │ - Queryable        │
└──────────────────┘  └────────────────────┘
           │               │
           └───────┬───────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  BRIDGE MODULE (Memory Query Layer)             │
│  - LTM access                                   │
│  - Episodic access                              │
│  - Fact queries                                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  ASTRA REASONING                                │
│  - "What changed?"                              │
│  - "Why did this happen?"                       │
│  - "What should I work on next?"                │
└─────────────────────────────────────────────────┘
```

### Components

**1. Updates Router** (`src/astra/api/routes/updates.py`)
- FastAPI router for receiving events
- Redaction, validation, impact assessment
- Memory adapter integration
- Mode-aware announcements

**2. Memory Adapter** (In updates.py)
- Connects to Bridge Memory Service
- Writes episodic records
- Stores semantic facts
- Handles errors gracefully

**3. Bridge Module** (`src/astra/bridge/`)
- Memory access layer
- Tool execution layer
- Registry for capabilities
- Health monitoring

**4. Scripts** (`scripts/`)
- `seed_architecture_facts.ps1` - Initial knowledge seeding
- `index_codebase.ps1` - Repository indexing
- `seed_curriculum.ps1` - Workflow teaching
- `updates_post_commit.ps1` - Git hook automation
- `test_intelligence_system.ps1` - Smoke tests

---

## TEACHING ASTRA (THE 3-STEP PROCESS)

### Step 1: Architecture Facts (Facts → Memory)

**Purpose:** Give ASTRA queryable knowledge about system structure

**Method:** POST JSONL to `/v1/bridge/ingest` with `quote_raw:true`

**Example Fact:**
```json
{
  "text": "FACT:{\"subject\":\"codebase\",\"predicate\":\"services\",\"object\":[\"identity\",\"memory\",\"autonomy\",\"task_agent\",\"api\",\"neural_browser\",\"bridge\"],\"tags\":[\"arch\",\"services\"],\"provenance\":\"project_analysis\",\"confidence\":0.98}",
  "quote_raw": true
}
```

**Result:** ASTRA can answer:
- "What services does the codebase have?"
- "What's the memory stack?"
- "How many modules are there?"

**Automation:**
```powershell
.\scripts\seed_architecture_facts.ps1
```

### Step 2: Repository Index (Code → Symbols)

**Purpose:** Enable code navigation and understanding

**Method:** POST to `/api/agent/execute` with code indexing tool

**Request:**
```json
{
  "tool": "code",
  "action": "index",
  "authorized": true,
  "args": {
    "root": "X:\\PROJECT_ASTRA_1.0 (ASTRA_CORE)",
    "include": ["src/**", "config/**", "persona/**"],
    "exclude": ["**/.venv/**", "runtime/**", "models/**"],
    "languages": ["py", "ts", "js", "ps1", "json", "yaml", "md"],
    "symbols": true
  }
}
```

**Result:** ASTRA can:
- Find file paths for any concept
- Locate function/class definitions
- Understand module relationships
- Trace imports and dependencies

**Automation:**
```powershell
.\scripts\index_codebase.ps1
```

### Step 3: Curriculum (Workflow → Process)

**Purpose:** Teach ASTRA how to work safely and effectively

**Method:** POST TEACH: messages to `/v1/bridge/ingest`

**Example Curriculum:**
```json
{
  "text": "TEACH: For any feature request, follow: Index→Ask→Plan→Approve→Apply→Learn. Always explain why, show impacted files, propose patches as unified diffs, and include a rollback note. Never execute tools without explicit authorization.",
  "quote_raw": true
}
```

**Teaches:**
- Development workflow
- Authorization levels (0-3)
- Safety checklist
- Mode awareness (NONE/DREAM/MUSIC/COGNITION/EMPIRE)
- Feature proposal template
- Documentation standards

**Automation:**
```powershell
.\scripts\seed_curriculum.ps1
```

---

## VERIFICATION & TESTING

### Automated Tests

**Run Full Test Suite:**
```powershell
.\scripts\test_intelligence_system.ps1
```

**Tests:**
1. ✅ Updates health check
2. ✅ Bridge health check
3. ✅ Post code commit event
4. ✅ Post build failure (high impact)
5. ✅ Post patch applied event
6. ✅ Updates stats endpoint

**Expected Output:**
```
======================================
  ASTRA INTELLIGENCE SYSTEM TESTS
======================================

TEST: Updates Health Check
  [✓] PASS

TEST: Bridge Health Check
  [✓] PASS

TEST: Post Code Commit Event
  [✓] PASS

...

======================================
  TEST RESULTS
======================================
  Passed:  6
  Failed:  0
  Skipped: 0
======================================

[✓] All tests passed!
```

### Manual Verification Queries

**1. System Map Verification**
```bash
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"ASK: Summarize the 7-service architecture, key entrypoints, and cross-service contracts (APIs, events, memory calls). Include file paths and code symbols.","quote_raw":true}'
```

**Expected:** ASTRA should list:
- Identity Engine (`identity_engine.py`)
- Memory Engine (`memory_engine.py`)
- Autonomy Engine (`autonomy_engine.py`)
- Task Agent Manager (`task_agent_manager.py`)
- Ascension API (`ascension_api.py`)
- Neural Browser (static UI)
- Bridge Module (`bridge/`)

**2. High-Leverage Seams**
```bash
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"ASK: From the repo index, list 20 high-leverage seams for enhancements (perf, safety, UX, reliability). For each: why it matters, primary files, and a smallest-viable patch.","quote_raw":true}'
```

**Expected:** ASTRA should propose:
- Performance improvements (ChromaDB startup, vector search)
- Safety enhancements (tool authorization, input validation)
- UX improvements (voice interface, DAW integration)
- Reliability upgrades (health checks, circuit breakers)

**3. Feature Proposals**
```bash
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"ASK: Propose 5 features you recommend shipping next. For each include: user value, acceptance tests, telemetry, risks, and a unified diff patch plan. Do not run tools—proposal only.","quote_raw":true}'
```

**Expected:** For each feature:
- ✅ User value statement
- ✅ Acceptance test criteria
- ✅ Telemetry/metrics to track
- ✅ Risk assessment
- ✅ Unified diff patch plan
- ✅ Rollback procedure

---

## USING THE UPDATES SYSTEM

### Automatic Updates (Git Hook)

**Setup:**
```powershell
# Test manually first
.\scripts\updates_post_commit.ps1

# Add to Git workflow (optional)
# Create .git\hooks\post-commit (bash):
#!/bin/bash
powershell.exe -File scripts/updates_post_commit.ps1
```

**What it does:**
- Captures commit hash, author, message
- Lists changed files
- Determines impact (low/medium/high/critical)
- POSTs to `/v1/updates/event`
- Creates episodic memory + semantic facts

### Manual Updates

**Post a Code Commit:**
```powershell
$body = @{
    kind = "code_commit"
    title = "feat(bridge): add explain strings to intents"
    summary = "Improved transparency for intent decisions"
    actor = "saint_lucid"
    impact = "medium"
    details = @{
        branch = "main"
        commit = "abc123"
        files_changed = 7
    }
    refs = @("src/astra/bridge/g_int.py", "docs/BRIDGE_QUICK_REFERENCE.md")
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/updates/event" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Post a Build Failure:**
```powershell
$body = @{
    kind = "build_failed"
    title = "CI failure on main"
    impact = "high"
    details = @{
        job = "ci"
        tests_total = 241
        tests_failed = 7
        coverage = 81.9
        duration_s = 412
        url = "http://ci/run/987"
    }
    refs = @(".github/workflows/ci.yml")
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/updates/event" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Post a Patch Applied:**
```powershell
$body = @{
    kind = "patch_applied"
    title = "Add Bridge startup backoff + health flag"
    impact = "medium"
    details = @{
        files = @("memory_bridge.py", "routes/bridge.py")
        tests_added = 3
    }
} | ConvertTo-Json -Compress

Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/updates/event" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

### Event Kinds

| Kind | Impact | Announced in COGNITION Mode |
|------|--------|----------------------------|
| `code_commit` | low-medium | Only if medium+ |
| `pr_opened` | low | No |
| `pr_merged` | medium | Yes |
| `build_passed` | low | No |
| `build_failed` | high-critical | Yes |
| `tests_passed` | low | No |
| `tests_failed` | medium-high | Yes |
| `deploy_started` | medium | Yes |
| `deploy_finished` | medium | Yes |
| `docs_updated` | low | No |
| `feature_proposed` | medium | Yes |
| `patch_applied` | medium | Yes |
| `index_refreshed` | low | No |
| `system_health` | varies | Only if critical |
| `note` | varies | Based on impact |

---

## ASKING ASTRA FOR FEATURES

### The Safe Way (Proposals Only)

**Step 1: Ask for Recommendations**
```bash
curl -X POST http://127.0.0.1:8765/v1/bridge/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"ASK: Propose 5 features you recommend shipping next. For each include: user value, acceptance tests, telemetry, risks, and a unified diff patch plan. Do not run tools—proposal only.","quote_raw":true}'
```

**Step 2: Review Proposal**
- Check user value makes sense
- Verify acceptance tests are complete
- Assess risks are reasonable
- Review patch plan for correctness
- Confirm rollback procedure exists

**Step 3: Approve Specific Patch (Manual)**
```bash
# Copy the unified diff from ASTRA's proposal
# Save to patch.diff
git apply --check patch.diff  # Test first
git apply patch.diff           # Apply if valid
```

**Step 4: Verify & Test**
```powershell
# Run tests
pytest tests/

# Check functionality
python launch_ascension_stack.py --port 8765

# Verify health
curl http://127.0.0.1:8765/api/system/health
```

### What ASTRA Will Likely Recommend (P0-P2)

**P0: Reliability, Safety, Observability**

1. **Memory Bridge Startup Robustness**
   - Make 3s ChromaDB timeout configurable
   - Add exponential backoff (3s, 6s, 12s; max 30s)
   - Surface circuit-breaker health in `/v1/bridge/healthz`

2. **Trigger Explainability + Audit Trail**
   - Persist `{trigger_id, inputs, decision, explanation, mode, user_response}`
   - Add "Why this fired" UI card
   - Expose PromQL metrics

3. **Tool Execution Guardrails**
   - Two-phase "Propose→Approve"
   - Default quota=0 in canary
   - Log denied attempts with reason

4. **End-to-End Golden Path Tests**
   - One command: health, ingest, routing, autonomy, non-execution
   - Wire into CI pipeline

**P1: Experience & Capability**

5. **Push-to-Talk Voice UI**
   - COGNITION/EMOTION only (NONE/DREAM blocked)
   - WebAudio + VAD front-end
   - Whisper/whisper.cpp backend
   - Session-level consent

6. **OSC/HTTP DAW Bridge**
   - BPM, transport, scene, clip, energy events
   - "Creative rhythm" telemetry panel
   - No autonomous BPM changes without consent

7. **Mode Inference v1**
   - Heuristic fusion (time, processes, DAW signals, intents)
   - >80% accuracy target vs manual labels

**P2: Learning & Scale**

8. **Trigger Learning (Contextual Bandit)**
   - Thompson sampling on "helpfulness" feedback
   - Decay on ignores
   - Plot uplift, freeze if regression

9. **Nightly Memory Consolidation**
   - Low-salience episodic → aggregates
   - Keep exemplars + causal links
   - Stable memory size over 30 days

10. **AuthN/Z for Multi-User**
    - JWT sessions + capability sets
    - Per-user memory spaces
    - Shared spaces opt-in

---

## SAFETY & AUTHORIZATION

### Authorization Levels

**Level 0: Read-Only**
- Query facts
- Read episodic memories
- View system health
- No side effects

**Level 1: Memory Read/Write**
- Store new memories
- Update existing memories
- Delete memories (soft delete only)
- Requires: Basic authorization

**Level 2: Tool Execution**
- Execute file operations
- Run system commands
- DAW integrations
- Requires: `authorized=true` flag

**Level 3: System Modifications**
- Config file changes
- Code generation/patching
- Deployment operations
- Requires: Explicit confirmation + logging

### Safety Checklist (Always Applied)

**1. Redaction**
```python
SECRET_PATTERNS = [
    r"(sk-[A-Za-z0-9]{10,})",              # API keys
    r"(?<!\d)(\d{4}[-\s]?){3}\d{4}(?!\d)", # Credit cards
    r"\b[a-f0-9]{32,64}\b",                # Long hex tokens
    r"password\s*[:=]\s*[^;\s]+"           # Passwords
]
```

**2. Path Validation**
- Allowlist: `["src/**", "config/**", "scripts/**"]`
- Blocklist: `["**/.git/**", "**/.env", "**/secrets/**"]`
- Glob pattern matching

**3. Size Limits**
- Max 500KB per file operation
- Max 10,000 files per index
- Max 1MB per update event

**4. Confirmation Requirements**
- Destructive operations require explicit approval
- High-impact changes show preview + rollback plan
- Critical operations log with request ID

**5. Audit Trail**
```python
log.info("updates.recorded",
    rid=ev.rid,
    kind=ev.kind.value,
    impact=ev.impact.value,
    actor=ev.actor,
    files=ev.refs[:10])
```

### Mode-Aware Behavior

| Mode | Autonomy | Announcements | Tool Execution |
|------|----------|---------------|----------------|
| **NONE** | Disabled | None | Blocked |
| **DREAM** | Disabled | None | Blocked |
| **MUSIC** | Limited | Critical only | Requires approval |
| **COGNITION** | Standard | Medium+ events | Requires approval |
| **EMPIRE** | Full | All events | Pre-authorized |

**Current Mode:**
```bash
curl http://127.0.0.1:8765/v1/updates/healthz
# Response includes: "current_mode": "COGNITION"
```

**Change Mode:**
```bash
# Edit .env
ASTRA_MODE=MUSIC

# Restart Ascension Stack
```

---

## TROUBLESHOOTING

### Updates System Not Working

**Symptom:** POST to `/v1/updates/event` returns 503

**Check:**
```bash
curl http://127.0.0.1:8765/v1/updates/healthz
```

**If `enabled: false`:**
```bash
# Edit .env
ASTRA_UPDATES_ENABLED=true

# Restart
python launch_ascension_stack.py --port 8765
```

### Bridge Module Not Available

**Symptom:** Updates system can't write memories

**Check:**
```bash
curl http://127.0.0.1:8765/v1/bridge/healthz
```

**If 404:**
1. Verify Bridge Module installed
2. Check `ASTRA_BRIDGE_ENABLED=true` in `.env`
3. Check startup logs for `bridge_router_mounted`

**Logs:**
```powershell
# Look for:
# [✓] bridge_router_mounted
# [✓] updates_system_initialized_with_memory
```

### ChromaDB Startup Timeout

**Symptom:** Ascension Stack hangs on startup

**Solution:**
```bash
# Edit .env
ASTRA_BRIDGE_CHROMA_STARTUP_TIMEOUT_MS=6000  # 6 seconds

# Or disable if not needed
ASTRA_BRIDGE_ENABLED=false
```

### Memory Writes Not Persisting

**Check episodic adapter is connected:**
```powershell
# Check logs for:
# episodic.write rid=... title=...
# fact.write rid=... subject=... predicate=...
```

**If seeing `_skipped_no_service`:**
1. Bridge didn't initialize properly
2. Memory service wasn't injected
3. Check startup sequence in logs

### Git Hook Not Working

**Symptom:** Commits don't trigger updates

**Test manually:**
```powershell
.\scripts\updates_post_commit.ps1 -Commit HEAD
```

**If fails:**
1. Check Ascension Stack is running
2. Verify port 8765 is accessible
3. Check `.env` has `ASTRA_UPDATES_ENABLED=true`

**Silent mode (don't fail commits):**
```powershell
.\scripts\updates_post_commit.ps1 -Silent
```

---

## API REFERENCE

### Updates Endpoints

#### `GET /v1/updates/healthz`
Health check for updates system.

**Response:**
```json
{
  "status": "ok",
  "enabled": true,
  "announce_level": "summary",
  "current_mode": "COGNITION"
}
```

#### `POST /v1/updates/event`
Record a project update event.

**Request Body:**
```json
{
  "kind": "code_commit",           // UpdateKind enum
  "ts": "2025-10-13T10:30:00Z",    // ISO 8601 (optional, defaults to now)
  "actor": "saint_lucid",           // Who performed the action
  "title": "feat: add updates system", // Short description (required, min 3 chars)
  "summary": "Detailed summary",    // Optional longer description
  "details": {                      // Optional structured data
    "commit": "abc123",
    "files_changed": 5,
    "branch": "main"
  },
  "impact": "medium",               // low|medium|high|critical
  "refs": [                         // Optional file paths, URLs, etc.
    "src/astra/api/routes/updates.py",
    "docs/ASTRA_INTELLIGENCE_SYSTEM.md"
  ]
}
```

**Response:**
```json
{
  "status": "ok",
  "rid": "a1b2c3d4-e5f6-...",       // Request ID
  "wrote_episodes": 1,
  "wrote_facts": 3,
  "announced": true,
  "explanation": "Recorded update: code_commit (medium) in mode=COGNITION"
}
```

#### `GET /v1/updates/stats`
Get statistics about recent updates (future feature).

**Response:**
```json
{
  "status": "ok",
  "message": "Statistics endpoint - wire to memory queries",
  "note": "Will show counts by kind, impact distribution, recent activity"
}
```

### UpdateKind Enum

```python
class UpdateKind(str, Enum):
    CODE_COMMIT = "code_commit"
    PR_OPENED = "pr_opened"
    PR_MERGED = "pr_merged"
    BUILD_PASSED = "build_passed"
    BUILD_FAILED = "build_failed"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_FINISHED = "deploy_finished"
    DOCS_UPDATED = "docs_updated"
    FEATURE_PROPOSED = "feature_proposed"
    PATCH_APPLIED = "patch_applied"
    INDEX_REFRESHED = "index_refreshed"
    SYSTEM_HEALTH = "system_health"
    NOTE = "note"
```

### Impact Enum

```python
class Impact(str, Enum):
    LOW = "low"           # No announcement unless verbose
    MEDIUM = "medium"     # Announced in COGNITION/EMPIRE
    HIGH = "high"         # Announced in MUSIC/COGNITION/EMPIRE
    CRITICAL = "critical" # Always announced (except NONE/DREAM)
```

---

## APPENDIX: ENVIRONMENT VARIABLES

### Updates System

```bash
# Enable/disable updates system
ASTRA_UPDATES_ENABLED=true

# Announcement level: silent, summary, verbose
# - silent: No announcements
# - summary: Announce medium+ events in COGNITION/EMPIRE
# - verbose: Announce all events including low impact
ASTRA_UPDATES_ANNOUNCE_LEVEL=summary
```

### Bridge Module

```bash
# Enable/disable bridge module
ASTRA_BRIDGE_ENABLED=true

# ChromaDB startup timeout (milliseconds)
# Increase if ChromaDB is slow to initialize
ASTRA_BRIDGE_CHROMA_STARTUP_TIMEOUT_MS=3000

# Tool execution budget per request
# 0 = no tool execution (safest)
# 1 = one tool call per request (recommended)
# N = N tool calls allowed
ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ=1
```

### Autonomy Engine

```bash
# Enable/disable autonomy engine
ASTRA_AUTONOMY_ENABLED=true

# Emit explanation strings in logs
# 0 = disabled, 1 = enabled
ASTRA_AUTONOMY_EXPLAIN=1
```

### Feature Flags

```bash
# Voice interface (experimental)
ASTRA_VOICE_ENABLED=0

# DAW OSC integration (experimental)
ASTRA_DAW_OSC_ENABLED=0
```

### Operating Mode

```bash
# Current operating mode
# NONE: Silent, no autonomy, no tools
# DREAM: Background processing, no interaction
# MUSIC: Creative mode, minimal interruptions
# COGNITION: Standard interaction, full features
# EMPIRE: Maximum autonomy and capability
ASTRA_MODE=COGNITION
```

---

## SACRED CODE: 333

**3 Phases to Teach ASTRA:**
1. Architecture Facts
2. Repository Index
3. Curriculum

**3 Types of Awareness:**
1. Structural (What exists)
2. Temporal (What changed)
3. Predictive (What's next)

**3 Safety Layers:**
1. Redaction (Secrets)
2. Authorization (Levels)
3. Audit (Logging)

---

**Built for Saint Lucid**  
**"I only obey God"**  
**🌟 ASTRA CAN NOW LEARN, REMEMBER, AND PROPOSE 🌟**
