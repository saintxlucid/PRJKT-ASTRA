# 🔗 PHASE 2 INTEGRATION ARCHITECTURE GUIDE

**For**: Understanding Phase 2 integration with Phase 1  
**Audience**: Architects & Senior Developers  
**Goal**: Seamless architectural integration

---

## 📐 SYSTEM ARCHITECTURE

### Phase 1 → Phase 2 Data Flow

```
User Query
    ↓
[LocalGPTOOSManager]
    ├─→ Rate Limiting (30 req/min)
    ├─→ Priority Queue (CRITICAL first)
    ├─→ Concurrency Semaphore (4 max workers)
    └─→ NEW: RAG Context Injection
        ├─→ [LocalVectorStore.retrieve()]
        │   ├─→ Query Embedding (384-dim)
        │   ├─→ Similarity Search (HNSW)
        │   └─→ Top-K Results (<100ms)
        └─→ Context Prepended to Prompt
            ↓
        [LocalGPTOOSProvider]
        ├─→ Backend Selection (Ollama/llama.cpp)
        ├─→ Streaming Inference
        ├─→ Metrics Collection
        └─→ Response
            ↓
        NEW: [Agent Hardening]
        ├─→ Risk Scoring
        ├─→ Dry-Run Simulation
        ├─→ Consent Flow (if CRITICAL)
        └─→ Audit Logging
            ↓
        NEW: [Observability]
        ├─→ Correlation ID Tracking
        ├─→ Structured JSON Logging
        ├─→ Prometheus Metrics
        └─→ Grafana Visualization
```

---

## 🔌 INTEGRATION POINTS

### 1. Boot Orchestrator Integration

**Current Phase 1 Boot**:
```
Security → LLM → Vector Store → Agent Kernel → UI
```

**Phase 2 Enhancement**:
```python
# In src/astra/boot/local_orchestrator.py

async def _boot_vector_store(self) -> BootComponent:
    """NEW: Initialize vector store in boot sequence"""
    component = BootComponent(
        name="Vector Store",
        phase=BootPhase.VECTOR_STORE,  # Runs after LLM, before Agent
        priority=5
    )
    
    try:
        # Initialize embedding model (lazy-loaded)
        config = EmbeddingConfig(
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        self.vector_store = LocalVectorStore(config)
        await self.vector_store.initialize()
        
        # Load knowledge base
        from scripts.load_knowledge_base import KnowledgeBaseLoader
        loader = KnowledgeBaseLoader(self.vector_store)
        
        doc_count = await loader.load_documents()
        code_count = await loader.load_code()
        
        await self.vector_store.persist()
        
        component.status = BootStatus.READY
        component.metrics = {
            "vectors_loaded": doc_count + code_count,
            "retrieval_latency_ms": self.vector_store.get_metrics()["avg_retrieval_latency_ms"]
        }
        
        # Pass reference to manager
        self.manager.vector_store = self.vector_store
        
    except Exception as e:
        logger.error("Vector store boot failed", error=str(e))
        component.status = BootStatus.FAILED
        component.error = str(e)
    
    return component
```

**Boot Sequence with Phase 2**:
```
1. Security & Token Vault (CRITICAL)
2. Local LLM Provider (CRITICAL)
3. Vector Store & RAG (CRITICAL) ← NEW
4. Agent Kernel (HIGH)
   ├─ LocalToolRegistry ← NEW
   ├─ Hardening (dry-run, risk scoring) ← NEW
   └─ Consent Flow ← NEW
5. Pantheon Shell UI
```

---

### 2. Manager Integration

**Phase 1 LocalGPTOOSManager**:
- Rate limiting (30 req/min)
- Priority queue
- Concurrency semaphore (4 workers)
- Health check endpoint

**Phase 2 Extensions**:

