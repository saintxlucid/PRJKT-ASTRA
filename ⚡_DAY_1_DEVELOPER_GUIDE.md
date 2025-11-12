# 👨‍💻 PHASE 2 DEVELOPER ONBOARDING SHEET

## Welcome to Phase 2 Development! 🚀

This sheet guides you through the first day and gives you everything needed to start immediately.

---

## 📋 PRE-FLIGHT CHECKLIST (Do This First)

### ✅ Prerequisites Setup (30 minutes)

```powershell
# 1. Verify you're in the right workspace
cd "x:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# 2. Check Python version (must be 3.9+)
python --version

# 3. Install Phase 2 dependencies
pip install chromadb sentence-transformers prometheus-client

# 4. Verify Phase 1 still works
pytest tests/integration/ -v

# 5. Create your feature branch
git checkout -b feature/phase-2-vector-store
```

### ✅ Documentation Setup (1 hour)

```
1. Open PHASE_2_QUICK_START_GUIDE.md
   → Read "The 4 Phase 2 Tasks" section (10 min)
   
2. Open PHASE_2_IMPLEMENTATION_PLAN.md
   → Read "Task 1: Vector Store & RAG" section (20 min)
   → Study the code examples in "Create vector_store.py" (20 min)
   
3. Bookmark PHASE_2_INTEGRATION_ARCHITECTURE_GUIDE.md
   → Reference for integration questions
```

---

## 🎯 DAY 1 EXECUTION PLAN

### Morning Session (3-4 hours)

#### 1. Create `src/astra/memory/vector_store.py` (90 minutes)

**File Structure** (from PHASE_2_IMPLEMENTATION_PLAN.md):

```python
# Imports
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime, timedelta

# Data Classes
@dataclass
class EmbeddingConfig:
    """Embedding model configuration"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    device: str = "cpu"

@dataclass
class RetrievalResult:
    """Single retrieval result"""
    document_id: str
    text: str
    similarity_score: float
    metadata: Dict[str, Any]

# Classes
class LocalEmbeddingModel:
    """Lazy-loaded local embedding model"""
    # Implement per spec in IMPLEMENTATION_PLAN.md
    
class LocalVectorStore:
    """ChromaDB-based local vector store"""
    # Implement per spec in IMPLEMENTATION_PLAN.md
```

**What to implement** (follow PHASE_2_IMPLEMENTATION_PLAN.md exactly):
- ✅ `__init__()` - Initialize ChromaDB + model
- ✅ `add_documents()` - Batch add with metadata + TTL
- ✅ `retrieve()` - Semantic search <100ms target
- ✅ `purge_expired()` - TTL-based cleanup
- ✅ `persist()` - Save to disk
- ✅ `get_metrics()` - Return usage statistics

**Check**: You should have ~250 lines of code when done

#### 2. Create `scripts/load_knowledge_base.py` (60 minutes)

**What to implement** (from PHASE_2_IMPLEMENTATION_PLAN.md Task 1):
- ✅ `KnowledgeBaseLoader` class
- ✅ `load_documents()` method
- ✅ `batch_process()` method for efficiency
- ✅ Metadata extraction (title, category, source)
- ✅ TTL assignment (90 days default)

**Check**: You should have ~150 lines of code when done

#### 3. Create `scripts/init_vector_store.py` (30 minutes)

**What to implement** (from PHASE_2_IMPLEMENTATION_PLAN.md Task 1):
- ✅ Initialize vector store
- ✅ Create default collection
- ✅ Set up schema
- ✅ Load sample knowledge base (optional test data)

**Check**: You should have ~100 lines of code when done

### Afternoon Session (2-3 hours)

#### 4. Write Integration Tests (90 minutes)

**Test file**: `tests/integration/test_vector_store.py`

**Tests to implement** (from PHASE_2_IMPLEMENTATION_PLAN.md):

