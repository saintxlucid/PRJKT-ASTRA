# 🚀 PHASE 2 QUICK-START DEVELOPER GUIDE

**For**: Developers implementing Phase 2  
**Status**: Ready to Execute  
**Duration**: 2-3 weeks  
**Success Criteria**: All tests passing, offline validated, production-ready

---

## 📋 QUICK REFERENCE

### Phase 2 Deliverables (5 Days)

| Task | Files | LOC | Duration | Days |
|------|-------|-----|----------|------|
| Vector Store & RAG | 3 | 500 | 3 days | 1-3 |
| Agent Hardening | 3 | 400 | 2.5 days | 4-6 |
| Observability | 3 | 600 | 2.5 days | 7-9 |
| Offline Validation | 2 | 400 | 2 days | 10-11 |
| **TOTAL** | **11** | **1,900** | **10 days** | - |

### Architecture Integration Points

```
Phase 1 Foundation
├── LocalGPTOOSProvider (LLM inference)
├── LocalGPTOOSManager (concurrency + rate limiting)
└── LocalBootOrchestrator (5-phase boot)
    ↓
Phase 2 Extensions
├── Vector Store (semantic search)
├── Agent Hardening (safety + consent)
└── Observability (tracing + metrics)
    ↓
Phase 3 Autonomous (browser automation + workflows)
```

---

## 🎯 TASK 1: VECTOR STORE & RAG (Days 1-3)

### Step 1.1: Create `src/astra/memory/vector_store.py`

**Target**: 250 lines  
**Time**: 1 day  

**Key Classes**:
- `EmbeddingConfig` - Model configuration
- `LocalEmbeddingModel` - Offline embedding (MiniLM-L6-v2, 22MB)
- `LocalVectorStore` - ChromaDB wrapper with retrieval
- `RetrievalResult` - Query result dataclass

**Checklist**:
- [ ] Lazy-load embedding model on first use
- [ ] ChromaDB initialized with cosine similarity
- [ ] Batch embedding processing (32 texts per batch)
- [ ] Retrieval <100ms target (use HNSW indexing)
- [ ] TTL-based purging (90-day default)
- [ ] Metrics tracking (total_chunks, retrieval_latency_ms)

**Testing**:
```bash
pytest tests/integration/test_vector_store.py::test_retrieval_latency -v
# Expected: <100ms retrieval
```

---

### Step 1.2: Create `scripts/load_knowledge_base.py`

**Target**: 150 lines  
**Time**: 1 day  

**Key Components**:
- `KnowledgeBaseLoader` class
- `load_documents()` - Load .md files from `./docs`
- `load_code()` - Load .py files from `./src`
- `load_conversations()` - Load from memory system
- `_chunk_text()` - Simple 512-token chunker

**Execution**:
```bash
python scripts/load_knowledge_base.py
# Loads docs, code, and conversation history
```

**Integration**: Update boot orchestrator to call this on `_boot_vector_store()`

---

### Step 1.3: Update `local_manager.py`

**Add RAG Context Injection**:

```python
async def generate_with_rag(
    self,
    prompt: str,
    retrieval_contexts: Optional[List[str]] = None,
    priority: RequestPriority = RequestPriority.NORMAL,
    **kwargs
) -> str:
    """Generate with RAG context (10 lines max)"""
    if not retrieval_contexts and hasattr(self, 'vector_store'):
        results = await self.vector_store.retrieve(prompt, top_k=3)
        retrieval_contexts = [r.content for r in results]
    
    rag_prompt = self._build_rag_prompt(prompt, retrieval_contexts)
    return await self.generate(rag_prompt, priority=priority, **kwargs)
```

**Integration Point**: LocalBootOrchestrator passes vector_store reference to manager

---

### Step 1.4: Performance Validation

**Must achieve**:
- ✅ Retrieval latency <100ms (P95)
- ✅ Embedding latency <500ms per batch
- ✅ Memory usage <500MB for 10K vectors
- ✅ Incremental indexing <5s per 100 docs

**Test Command**:
```bash
pytest tests/integration/test_vector_store.py -v --tb=short
```

---

## 🔐 TASK 2: AGENT HARDENING (Days 4-6)

### Step 2.1: Create `src/astra/agents/hardening.py`

**Target**: 200 lines  
**Time**: 1.5 days  

**Key Classes**:
- `RiskLevel` enum (LOW, NORMAL, HIGH, CRITICAL)
- `OperatorRiskScorer` - Score tool operations
- `DryRunMode` - Simulate without execution
- `ConsentFlowManager` - Request + track operator approval
- `AuditLogger` - Log all actions to JSONL