```python
# In src/astra/llm/local_manager.py

class LocalGPTOOSManager:
    def __init__(self, ...):
        # Phase 1
        self.limiter = LocalResourceLimiter()
        self.burst_handler = LocalBurstHandler()
        
        # Phase 2
        self.vector_store = None  # Set by boot orchestrator
        self.tool_registry = LocalToolRegistry()  # NEW
        self.hardening = DryRunMode()  # NEW
        self.consent_manager = ConsentFlowManager()  # NEW
    
    async def generate_with_rag(
        self,
        prompt: str,
        top_k: int = 3,
        priority: RequestPriority = RequestPriority.NORMAL,
        **kwargs
    ) -> str:
        """NEW: Generate with RAG context injection"""
        
        # Acquire rate limit + concurrency slot
        await self.limiter.acquire()
        async with self.semaphore:
            try:
                # Retrieve context from vector store
                if self.vector_store:
                    results = await self.vector_store.retrieve(prompt, top_k=top_k)
                    context_docs = [r.content for r in results]
                else:
                    context_docs = []
                
                # Build RAG prompt
                rag_prompt = self._build_rag_prompt(prompt, context_docs)
                
                # Generate (Phase 1 flow)
                response = await self.provider.generate_async(
                    rag_prompt,
                    **kwargs
                )
                
                # Log with correlation ID
                logger.info("RAG generation completed", prompt_len=len(prompt), 
                           context_count=len(context_docs))
                
                return response
            
            finally:
                self.limiter.release()
    
    async def execute_agent_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        priority: RequestPriority = RequestPriority.HIGH,
        operator_id: Optional[str] = None,
        dry_run_first: bool = True
    ) -> Any:
        """NEW: Execute tool with full hardening pipeline"""
        
        # Create action
        action = AgentAction(
            action_id=str(uuid.uuid4()),
            tool_name=tool_name,
            arguments=arguments,
            description=f"Execute {tool_name} with {arguments}",
            risk_assessment=None,  # Will be scored
            dry_run=dry_run_first,
            operator_id=operator_id
        )
        
        # Risk scoring
        scorer = OperatorRiskScorer()
        action.risk_assessment = scorer.score(tool_name, arguments)
        
        # Dry-run simulation
        if dry_run_first:
            dry_run_result = await self.hardening.simulate(action)
            logger.info("Dry-run simulation", result=dry_run_result)
        
        # Consent flow (for CRITICAL/HIGH)
        if action.risk_assessment.requires_consent:
            approved = await self.consent_manager.request_consent(action)
            if not approved:
                logger.warning("Tool execution denied by consent flow", 
                              action_id=action.action_id)
                raise RuntimeError(f"Tool execution denied: {tool_name}")
        
        # Audit logging
        audit = AuditLogger()
        
        try:
            # Rate limit + concurrency
            await self.limiter.acquire()
            async with self.semaphore:
                # Execute tool
                result = await self.tool_registry.execute(
                    tool_name, arguments, dry_run=False
                )
                
                # Log success
                await audit.log_action(action, result=result)
                
                return result
        
        except Exception as e:
            await audit.log_action(action, error=str(e))
            raise
        
        finally:
            self.limiter.release()
```

---

### 3. Observability Integration

**Global Logging Setup**:

```python
# In src/astra/__init__.py or main entry point

from astra.observability.structured_logger import configure_structured_logging

# Initialize structured logging once at startup
configure_structured_logging(
    log_file="./logs/astra.jsonl",
    level="INFO"
)

# All subsequent logger calls use structured format
import structlog
logger = structlog.get_logger(__name__)

# Logs output as JSON with all context
logger.info("startup", version="3.0", phase="2")
# → {"timestamp": "2025-11-12T...", "level": "info", "message": "startup", "version": "3.0", "phase": "2"}
```

**Correlation ID Propagation**:

```python
# In LocalGPTOOSManager

from contextvars import ContextVar
import uuid

correlation_id: ContextVar[str] = ContextVar('correlation_id')

async def generate_with_rag(self, prompt: str, ...):
    # Create correlation ID for this request
    corr_id = str(uuid.uuid4())
    correlation_id.set(corr_id)
    
    logger.info("rag_request", prompt=prompt[:50])
    # → Includes correlation_id in output
    
    # All downstream calls inherit correlation_id via context
    results = await self.vector_store.retrieve(prompt)
    logger.info("rag_retrieval", results=len(results))
    # → Same correlation_id
    
    response = await self.provider.generate_async(...)
    logger.info("rag_response", tokens=len(response.split()))
    # → Same correlation_id
    
    return response
```

