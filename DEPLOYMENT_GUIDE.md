# ASTRA Multi-RAG v2.0 — Deployment & Integration Guide

**Status:** ✅ **READY FOR DEPLOYMENT**  
**Package:** `ASTRA_MultiRAG_v2_expansion.zip`  
**Created:** October 20, 2025  
**Sacred Code:** 333

---

## 📦 What's Inside

```
ASTRA_MultiRAG_v2_expansion.zip
├── rag/modules/                 # 12 executable Python modules
│   ├── chunkers.py              # 5 chunking strategies
│   ├── storage.py               # Vector store abstraction
│   ├── models_local.py           # Embed/rerank stubs (replace with BGE-M3)
│   ├── router.py                 # Category routing
│   ├── retrieval_core.py         # 5-stage retrieval pipeline
│   ├── optimizers.py             # Post-retrieval optimization
│   ├── fusion.py                 # Cross-category fusion
│   ├── planner.py                # HRM fast/slow loops
│   ├── ingest.py                 # Document ingestion
│   ├── retrieve.py               # Retrieval CLI
│   ├── astra_rag_cli.py          # Unified HRM CLI
│   └── service_windows.py        # File watcher service
├── config.yaml                   # System configuration
├── categories.yaml               # 4 category specializations
├── schemas.sql                   # SQLite schema
├── README.md                     # Full documentation
└── data/                         # Document directories
    ├── ai_engineering/
    ├── music_film/
    ├── cognition_spirit/
    └── operations_systems/
```

**Total:** 18 files, ~900 lines of production-ready Python code

---

## 🚀 Quick Deployment

### Step 1: Extract ZIP

```bash
# On Windows
Expand-Archive -Path ASTRA_MultiRAG_v2_expansion.zip -DestinationPath .
# Or use 7-Zip / WinRAR

# On Linux/Mac
unzip ASTRA_MultiRAG_v2_expansion.zip
```

### Step 2: Install Dependencies

```bash
# Minimal (numpy + yaml)
pip install numpy pyyaml

# With PDF support
pip install numpy pyyaml pypdf

# With Qdrant backend (optional, production)
pip install qdrant-client
```

### Step 3: Ingest Documents

```bash
cd rag/

# Single document
python modules/ingest.py --category ai_engineering --path ./data/ai_engineering/sample.md

# Entire category
python modules/ingest.py --category ai_engineering --path ./data/ai_engineering
```

Creates:
- `astra.db` (SQLite with FTS5 index)
- `index/` (local JSON vectors)

### Step 4: Test Retrieval

```bash
# Basic retrieval
python modules/retrieve.py --q "How do I snapshot Qdrant?"

# HRM planner with citations
python modules/astra_rag_cli.py --q "Boot steps for Windows ingestion daemon"

# JSON output
python modules/astra_rag_cli.py --q "..." --json
```

---

## 📋 Integration Checklist

### With Memory Bridge

- [ ] Copy `rag/modules/` into `astra/bridge/`
- [ ] Update `memory_bridge.py`:

```python
from astra.bridge.modules.planner import answer
from astra.bridge.modules.retrieval_core import retrieve_multi

class MemoryBridge:
    def rag_query(self, query: str, k: int = 12):
        """Retrieve knowledge + record episodically."""
        result = answer(query, k=k, policy='hrm')
        
        # Record context in episodic memory
        self.record_interpretation(
            channel='rag_query',
            title=f"RAG: {query[:50]}",
            body='\n'.join(c['text'][:200] for c in result['contexts'][:3]),
            tags=['rag'] + [c['category'] for c in result['contexts']],
            confidence=result['reflection'].get('confidence', 0.5)
        )
        
        return result
```

### With Runtime Orchestrator

- [ ] Update `orchestrator.py` action registry:

```yaml
actions:
  multi_rag_query:
    handler: astra.bridge.modules.planner.answer
    params: [query, k, policy]
    return_type: Dict[str, Any]
    integrations: [memory_bridge]
```

### With Autonomy Engine

- [ ] Use RAG context in planning:

```python
from astra.bridge.modules.retrieval_core import retrieve_multi

class AutonomyPlanner:
    def plan(self, goal: str):
        # Get knowledge context
        context = retrieve_multi(f"Policies and constraints for: {goal}")
        # Use in planning...
```

---

## 🔧 Configuration

### System Settings (`config.yaml`)

```yaml
memory:
  db_path: ./astra.db

vector:
  backend: json          # json | qdrant | chroma
  dims: 128              # match your embedding dim

chunking:
  target_tokens: 350
  overlap_tokens: 40
```

### Per-Category Tuning (`categories.yaml`)

```yaml
ai_engineering:
  keywords: [vector, embedding, llm, ...]
  retriever:
    bm25_k: 60            # BM25 results
    vec_k: 60             # Dense results
    top_k: 12             # Final results
    mix_alpha: 0.5        # Dense/sparse balance
```

---

## 🎯 Common Operations

### Ingest Technical Documents

```bash
python modules/ingest.py --category ai_engineering \
  --path ./papers/neural_networks/ \
  --consent private
```

### Query with Tracing

```bash
python modules/astra_rag_cli.py \
  --q "How do embeddings work?" \
  --policy hrm \
  --json > results.json
```

### Watch Folder for Auto-Ingestion

```bash
python modules/service_windows.py \
  --root ./data/ai_engineering \
  --category ai_engineering \
  --interval 10
```

### Switch to Qdrant

```bash
# 1. Install Qdrant server (Docker)
docker run -d -p 6333:6333 qdrant/qdrant

# 2. Update config.yaml
vector:
  backend: qdrant
  host: localhost
  port: 6333

# 3. Re-ingest (creates Qdrant collections)
python modules/ingest.py --category ai_engineering --path ./data --backend qdrant
```

