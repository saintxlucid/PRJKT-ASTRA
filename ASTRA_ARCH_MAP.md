# 🗺️ ASTRA CORE - ARCHITECTURE & MODULE MAP

**Date**: 2025-11-01  
**Repository**: `X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)`  
**Purpose**: Module dependency graph, service interactions, data flows

---

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW

### High-Level Layers

```
┌───────────────────────────────────────────────────────┐
│          PRESENTATION LAYER                            │
│  FastAPI HTTP Endpoints + WebSocket (future)          │
│  Rate Limiting | Circuit Breakers | Metrics           │
└───────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────────────────────────────────┐
│          COGNITIVE LAYER                               │
│  IdentityEngine | AlignmentEngine | PolicyEngine      │
│  PersonaManager | ConsentManager                       │
└───────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────────────────────────────────┐
│          INTELLIGENCE LAYER                            │
│  RAGFusionEngine | MemoryEngine | PlannerL2           │
│  Multi-Query | Reranking | Memory Retrieval           │
└───────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────────────────────────────────┐
│          EXECUTION LAYER                               │
│  Executor | ToolRegistry | TaskAgent | Bridge         │
│  Sandboxed Tool Calls | Capability Guards             │
└───────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────────────────────────────────┐
│          INFRASTRUCTURE LAYER                          │
│  LLM Providers (llamacpp, OpenAI, Anthropic)          │
│  Vector Stores (ChromaDB, Qdrant, SimpleVecDB)        │
│  Databases (SQLite, PostgreSQL)                        │
└───────────────────────────────────────────────────────┘
```

---

## 📦 CORE MODULE CATALOG

### Presentation Layer

**astra_core.py** [`astra_core.py:1-516`]
- FastAPI application entry point
- Rate limiter (token bucket per endpoint)
- Metrics collector (Prometheus format)
- Health checks (/live, /ready, /health/full)
- Graceful shutdown (/drain endpoint)
- **Exports**: `app` (FastAPI instance), `metrics` (MetricsCollector)