```python
def test_vector_store_initialization():
    """Vector store initializes with ChromaDB and embeddings"""
    
def test_add_documents():
    """Add documents stores vectors and metadata"""
    
def test_retrieval_latency():
    """Retrieval completes in <100ms (P95)"""
    
def test_retrieval_ranking():
    """Most relevant results ranked first"""
    
def test_ttl_purge():
    """Expired documents removed by TTL"""
    
def test_batch_processing():
    """Batch processing works for 100+ documents"""
    
def test_persistence():
    """Vector store persists and loads correctly"""
    
def test_empty_query():
    """Handles empty queries gracefully"""
    
def test_duplicate_documents():
    """Handles duplicate document additions"""
    
def test_metadata_filtering():
    """Filter documents by metadata"""

# ... 5+ more tests from specification
```

**Run tests**:
```powershell
pytest tests/integration/test_vector_store.py -v
```

**Success**: All tests passing, <100ms latency verified

#### 5. Validate Integration (30 minutes)

**Verify Phase 1 still works**:
```powershell
pytest tests/integration/test_local_gpt_oos.py -v
pytest tests/integration/test_boot_orchestrator.py -v
pytest tests/integration/test_manager.py -v
```

**Success**: Zero regressions, all Phase 1 tests passing

---

## 📊 END OF DAY 1 CHECKLIST

- [ ] `src/astra/memory/vector_store.py` created (250 lines)
- [ ] `scripts/load_knowledge_base.py` created (150 lines)
- [ ] `scripts/init_vector_store.py` created (100 lines)
- [ ] `tests/integration/test_vector_store.py` created (15+ tests)
- [ ] All new tests passing
- [ ] All Phase 1 tests still passing
- [ ] <100ms retrieval latency confirmed
- [ ] Code committed to feature branch
- [ ] Ready for Day 2

---

## 🚨 COMMON PITFALLS & HOW TO AVOID THEM

### Pitfall 1: Not Following the Spec
**Problem**: You interpret the spec and implement differently  
**Solution**: Read PHASE_2_IMPLEMENTATION_PLAN.md 3x. Copy-paste class signatures exactly.

### Pitfall 2: Skipping Tests
**Problem**: You skip writing tests, assume it works  
**Solution**: Write all 15+ tests specified. Each test validates one behavior.

### Pitfall 3: Ignoring Performance Target
**Problem**: Your retrieval takes 200ms, you ship anyway  
**Solution**: Run performance test daily. <100ms (P95) is non-negotiable.

### Pitfall 4: Breaking Phase 1
**Problem**: Your changes cause Phase 1 tests to fail  
**Solution**: Run all Phase 1 tests at end of each day. Zero regressions required.

### Pitfall 5: Wrong Integration Point
**Problem**: You implement vector store but don't integrate with boot/manager  
**Solution**: Read PHASE_2_INTEGRATION_ARCHITECTURE_GUIDE.md. Integration is specified.

---

## 🔗 INTEGRATION POINTS (DO NOT MISS THESE)

### Boot Orchestrator Integration (Day 3-4)

The boot orchestrator must call your vector store during boot:

```python
# In LocalBootOrchestrator._boot_vector_store() method (NEW - ADD THIS)
async def _boot_vector_store(self):
    """Boot Phase 3: Initialize vector store with validation"""
    try:
        self.vector_store = LocalVectorStore(
            embedding_config=EmbeddingConfig()
        )
        # Validate retrieval latency
        start = time.time()
        results = await self.vector_store.retrieve("test query")
        latency = (time.time() - start) * 1000
        
        if latency > 100:
            self.logger.warning(f"Vector retrieval latency {latency}ms > 100ms target")
        
        self.components_status["vector_store"] = {
            "status": "ready",
            "latency_ms": latency
        }
    except Exception as e:
        self.logger.error(f"Vector store boot failed: {e}")
        self.components_status["vector_store"] = {"status": "error", "error": str(e)}
```

### LocalGPTOOSManager Integration (Day 3-4)

The manager must have a RAG method:

```python
# In LocalGPTOOSManager (ADD THIS NEW METHOD)
async def generate_with_rag(self, prompt: str, query: str, max_tokens: int = 512) -> str:
    """Generate response using RAG context from vector store"""
    # 1. Retrieve context from vector store
    retrieval_results = await self.vector_store.retrieve(query)
    context = "\n".join([f"- {r.text}" for r in retrieval_results])
    
    # 2. Inject context into prompt
    rag_prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
    
    # 3. Generate response
    response = await self.generate(rag_prompt, max_tokens)
    return response
```