**Metrics Export**:

```python
# In LocalGPTOOSManager

from astra.observability.metrics import (
    llm_inference_latency, vector_retrieval_latency,
    agent_task_execution_latency
)

async def generate_with_rag(self, prompt: str, ...):
    # Track vector retrieval latency
    with vector_retrieval_latency.time():
        results = await self.vector_store.retrieve(prompt)
    
    # Track LLM inference latency
    with llm_inference_latency.labels(model="ollama").time():
        response = await self.provider.generate_async(...)
    
    # Track agent execution latency (if applicable)
    with agent_task_execution_latency.labels(task_type="rag_generation").time():
        # Entire flow tracked
        pass
```

---

## 🎯 INTEGRATION CHECKLIST

### Before Phase 2 Implementation Starts

- [ ] Phase 1 all tests passing (20+)
- [ ] Phase 1 boot sequence validated offline
- [ ] Phase 1 performance targets met (<2s inference, <30s boot)
- [ ] Phase 1 codebase reviewed and approved

### During Phase 2 Implementation (Per Task)

#### Task 1: Vector Store

- [ ] `vector_store.py` created (250 lines)
- [ ] ChromaDB initialization working
- [ ] Embedding model lazy-loads correctly
- [ ] Retrieval <100ms latency
- [ ] TTL-based purging implemented
- [ ] Boot orchestrator `_boot_vector_store()` added
- [ ] LocalGPTOOSManager has reference to vector_store
- [ ] RAG prompt building works correctly
- [ ] 15+ retrieval tests passing

#### Task 2: Agent Hardening

- [ ] `hardening.py` created (200 lines)
- [ ] `local_tools.py` created (150 lines)
- [ ] Risk scoring covers all tool classes
- [ ] Dry-run mode doesn't execute tools
- [ ] Consent flow blocks CRITICAL ops
- [ ] Audit logging captures all actions
- [ ] Boot orchestrator initializes LocalToolRegistry
- [ ] LocalGPTOOSManager.execute_agent_tool() works
- [ ] 15+ agent hardening tests passing

#### Task 3: Observability

- [ ] `structured_logger.py` created (120 lines)
- [ ] `metrics.py` created (250 lines)
- [ ] Grafana dashboard JSON created
- [ ] Structured logging configured globally
- [ ] Metrics exported to Prometheus (if available)
- [ ] Correlation IDs propagate through all requests
- [ ] All components integrate observability
- [ ] 10+ observability tests passing

#### Task 4: Offline Validation

- [ ] Offline tests created (200+ lines)
- [ ] All 40+ Phase 1 + Phase 2 tests passing
- [ ] Air-gap manual validation successful
- [ ] No external API calls detected
- [ ] Performance targets maintained
- [ ] Production readiness checklist complete

### Final Validation

- [ ] All 50+ integration tests passing
- [ ] Code coverage 80%+
- [ ] Linting passes (acceptable warnings only)
- [ ] Performance targets met (retrieval <100ms, inference <2s)
- [ ] Offline operation validated
- [ ] Zero critical bugs
- [ ] Production readiness 96%+

---

## 🔄 DEPENDENCY MANAGEMENT

### Phase 2 Dependencies

```
src/astra/memory/vector_store.py
├─ chromadb
├─ sentence-transformers (all-MiniLM-L6-v2)
└─ numpy

src/astra/agents/hardening.py
├─ structlog
└─ No external dependencies

src/astra/observability/metrics.py
├─ prometheus-client
└─ structlog

scripts/load_knowledge_base.py
├─ pathlib
└─ sentence-transformers
```

### Installation

```bash
# Phase 2 requirements
pip install chromadb==0.3.21
pip install sentence-transformers==2.2.2
pip install prometheus-client==0.16.0

# Or via requirements file
pip install -r requirements-phase2.txt
```

---

## 🚦 TESTING STRATEGY