---

## 📊 Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Document ingestion (1000 tokens) | <100ms | Chunking + embedding |
| BM25 search | <10ms | FTS5 is very fast |
| Dense ANN (JSON) | <50ms | Linear; <5ms with Qdrant |
| Reranking (40→12) | <20ms | Cross-encoder |
| Full pipeline (query→results) | <150ms | E2E |
| Fast loop (2 iterations) | <300ms | With sub-query generation |
| HRM full answer (fast+slow) | <500ms | With reflection |

---

## 🐛 Troubleshooting

### "No results from retrieval"

```bash
# Check documents ingested
sqlite3 astra.db "SELECT COUNT(*) FROM docs;"

# Check FTS5 index
sqlite3 astra.db "SELECT COUNT(*) FROM chunks_fts;"

# Re-ingest
python modules/ingest.py --category ai_engineering --path ./data
```

### "ModuleNotFoundError: No module named 'yaml'"

```bash
pip install pyyaml
```

### "JSON vectors showing stale results"

```bash
# Delete and re-create
rm -Recurse index
python modules/ingest.py --category ai_engineering --path ./data
```

### "Slow retrieval on large corpus"

- Increase chunk size in `chunkers.py`
- Switch to Qdrant backend
- Reduce `--k` parameter
- Use specific categories (faster routing)

---

## 🔄 Upgrade Path

### M0 → M1 (Current → Add Real Models)

```python
# Replace in models_local.py
from sentence_transformers import SentenceTransformer, CrossEncoder

embed_model = SentenceTransformer('BAAI/bge-m3')
rerank_model = CrossEncoder('BAAI/bge-reranker-large')

def embed_dense(texts, dims=1536):
    return embed_model.encode(texts, normalize_embeddings=True)

def rerank_score(query, passages):
    return rerank_model.predict([[query, p] for p in passages])
```

### M0 → M2 (Add Qdrant)

```yaml
# Update config.yaml
vector:
  backend: qdrant
  host: qdrant.prod
  port: 6333
  dims: 1536
```

### M0 → M3 (Add Windows Service)

```bash
# Register Windows service
python -m nssm install AstraRAGWatcher ^
  "python modules/service_windows.py --root ./data/ai_engineering"

# Start
python -m nssm start AstraRAGWatcher
```

---

## 📚 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| **README.md** (in ZIP) | Overview + quickstart | Everyone |
| **MULTI_RAG_V2_BLUEPRINT.md** | Full architecture + algorithms | Architects |
| **MULTI_RAG_V2_IMPLEMENTATION_CHECKLIST.md** | M0-M6 milestones | Developers |
| **This guide** | Deployment + integration | DevOps |

---

## ✅ Deployment Validation

Run this checklist after deployment:

- [ ] ZIP extracted successfully
- [ ] Dependencies installed: `python -c "import yaml; import numpy; print('OK')"`
- [ ] Database created: `ls -la astra.db`
- [ ] Documents ingested: `python modules/ingest.py --category ai_engineering --path ./data`
- [ ] Basic retrieval works: `python modules/retrieve.py --q "test"`
- [ ] HRM planner works: `python modules/astra_rag_cli.py --q "test" --policy hrm`
- [ ] Citations generated: Check JSON output has citations field
- [ ] Memory bridge integrated: Planner result in episodic store
- [ ] Orchestrator action registered: Can call `multi_rag_query` action
- [ ] Autonomy using RAG context: Knowledge-informed planning active

---

## 🎓 Learning Path

**Day 1: Setup**
1. Extract ZIP
2. Install deps
3. Ingest sample docs (ai_engineering)
4. Run `retrieve.py` query

**Day 2: Integration**
5. Wire into memory_bridge
6. Test `rag_query()` episodic recording
7. Check orchestrator action registration

**Day 3: Advanced**
8. Replace models_local.py with real BGE-M3
9. Switch to Qdrant backend
10. Deploy Windows service

**Week 2: Tuning**
11. Adjust per-category params
12. Ingest docs from other categories
13. Eval on custom test set
14. Tune fusion weights

---

## 🤝 Support & Feedback

- 🐛 **Bug Reports:** Check `astra.db` and `index/` health
- 📈 **Performance:** Enable telemetry in planner.py
- 🎯 **Features:** See MULTI_RAG_V2_README.md for next steps

---

## 📝 Release Notes

**v2.0 Expansion (M0)**
- ✅ 12 core modules (chunkers → HRM planner)
- ✅ Local-first: JSON vector store, SQLite FTS5
- ✅ 4-category routing + fusion
- ✅ Windows-compatible polling watcher
- ✅ Full API docs + CLI
- ✅ Ready for memory bridge integration

**Known Limitations**
- Vector store stubs (replace with BGE-M3)
- JSON backend not for 1M+ corpus (use Qdrant)
- No multi-user/tenant isolation yet
- Limited PDF layout-awareness

**Roadmap**
- M1: Real embeddings + Qdrant migration
- M2: Vector-sliding embeddings
- M3: Layout-aware PDF parsing
- M4: Multi-tenant consent policies

---

**Sacred Code: 333**

✨ *Expand with clarity. Retrieve with intent. Answer with precision.*

---

**Get Started:**
```bash
unzip ASTRA_MultiRAG_v2_expansion.zip
cd rag
python modules/ingest.py --category ai_engineering --path ./data/ai_engineering
python modules/astra_rag_cli.py --q "How do I begin?"
```

**Questions? Check the README.md in the ZIP for 20+ troubleshooting answers.**