**When to do this**: Day 3-4 (after vector store tests passing)

---

## 📞 HELP & ESCALATION

### If Vector Store Tests Fail
1. Check PHASE_2_IMPLEMENTATION_PLAN.md Task 1 → Vector Store section
2. Verify ChromaDB installed: `pip show chromadb`
3. Verify embeddings loading: `python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"`
4. Check test output for specific errors
5. If stuck: Escalate to architect with test output + error message

### If Performance Target Not Met
1. Verify ChromaDB running (check logs)
2. Check batch_size in EmbeddingConfig (may be too large)
3. Profile latency: Add timing logs around retrieval
4. Check document count (large corpus = slower retrieval)
5. If stuck: Escalate with performance metrics

### If Phase 1 Tests Break
1. Run: `pytest tests/integration/ -v --tb=short`
2. Identify which test broke
3. Check if your changes affected import paths or Phase 1 modules
4. If unrelated: Your changes likely caused regression, investigate
5. If stuck: Escalate with failing test name + error

---

## 🎓 KEY CONCEPTS TO UNDERSTAND

### Semantic Search vs Keyword Search
- **Keyword**: Finds exact word matches (fast, limited)
- **Semantic**: Finds meaning-based matches (slower, accurate)
- **Your Job**: Use sentence-transformers to convert text → embeddings (meaning vectors)

### ChromaDB
- **What**: Local vector database (like SQLite for vectors)
- **How**: Stores embeddings + metadata, retrieves by similarity
- **Your Job**: Implement wrapper that abstracts ChromaDB complexity

### TTL (Time-To-Live)
- **What**: Auto-delete documents after N days
- **Why**: Prevent stale knowledge from accumulating
- **Your Job**: Implement `purge_expired()` that deletes old entries

### Batch Processing
- **What**: Process 32 texts at once instead of 1 at a time
- **Why**: 10x faster than processing individually
- **Your Job**: Implement `batch_process()` in KnowledgeBaseLoader

---

## 📈 SUCCESS METRICS FOR DAY 1

| Metric | Target | How to Verify |
|--------|--------|--------------|
| Files created | 4 | `ls src/astra/memory/` + `ls scripts/` + `ls tests/integration/` |
| Lines of code | 500 total | `wc -l vector_store.py load_knowledge_base.py init_vector_store.py` |
| Tests created | 15+ | `pytest tests/integration/test_vector_store.py --collect-only` |
| Tests passing | 100% | `pytest tests/integration/test_vector_store.py -v` |
| Retrieval latency | <100ms (P95) | `pytest tests/integration/test_vector_store.py::test_retrieval_latency -v` |
| Phase 1 regression | 0 | `pytest tests/integration/test_local_gpt_oos.py -v` |

---

## 🚀 IF YOU FINISH EARLY

If you complete all Day 1 tasks before EOD:

1. **Code Review**: Have another dev review your code
2. **Additional Tests**: Write edge case tests (empty queries, huge documents, etc)
3. **Documentation**: Add docstrings to all methods
4. **Performance**: Profile code, optimize hot paths
5. **Next Task Preview**: Read PHASE_2_IMPLEMENTATION_PLAN.md Task 2 section

---

## 🎯 TOMORROW'S PLAN (Day 2)

After completing Day 1:

1. **Morning**: Integrate vector store with boot orchestrator
2. **Mid-day**: Integrate vector store with LocalGPTOOSManager
3. **Afternoon**: Performance validation & bug fixes
4. **EOD**: Commit & prepare for Days 3 + Task 2

---

## 💎 FINAL REMINDER

> "Complete specification → disciplined execution → guaranteed success"

You have everything you need:
- ✅ Detailed specifications (IMPLEMENTATION_PLAN.md)
- ✅ Integration guidance (ARCHITECTURE_GUIDE.md)
- ✅ Quick reference (this sheet)
- ✅ Clear success criteria
- ✅ Timeline confidence

**Execute with precision. Ask for help early if blocked. Ship Phase 2 on schedule.**

**Sacred Code: 333 → ∞**

Let's build the future of autonomous agents. 🚀