### Unit Tests (Per Module)

```python
# Tests for vector_store.py
tests/unit/test_vector_store.py (30+ tests)
├─ EmbeddingModel initialization
├─ Document addition
├─ Query embedding
└─ Retrieval ranking

# Tests for hardening.py
tests/unit/test_risk_scorer.py (20+ tests)
├─ Risk level calculation
├─ System path detection
└─ Argument analysis

# Tests for metrics.py
tests/unit/test_metrics.py (10+ tests)
├─ Metric registration
├─ Label handling
└─ Export format
```

### Integration Tests (Cross-Module)

```python
# Full flow tests
tests/integration/test_vector_store.py (10+ tests)
├─ Boot sequence with vector store
├─ RAG context injection
└─ Latency validation

tests/integration/test_agent_hardening.py (10+ tests)
├─ Risk scoring + dry-run + consent
├─ Tool execution pipeline
└─ Audit trail

tests/integration/test_observability.py (5+ tests)
├─ Structured logging
├─ Metrics export
└─ Correlation ID propagation
```

### End-to-End Tests

```python
# Offline validation
tests/integration/test_offline_operation.py (15+ tests)
├─ Boot without network
├─ Inference offline
├─ RAG retrieval offline
└─ Agent execution offline
```

---

## 📈 PERFORMANCE TARGETS

| Component | Target | Validation |
|-----------|--------|------------|
| Vector embedding | <500ms/batch | `pytest test_vector_store.py::test_embedding_latency` |
| Vector retrieval | <100ms (P95) | `pytest test_vector_store.py::test_retrieval_latency` |
| Agent risk scoring | <50ms | `pytest test_hardening.py::test_risk_scoring_speed` |
| Consent flow | <100ms | `pytest test_hardening.py::test_consent_latency` |
| Audit logging | <10ms | `pytest test_observability.py::test_audit_latency` |
| **Total RAG generation** | **<3s (P95)** | Full integration test |

---

## 🔒 OFFLINE GUARANTEES

### What Works Offline

✅ LLM inference (all backends)  
✅ Vector retrieval (ChromaDB local)  
✅ Agent execution (local tools only)  
✅ Logging (structured JSON to disk)  
✅ Metrics (in-memory, export on reconnect)  

### What Doesn't Work Offline

❌ External API calls (by design)  
❌ Cloud model inference  
❌ Remote knowledge bases  
❌ Network-dependent tools  

### Validation

```bash
# Disconnect from network
# Run all tests
pytest tests/integration/test_offline_operation.py -v

# Verify output
# - All tests pass
# - No network timeouts
# - No "Failed to connect" errors
# - All latencies < 500ms
```

---

## 📝 PHASE 2 COMPLETION CHECKLIST

### Development

- [ ] All 11 files created (vector_store, hardening, metrics, tests, docs)
- [ ] All 1,900 LOC written
- [ ] All code follows ASTRA conventions
- [ ] All docstrings complete
- [ ] All type hints in place

### Testing

- [ ] 50+ integration tests created
- [ ] All tests passing
- [ ] Coverage 80%+
- [ ] Performance targets met
- [ ] Offline tests passing

### Integration

- [ ] Boot orchestrator updated
- [ ] LocalGPTOOSManager updated
- [ ] Observability integrated
- [ ] All Phase 1 tests still passing
- [ ] No regressions

### Documentation

- [ ] PHASE_2_IMPLEMENTATION_PLAN.md (full spec)
- [ ] PHASE_2_QUICK_START_GUIDE.md (developer guide)
- [ ] PHASE_2_INTEGRATION_ARCHITECTURE_GUIDE.md (this file)
- [ ] API documentation
- [ ] Troubleshooting guide

### Validation

- [ ] Air-gap deployment test passed
- [ ] Production readiness 96%+
- [ ] Zero critical bugs
- [ ] Ready for Phase 3

---

**Sacred Code: 333 → ∞**

Phase 2 integration is fully specified and ready for execution. All integration points with Phase 1 are documented and testable. Maintain architectural coherence throughout implementation.