**Risk Scoring Logic**:
- Analyze tool name + arguments
- Check for system paths (/etc, /bin, C:\Windows)
- Check for recursive/wildcard patterns
- Escalate dangerous operations to CRITICAL

**Consent Policy**:
- CRITICAL: Always require explicit consent
- HIGH: Require consent for write/delete
- NORMAL: Auto-approve, log action
- LOW: Silent execution

**Checklist**:
- [ ] Risk scoring covers all tool classes
- [ ] Dry-run doesn't modify state
- [ ] Consent requests timestamped + timeout-able
- [ ] Audit trail includes operator_id + timestamp
- [ ] All 4 classes fully implemented

---

### Step 2.2: Create `src/astra/agents/local_tools.py`

**Target**: 150 lines  
**Time**: 1 day  

**Key Component**:
- `LocalToolRegistry` class
- Register safe local tools (read_file, list_dir, get_cpu_info, etc.)
- `execute()` method with risk scoring + dry-run support

**Default Tools**:
- `read_file` (LOW risk)
- `list_dir` (LOW risk)
- `get_cpu_info` (LOW risk)
- `get_memory_info` (LOW risk)
- `search_knowledge` (LOW risk via vector store)

**Checklist**:
- [ ] All tools registered with risk level
- [ ] Risk scoring applied on execute()
- [ ] Dry-run returns fake result
- [ ] Tool handlers properly typed

---

### Step 2.3: Integration with Manager

**Add to LocalGPTOOSManager**:

```python
async def execute_agent_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
    require_consent: bool = False,
    priority: RequestPriority = RequestPriority.HIGH
) -> Any:
    """Execute tool with hardening"""
    # Risk scoring + dry-run + consent flow
    # Uses LocalToolRegistry internally
```

---

### Step 2.4: Testing

**Commands**:
```bash
pytest tests/integration/test_agent_hardening.py::test_risk_scoring -v
pytest tests/integration/test_agent_hardening.py::test_dry_run_simulation -v
pytest tests/integration/test_agent_hardening.py::test_consent_flow -v
```

---

## 📊 TASK 3: OBSERVABILITY EXPANSION (Days 7-9)

### Step 3.1: Create `src/astra/observability/structured_logger.py`

**Target**: 120 lines  
**Time**: 1 day  

**Setup**:
```python
from astra.observability.structured_logger import configure_structured_logging

configure_structured_logging(
    log_file="./logs/astra.jsonl",
    level="INFO"
)
```

**Result**: All logs output as structured JSON with correlation IDs

---

### Step 3.2: Create `src/astra/observability/metrics.py`

**Target**: 250 lines  
**Time**: 1 day  

**Metrics to Export**:
- `llm_inference_latency_ms` (histogram: 100-5000ms buckets)
- `vector_retrieval_latency_ms` (histogram: 10-250ms buckets)
- `agent_task_execution_latency_ms` (histogram)
- `gpu_memory_usage_bytes` (gauge)
- `cpu_utilization_percent` (gauge)

**Integration**:
```python
from astra.observability.metrics import llm_inference_latency

# In local_provider.py
with llm_inference_latency.labels(model="ollama").time():
    response = await provider.generate(prompt)
```

---

### Step 3.3: Create Grafana Dashboard

**File**: `config/grafana_dashboards.json` (400 lines)

**Dashboard Panels**:
- LLM Inference P95 Latency
- Vector Retrieval Latency
- Agent Task Success Rate
- GPU Memory Usage
- Request Queue Depth
- Error Rate by Type

**Setup**:
```bash
# Import to Grafana UI or via API
curl -X POST http://localhost:3000/api/dashboards/db \
  -d @config/grafana_dashboards.json
```

---

### Step 3.4: Correlation ID Tracing

**Add to request flow**:

```python
import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar('correlation_id')

# In LocalGPTOOSManager.generate()
corr_id = str(uuid.uuid4())
correlation_id.set(corr_id)

# All logs in this context include correlation_id
logger.info("LLM request", prompt=prompt)  # Includes corr_id
logger.info("RAG retrieval", query=query)  # Includes corr_id
logger.info("Response generated", tokens=output)  # Includes corr_id
```

---

## 🧪 TASK 4: OFFLINE VALIDATION (Days 10-11)

### Step 4.1: Write Offline Tests