**src/astra/api/routes/** [`src/astra/api/routes/*`]
- `bridge.py` — Bridge ingestion, registry, healthz, config
- **Endpoints**: POST /ingest, GET /registry, GET /healthz, POST /config
- **Rate Limits**: Inherited from `astra_core.py` rate limiter

---

### Cognitive Layer

**IdentityEngine** [`src/astra/core/identity_engine.py:55`]
- Loads identity from `config/astra_identity.yaml`
- Injects system prompt + memory context
- Enforces safety boundaries (hard red-lines)
- **Key Methods**: `get_system_prompt()`, `check_safety_boundary()`

**AlignmentEngine** [`src/astra/core/alignment_engine.py:35`]
- Pre-execution plan validation
- Checks plan against identity values
- **Key Methods**: `validate_plan(plan, identity)`

**PolicyEngine** [`src/astra/core/policy_engine.py:87`]
- Consent policy enforcement
- Policy types: `explicit`, `explicit_with_backup`, `red_line`
- **Key Methods**: `check_consent(action, policy)`, `block_red_line(action)`

**PersonaManager** [`src/astra/core/personas.py:8`]
- Multi-persona support (Guardian Engineer, 7 modes)
- **Key Methods**: `load_persona(name)`, `get_active_persona()`

**ConsentManager** [`src/astra/core/planner_l2.py:285`]
- Batched consent requests
- Consent queue + expiration
- **Key Methods**: `request_consent(action)`, `batch_approve(actions[])`

---

### Intelligence Layer

**RAGFusionEngine** [`src/astra/core/rag_fusion.py:25`]
- **Pipeline**:
  1. Multi-query generation (3 variants)
  2. Dense retrieval (FAISS, k_dense=10)
  3. Reciprocal Rank Fusion (RRF k=60)
  4. Nutrition scoring (reranker cascade)
  5. Truncation (1280 token budget)
- **Key Methods**: `retrieve(query, k_final=5)`, `fuse_results(results[])`
- **Config**: [`config/rag.yaml`]

**MemoryEngine** [`src/astra/core/memory_engine.py:67`]
- **3-Tier Architecture**:
  - **Semantic**: Vector store (ChromaDB), user preferences, facts
  - **Episodic**: SQLite, key conversations, emotional moments
  - **Procedural**: SQLite, workflows, task patterns
- **Retrieval Params**:
  - Semantic: top_k=6, similarity_threshold=0.75, boost_recent=0.2
  - Episodic: max_episodes=3, time_decay=0.1
  - Procedural: pattern_threshold=0.8, max_workflows=2
- **Key Methods**: `store(memory, type)`, `retrieve(query, type)`, `consolidate()`
- **Config**: [`config/astra_identity.yaml:82-100`]

**PlannerL2** [`src/astra/core/planner_l2.py`]
- Plan generation + verification
- Multi-step reasoning
- **Key Methods**: `generate_plan(goal)`, `verify_plan(plan)`

---

### Execution Layer

**Executor** [`src/astra/executor/*`]
- Tool execution runtime
- **Gap**: No sandboxing (F-004) — runs with full privileges
- **Recommendation**: Implement chroot/Docker sandbox
- **Key Methods**: `execute_tool(tool_name, args)`, `validate_capability(tool)`

**ToolRegistry** (Location TBD)
- Tool discovery + capability declarations
- **Gap**: No plugin signing (risk: capability misreport)
- **Recommendation**: Add plugin signing, version pinning, allowlist

**TaskAgent** [`src/astra/task/*`]
- Task breakdown + sub-agent routing
- **Future**: Multi-agent task graph (DAG)
- **Key Methods**: `break_down_task(goal)`, `route_to_sub_agent(task)`

**Bridge** [`src/astra/api/routes/bridge.py`]
- External system integration
- **Endpoints**: POST /ingest (ingest data), POST /config (update config)

---

### Infrastructure Layer

**LLM Providers** [`src/astra/infrastructure/llm/*`]
- **llamacpp**: Local GGUF models (gpt-oss-20b)
- **OpenAI**: Cloud fallback (optional)
- **Anthropic**: Cloud fallback (optional)
- **Key Methods**: `generate(prompt, model)`, `stream(prompt, model)`

**Vector Stores**:
- **ChromaDB** [`src/astra/vector_stores/chromadb_store.py`] — Default, local
- **Qdrant** [`src/astra/vector_stores/qdrant_store.py`] — Alternative
- **SimpleVecDB** [`src/astra/vector_stores/simple_store.py`] — Lightweight fallback
- **Recommendation**: Simplify to ChromaDB only (F-006)

**Databases**:
- **SQLite** — Episodic + procedural memory (local)
- **PostgreSQL** (optional) — Production scaling

---

## 🔄 DATA FLOW DIAGRAMS

### Request Flow (HTTP)

```
User Request
    ↓
[FastAPI Entry Point] (astra_core.py)
    ↓
[Rate Limiter] (token bucket check)
    ↓ (429 if rate exceeded)
[Route Handler] (src/astra/api/routes/*)
    ↓
[IdentityEngine] (inject system prompt)
    ↓
[MemoryEngine] (retrieve relevant memories)
    ↓
[RAGFusionEngine] (retrieve docs if needed)
    ↓
[LLM Provider] (generate response)
    ↓
[AlignmentEngine] (validate plan if tools needed)
    ↓
[PolicyEngine] (check consent)
    ↓
[Executor] (execute tools)
    ↓
[Response] (JSON or StreamingResponse)
    ↓
[MetricsCollector] (record latency, errors)
```

### Memory Storage Flow

```
User Interaction
    ↓
[Trigger Check] (IdentityEngine.memory_triggers)
    ↓ (if trigger matches)
[Memory Categorization]
    ├─ Semantic → [Embed] → [ChromaDB]
    ├─ Episodic → [Store] → [SQLite]
    └─ Procedural → [Store] → [SQLite]
    ↓
[Memory Consolidation] (nightly job, future)
    ↓
[Pattern Extraction] → [Procedural Memory]
```

### RAG Retrieval Flow

```
User Query
    ↓
[Multi-Query Generator] (3 variants)
    ↓
[FAISS Dense Index] (k_dense=10)
    ↓
[Reciprocal Rank Fusion] (merge + rerank)
    ↓
[Nutrition Scoring] (custom cascade)
    ↓
[Truncate to Budget] (1280 tokens)
    ↓
[Attach Provenance] (source_docs, future)
    ↓
[Return Chunks]
```

---

## 🕸️ MODULE DEPENDENCY GRAPH

### Core Dependencies

```
astra_core.py
  ├─ FastAPI
  ├─ Uvicorn
  ├─ structlog
  └─ MetricsCollector (internal)

IdentityEngine
  ├─ astra_identity.yaml (config)
  └─ MemoryEngine (retrieval)

MemoryEngine
  ├─ ChromaDB (semantic)
  ├─ SQLite (episodic, procedural)
  └─ IdentityEngine (memory_triggers)
      ⚠️ CIRCULAR DEPENDENCY (F-009)

RAGFusionEngine
  ├─ FAISS (dense index)
  ├─ BGE-M3 embeddings (transformers)
  └─ rag.yaml (config)

PolicyEngine
  ├─ policy.yaml (config)
  └─ IdentityEngine (safety boundaries)

Executor
  ├─ ToolRegistry
  └─ ⚠️ NO SANDBOX (F-004)
```

**Circular Dependency Issue** (F-009):
- `MemoryEngine` imports `IdentityEngine` (for triggers)
- `IdentityEngine` imports `MemoryEngine` (for retrieval)
- **Recommendation**: Extract shared interfaces to `astra.core.interfaces`, use DI

---

## 📊 SERVICE INTERACTION MAP

### Internal Services

```
┌─────────────────┐      ┌─────────────────┐
│  FastAPI App    │◀────▶│  MemoryEngine   │
│  (astra_core.py)│      │  (3-tier store) │
└────────┬────────┘      └─────────────────┘
         │
         ├─────────────▶ ┌─────────────────┐
         │               │ RAGFusionEngine │
         │               │ (retrieval)     │
         │               └─────────────────┘
         │
         ├─────────────▶ ┌─────────────────┐
         │               │ IdentityEngine  │
         │               │ (persona)       │
         │               └─────────────────┘
         │
         └─────────────▶ ┌─────────────────┐
                         │ PolicyEngine    │
                         │ (consent)       │
                         └─────────────────┘
```

### External Integrations

```
┌─────────────────┐
│  ASTRA Core     │
└────────┬────────┘
         │
         ├─────────────▶ LLM Providers
         │               ├─ llamacpp (local)
         │               ├─ OpenAI (cloud, optional)
         │               └─ Anthropic (cloud, optional)
         │
         ├─────────────▶ Vector Stores
         │               ├─ ChromaDB (default)
         │               ├─ Qdrant (alternative)
         │               └─ SimpleVecDB (fallback)
         │
         ├─────────────▶ Databases
         │               ├─ SQLite (local)
         │               └─ PostgreSQL (production, optional)
         │
         └─────────────▶ Monitoring
                         ├─ Prometheus (/metrics endpoint)
                         └─ Grafana (dashboards)
```

---

## 🎯 CRITICAL INTEGRATION POINTS

### 1. Identity → Memory

**Flow**: `IdentityEngine.memory_triggers` → `MemoryEngine.store()`

**Triggers** [`config/astra_identity.yaml:51-58`]:
- User shares personal preferences
- Important decision is made
- User teaches something new
- Emotional moment or turning point
- Repeated pattern emerges
- Explicit "remember this" request

**Code Path**:
```python
# IdentityEngine checks trigger
if self.is_memory_trigger(message):
    memory_type = self.categorize_memory(message)
    memory_engine.store(message, type=memory_type)
```

### 2. RAG → LLM

**Flow**: `RAGFusionEngine.retrieve()` → `LLMProvider.generate(prompt + chunks)`

**Token Budget** [`config/rag.yaml:18-22`]:
- Total: 2048 tokens
- Docs: 1280 tokens (retrieved chunks)
- Query: 256 tokens
- Response: 512 tokens

**Code Path**:
```python
# RAG retrieval
chunks = rag_engine.retrieve(query, k_final=5)
context = truncate(chunks, max_tokens=1280)

# LLM generation
prompt = system_prompt + context + query
response = llm.generate(prompt)
```

### 3. Policy → Executor

**Flow**: `PolicyEngine.check_consent()` → `Executor.execute_tool()` (if approved)

**Policy Types** [`src/astra/core/policy_engine.py`]:
- `explicit`: Require user approval
- `explicit_with_backup`: Require backup artifact first
- `red_line`: Block unconditionally

**Code Path**:
```python
# Pre-execution validation
if policy_engine.is_red_line(action):
    raise BlockedByPolicyError("Red line violated")

if policy_engine.requires_consent(action):
    if not consent_manager.is_approved(action):
        raise ConsentRequiredError()

if policy_engine.requires_backup(action):
    backup_path = create_backup_artifact(action)
    action.backup_artifact = backup_path

# Execute
executor.execute_tool(action.tool, action.args)
```

---

## 🚧 ARCHITECTURAL GAPS

### 1. Circular Dependencies (F-009)

**Current**:
```
MemoryEngine ↔ IdentityEngine (circular)
```

**Recommended**:
```
MemoryEngine → IIdentityProvider (interface)
IdentityEngine → IMemoryStore (interface)
DIContainer → instantiate both with DI
```

### 2. Missing Operator Console (F-013)

**Current**: No UI for plan preview, consent batching, emergency pause

**Recommended Architecture**:
```
┌─────────────────────────────────────────┐
│  Operator Console (Web UI)              │
│  - Plan Preview (show tool calls)       │
│  - Consent Queue (approve/reject batch) │
│  - Live Metrics Dashboard                │
│  - Emergency Pause Button (<5s)         │
└────────────┬────────────────────────────┘
             │ WebSocket
             ↓
┌─────────────────────────────────────────┐
│  FastAPI Backend                         │
│  - /ws/console (WebSocket endpoint)     │
│  - /api/plans (plan preview)            │
│  - /api/consent (approval queue)        │
│  - /api/emergency-pause (kill switch)   │
└─────────────────────────────────────────┘
```

### 3. No Event Sourcing

**Current**: Actions executed without event log

**Recommended Architecture**:
```
┌─────────────────────────────────────────┐
│  Event Log (append-only)                │
│  - timestamp, action, context, result   │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│  Replay API                              │
│  - /api/replay?from=timestamp&to=timestamp │
│  - Step-by-step debugger                │
└─────────────────────────────────────────┘
```

---

## 📐 DEPLOYMENT ARCHITECTURE

### Current (K8s Over-Engineering)

```
┌─────────────────────────────────────────┐
│  Kubernetes Cluster (67 manifests)      │
│  ├─ 15+ Deployments                     │
│  ├─ 8+ HPAs                             │
│  ├─ 10+ NetworkPolicies                 │
│  ├─ 5+ ServiceMonitors                  │
│  └─ 3+ PrometheusRules                  │
└─────────────────────────────────────────┘
```

**Issue** (F-006): 60% unnecessary for single-user deployment

### Recommended (Simplified)

```
┌─────────────────────────────────────────┐
│  Docker Compose (single-user)           │
│  ├─ astra-core (FastAPI app)            │
│  ├─ chromadb (vector store)             │
│  ├─ prometheus (metrics)                │
│  └─ grafana (dashboards)                │
└─────────────────────────────────────────┘
```

**Startup**: `docker-compose up` (< 2 min vs K8s ~15 min)

---

## ✅ ARCHITECTURE ACCEPTANCE CRITERIA

**System passes architecture audit if**:
- [ ] No circular dependencies (verified by import graph analysis)
- [ ] All engines use dependency injection
- [ ] Operator Console MVP operational (:8080/console)
- [ ] Event sourcing operational (replay API)
- [ ] K8s archived to `archive/k8s_for_scale/`
- [ ] Docker Compose startup <2 min
- [ ] All integrations documented in this map

---

## 📁 ARTIFACTS

**Module Catalog**: This document  
**Dependency Graph**: [`analysis/py_symbols.jsonl`] (Python AST)  
**Config Maps**: [`analysis/config_*.normalized.json`]  
**K8s Objects**: [`analysis/k8s_index.json`]  
**API Endpoints**: [`ASTRA_API_ENDPOINTS.csv`]

---

🗺️ **Architecture map complete. All integration points documented.**