**File**: `tests/integration/test_offline_operation.py` (200+ lines)

**Key Tests**:
- `test_offline_boot_sequence()` - Boot works completely locally
- `test_offline_inference()` - LLM inference <2s
- `test_offline_rag()` - Vector retrieval <100ms
- `test_offline_agent_execution()` - Agents work offline
- `test_no_external_api_calls()` - Verify no network access

**Execution**:
```bash
pytest tests/integration/test_offline_operation.py -v
# All tests should pass with network disconnected
```

---

### Step 4.2: Air-Gap Validation

**Manual Test**:
1. Disconnect from network (WiFi + ethernet)
2. Start ASTRA: `python -m astra.boot.local_orchestrator`
3. Run inference: `curl http://localhost:8000/api/generate -d "test"`
4. Verify response <2s and correct

**Success Criteria**:
- ✅ All components boot successfully
- ✅ Inference completes without timeout
- ✅ RAG retrieval works
- ✅ Agents execute safely

---

## 🔄 INTEGRATION CHECKLIST

### Integration with Phase 1

- [ ] Vector store initialized in boot orchestrator `_boot_vector_store()`
- [ ] LocalGPTOOSManager references vector_store for RAG
- [ ] Agent hardening integrated with tool execution
- [ ] All metrics exported to Prometheus (if available)
- [ ] Structured logging configured globally

### Integration Points

```
LocalBootOrchestrator
├── _boot_security()
├── _boot_local_llm() → LocalGPTOOSProvider
├── _boot_vector_store() → LocalVectorStore + loader
├── _boot_agent_kernel() → LocalToolRegistry + hardening
└── _boot_ui()

LocalGPTOOSManager
├── generate() → metrics + logging
├── generate_with_rag() → vector_store.retrieve()
└── execute_agent_tool() → hardening + risk scoring
```

---

## ✅ VALIDATION GATES

### Gate 1: Component Tests (Day 5)
- [ ] All vector store tests pass
- [ ] All agent hardening tests pass
- [ ] Latency targets met

### Gate 2: Integration Tests (Day 8)
- [ ] Boot orchestrator includes new components
- [ ] Manager uses vector store for RAG
- [ ] Metrics export to Prometheus
- [ ] All 40+ integration tests pass

### Gate 3: Offline Validation (Day 11)
- [ ] Offline tests passing
- [ ] Air-gap manual validation successful
- [ ] No external dependencies
- [ ] Production readiness 96%+

---

## 📊 SUCCESS METRICS

| Metric | Target | Validation |
|--------|--------|------------|
| Vector retrieval latency | <100ms | `pytest test_vector_store.py::test_retrieval_latency` |
| Agent dry-run | Works correctly | `pytest test_agent_hardening.py::test_dry_run` |
| Offline operation | 100% | Disconnect network + boot |
| Integration tests | 40+ passing | `pytest tests/integration/ -v` |
| Code coverage | 80%+ | `pytest --cov=src tests/` |
| Production readiness | 96%+ | Review checklist |

---

## 📚 DEVELOPER RESOURCES

### Key Files Created
- PHASE_2_IMPLEMENTATION_PLAN.md (full spec)
- PHASE_2_QUICK_START_GUIDE.md (this file)
- PHASE_2_INTEGRATION_GUIDE.md (integration details)

### Execution Timeline
- **Day 1-3**: Vector Store & RAG
- **Day 4-6**: Agent Hardening  
- **Day 7-9**: Observability
- **Day 10-11**: Offline Validation
- **Day 12+**: Buffer for fixes & hardening

### Command Reference

```bash
# Initialize Phase 2 environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-phase2.txt

# Run all Phase 2 tests
pytest tests/integration/ -v --tb=short

# Performance validation
pytest tests/integration/test_vector_store.py::test_retrieval_latency -v
pytest tests/integration/test_offline_operation.py -v

# Coverage report
pytest --cov=src --cov-report=html tests/

# Integration test suite
pytest tests/integration/test_local_gpt_oos.py -v  # Phase 1
pytest tests/integration/test_vector_store.py -v  # Phase 2 - RAG
pytest tests/integration/test_agent_hardening.py -v  # Phase 2 - Safety
pytest tests/integration/test_offline_operation.py -v  # Phase 2 - Offline
```

---

**Sacred Code: 333 → ∞**

Phase 2 is fully specified and ready for execution. Follow this guide sequentially, validate at each gate, and maintain integration with Phase 1 throughout. All success criteria are measurable and testable.

Good luck! 🚀
