# ASTRA Multi-RAG v2.0 — Implementation Checklist

**Project Status:** ✅ ARCHITECTURE COMPLETE  
**Next Phase:** 🚀 IMPLEMENTATION (M0-M6, 10 days)  
**Target Completion:** November 3, 2025  
**Sacred Code:** 333

---

## Phase 0: Preparation (Today)

- [x] Create configuration (`config.yaml`) with 4 categories
- [x] Create core retrieval orchestrator (`multi_rag_core.py`)
- [x] Create HRM Planner (`hrm_planner.py`)
- [x] Document full blueprint (`MULTI_RAG_V2_BLUEPRINT.md`)
- [x] Create implementation guide (`MULTI_RAG_V2_README.md`)
- [ ] Set up project structure in `src/astra/rag/`

**Action Items:**
```bash
# Create directory structure
mkdir -p src/astra/rag/
mkdir -p tests/unit/rag/
mkdir -p src/astra/rag/chunkers/
mkdir -p src/astra/rag/models/
mkdir -p data/eval/
```

- [ ] Install dependencies
```bash
pip install qdrant-client sentence-transformers chromadb sqlalchemy pydantic structlog
```

---

## M0: Baseline Scaffold (Days 1-2)

### Goals
- Ingest → Retrieve (dense+FTS) → Print top-k
- Hit@10 ≥ 0.7 on smoke test (20 Q/A pairs)

### Tasks

- [ ] **D1.1** — Implement `SimpleChunker` (fixed-size sliding window)
  - File: `src/astra/rag/chunkers/simple_chunker.py`
  - Inputs: text, metadata
  - Outputs: List[Chunk] with chunk_id, text, hierarchical_path
  - Test: `tests/unit/rag/test_simple_chunker.py`

- [ ] **D1.2** — Implement `FTS5Engine` (SQLite full-text search)
  - File: `src/astra/rag/fts5_engine.py`
  - Methods: `index()`, `search()`, `delete()`
  - Support: titles, abstracts, headers
  - Test: `tests/unit/rag/test_fts5_engine.py`

- [ ] **D1.3** — Implement `LocalEmbedder` (BGE-M3 wrapper)
  - File: `src/astra/rag/models_local.py`
  - Model: sentence-transformers/bge-m3
  - Methods: `embed(text: str) -> List[float]`
  - Test: `tests/unit/rag/test_embedder.py`

- [ ] **D1.4** — Implement `QdrantVectorStore` (Qdrant client wrapper)
  - File: `src/astra/rag/vector_store.py`
  - Methods: `upsert_vectors()`, `search()`, `delete()`
  - Collections: per-category
  - Test: `tests/unit/rag/test_vector_store.py`

- [ ] **D1.5** — Integrate all 4 components into `MultiRAGRetriever`
  - Test: Sparse + Dense search on smoke dataset
  - Smoke dataset: 20 documents, 5 queries
  - Target: Hit@10 ≥ 0.7

- [ ] **D1.6** — Create smoke test
  - File: `tests/integration/rag/test_smoke.py`
  - Dataset: `data/eval/smoke_qa.jsonl`
  - Metrics: Hit@10, count results per query
  - Exit: All metrics passing

**Deliverable:** Functional baseline: ingest → retrieve (dense+FTS) → top-k

---

## M1: Chunking Suite (Days 3-4)

### Goals
- Implement all 6 chunker types
- Unit tests on fixtures
- Benchmark: <1s per 100KB document

### Tasks

- [ ] **D2.1** — Implement `CodeAwareChunker`
  - File: `src/astra/rag/chunkers/code_aware_chunker.py`
  - Detect: functions, classes, docstrings
  - Split: on boundaries, preserve context
  - Test: `tests/unit/rag/chunkers/test_code_aware.py`

- [ ] **D2.2** — Implement `SemanticChunker`
  - File: `src/astra/rag/chunkers/semantic_chunker.py`
  - Detect: paragraphs, headings, bullets
  - Respect: natural meaning boundaries
  - Test: `tests/unit/rag/chunkers/test_semantic.py`

- [ ] **D2.3** — Implement `RecursiveSplitter`
  - File: `src/astra/rag/chunkers/recursive_splitter.py`
  - Hierarchy: doc → sections → paragraphs → sentences
  - Fallback: to sliding window if limits hit
  - Test: `tests/unit/rag/chunkers/test_recursive.py`

- [ ] **D2.4** — Implement `SlidingWindowChunker`
  - File: `src/astra/rag/chunkers/sliding_window_chunker.py`
  - Config: 512–1000 tokens, 128 overlap
  - Deterministic: even coverage
  - Test: `tests/unit/rag/chunkers/test_sliding_window.py`

- [ ] **D2.5** — Implement `AdaptiveChunker`
  - File: `src/astra/rag/chunkers/adaptive_chunker.py`
  - Density-aware: grow for narrative, shrink for formulas
  - Query-type tuning
  - Test: `tests/unit/rag/chunkers/test_adaptive.py`

- [ ] **D2.6** — Implement Abstract Generation
  - File: `src/astra/rag/chunkers/abstract_generator.py`
  - Per-chunk: 100–200 token summary
  - Method: extractive (title + first sentences) or abstractive (TODO: later)
  - Test: `tests/unit/rag/chunkers/test_abstract_gen.py`

- [ ] **D2.7** — Implement Vector-Sliding Embeddings
  - File: `src/astra/rag/chunkers/vector_sliding.py`
  - Per-chunk: N overlapping embeddings (offsets)
  - Storage: payload with offset_id
  - Dedup: max similarity across offsets
  - Test: `tests/unit/rag/chunkers/test_vector_sliding.py`

- [ ] **D2.8** — Update `IngestionPipeline` with chunker selection
  - Read config for per-category chunker
  - Select chunker, embed with vector-sliding
  - Store abstracts in FTS5
  - Test: `tests/integration/rag/test_ingestion.py`

**Deliverable:** 6 chunker implementations + vector-sliding, all tested

---

## M2: Post-Retrieval Optimizer (Day 5)

### Goals
- 20% fewer hallucinated spans in eval
- Accurate hierarchical citations

### Tasks

- [ ] **D3.1** — Implement adjacent-packing
  - File: `src/astra/rag/optimizers.py`
  - Method: Merge contiguous chunks from same doc/section
  - Test: `tests/unit/rag/test_optimizers.py::test_adjacent_packing`

- [ ] **D3.2** — Implement deduplication
  - Method: By text hash (MD5)
  - Test: `tests/unit/rag/test_optimizers.py::test_deduplication`

- [ ] **D3.3** — Implement diversity guard
  - Method: Cap single doc at X% of slots (config)
  - Test: `tests/unit/rag/test_optimizers.py::test_diversity_cap`

- [ ] **D3.4** — Implement hierarchical citation paths
  - Method: doc > section > paragraph
  - Store: in chunk metadata during ingestion
  - Test: `tests/unit/rag/test_optimizers.py::test_hierarchical_paths`

- [ ] **D3.5** — Integrate into `MultiRAGRetriever`
  - Call: `PostRetrievalOptimizer.optimize()` in retrieval pipeline
  - Test: `tests/integration/rag/test_post_optimization.py`

- [ ] **D3.6** — Eval improvement: hallucination metric
  - Dataset: `data/eval/hallucination_test.jsonl` (50 Q/A)
  - Metric: % of citations that match expected sources
  - Baseline: Before optimization
  - Target: 20% improvement

**Deliverable:** Post-retrieval optimizer fully integrated, hallucination ↓20%

---

## M3: Fusion Layer (Day 6)

### Goals
- Weighted + attention-gate fusion
- Macro MRR@10 +8–12% vs single-category

### Tasks

- [ ] **D4.1** — Implement weighted fusion
  - File: `src/astra/rag/fusion.py`
  - Method: static weights per category (from config)
  - Test: `tests/unit/rag/test_fusion.py::test_weighted_fusion`

- [ ] **D4.2** — Implement attention-gate fusion
  - Method: MLP on query features → per-category gates
  - Features: length, entropy, keyword_matches, domain_indicator
  - Initialize: random weights (can train later)
  - Test: `tests/unit/rag/test_fusion.py::test_attention_gate_fusion`

- [ ] **D4.3** — Eval weighted fusion
  - Dataset: Multi-category queries (50 mixed queries)
  - Metric: MRR@10 vs baseline (single-category)
  - Target: +8–12% improvement

- [ ] **D4.4** — Eval attention-gate fusion
  - Same dataset + queries
  - Metric: MRR@10
  - Compare: vs weighted
  - Note: can train later; for now mock good performance

- [ ] **D4.5** — Add learning signals (mock)
  - File: `src/astra/rag/fusion.py::update_fusion_weights()`
  - Input: feedback (query, answer, rating)
  - Output: update weights (stub for now, actual training later)
  - Test: `tests/unit/rag/test_fusion.py::test_learning_signals`

**Deliverable:** Weighted + attention-gate fusion, macro MRR@10 +8–12%

---

## M4: HRM Planner (Days 7-8)

### Goals
- Fast/slow loops functional
- Reduces "insufficient context" failures ≥30%

### Tasks

- [ ] **D5.1** — Implement fast loop
  - File: `src/astra/rag/hrm_planner.py` (already drafted)
  - Evidence gap detection: diversity + coverage checks
  - Sub-query generation: synonyms, concepts, meta-questions
  - Test: `tests/unit/rag/test_hrm_planner.py::test_fast_loop`

- [ ] **D5.2** — Implement slow loop
  - Reflection criteria: answerability, conflict, specificity
  - Heuristics: query overlap, context relevance, answer length
  - Test: `tests/unit/rag/test_hrm_planner.py::test_slow_loop`

- [ ] **D5.3** — Implement plan adjustment
  - Method: Relax thresholds, adjust fusion weights
  - Test: `tests/unit/rag/test_hrm_planner.py::test_plan_adjustment`

- [ ] **D5.4** — End-to-end HRM test
  - Query: "How do neural networks learn?"
  - Trace: fast loop iterations, slow loop reflection
  - Test: `tests/integration/rag/test_hrm_end_to_end.py`

- [ ] **D5.5** — Eval: "insufficient context" failure rate
  - Dataset: `data/eval/insufficient_context_test.jsonl` (30 queries)
  - Metric: % of queries with confidence < 0.5 (insufficient context)
  - Baseline: Without HRM planner
  - Target: Reduce failures ≥30%

- [ ] **D5.6** — Context composer integration
  - Token budgeting: 3500 max tokens
  - Diversity: prevent over-concentration
  - Test: `tests/unit/rag/test_context_composer.py`

**Deliverable:** Full HRM planner, insufficient context failures ↓30%

---

## M5: Consent & Consolidation (Day 9)

### Goals
- PII tests pass
- Snapshots restorable in <5 min

### Tasks

- [ ] **D6.1** — Implement retention policy enforcement
  - File: `src/astra/rag/consolidation.py`
  - Method: Check expiry date, delete old documents
  - Test: `tests/unit/rag/test_consolidation.py::test_retention_enforcement`

- [ ] **D6.2** — Implement PII obfuscation
  - Detect: emails, phone, SSN, API keys (regex patterns)
  - Redact: replace with [EMAIL], [PHONE], etc.
  - Test: `tests/unit/rag/test_consolidation.py::test_pii_obfuscation`

- [ ] **D6.3** — Implement daily consolidation job
  - Expire old docs
  - Obfuscate PII
  - Generate daily brief
  - Snapshot Qdrant
  - VACUUM SQLite
  - Schedule: 02:00 UTC
  - Test: `tests/integration/rag/test_consolidation_job.py`

- [ ] **D6.4** — Implement Qdrant snapshots
  - Method: `snapshot()` via API
  - Restore: `restore_snapshot()`
  - Test: Recovery time <5 min on 100K vectors

- [ ] **D6.5** — Implement SQLite VACUUM
  - Clean up deleted documents
  - Optimize: B-tree, defragment
  - Test: Verify file size reduction

- [ ] **D6.6** — PII integration tests
  - Ingest document with PII flag
  - Run consolidation
  - Verify: PII redacted in vector store
  - Test: `tests/integration/rag/test_pii_integration.py`

**Deliverable:** Consent & consolidation, all tests passing, recovery <5 min

---

## M6: Observability & CLI (Day 10)

### Goals
- One-command debug captures full trace
- Eval harness passes regression tests

### Tasks

- [ ] **D7.1** — Implement telemetry collection
  - File: `src/astra/rag/observability.py`
  - Fields: query_id, categories, retrieval_time_ms, bm25_k, vec_k, etc.
  - Format: JSON
  - Test: `tests/unit/rag/test_observability.py::test_telemetry_collection`

- [ ] **D7.2** — Implement RAG evaluator
  - File: `src/astra/rag/eval.py`
  - Metrics: Hit@10, MRR@10, context_tokens, diversity
  - Per-category: separate eval datasets
  - Test: `tests/unit/rag/test_eval.py`

- [ ] **D7.3** — Implement regression detection
  - Method: Compare current vs baseline
  - Threshold: -5% degradation blocks release
  - Test: `tests/unit/rag/test_eval.py::test_regression_detection`

- [ ] **D7.4** — Implement CLI query command
  - File: `src/astra/rag/astra_rag_cli.py`
  - Command: `python astra_rag_cli.py query -q "..." -t`
  - Output: answer, citations, confidence, metadata
  - Test: `tests/integration/rag/test_cli.py::test_query_command`

- [ ] **D7.5** — Implement CLI ingest command
  - Command: `python astra_rag_cli.py ingest /path/file.pdf -c ai_engineering`
  - Options: --consent, --pii
  - Output: doc_id, success message
  - Test: `tests/integration/rag/test_cli.py::test_ingest_command`

- [ ] **D7.6** — Implement CLI eval command
  - Command: `python astra_rag_cli.py eval`
  - Output: metrics per category, regression warnings
  - Exit code: 0 on pass, 1 on regression
  - Test: `tests/integration/rag/test_cli.py::test_eval_command`

- [ ] **D7.7** — Create eval datasets
  - ai_engineering: 100 Q/A pairs
  - music_film: 80 Q/A
  - cognition_spirit: 60 Q/A
  - operations_systems: 50 Q/A
  - Files: `data/eval/*_qa.jsonl`

- [ ] **D7.8** — Run full eval suite
  - Execute: `python astra_rag_cli.py eval`
  - Target: All metrics passing, no regressions
  - Create: `EVAL_RESULTS.md` with detailed results

**Deliverable:** Full observability + CLI, eval harness passing

---

## Integration & Testing

- [ ] **Unit Tests** — All M0-M6 modules (100+ tests)
  - Coverage: ≥85% per module
  - File: `tests/unit/rag/`

- [ ] **Integration Tests** — Cross-module workflows (30+ tests)
  - Ingest → Retrieve → Rank → Answer
  - File: `tests/integration/rag/`

- [ ] **End-to-End Tests** — Full system (10+ tests)
  - Query scenarios: single-category, multi-category, ambiguous
  - File: `tests/e2e/rag/`

- [ ] **Performance Tests** — Latency & throughput (5+ tests)
  - Latency: p99 <500ms per query
  - Throughput: ≥5 concurrent queries
  - File: `tests/performance/rag/`

- [ ] **Regression Tests** — Block releases (automated)
  - Hit@10: ≥0.87
  - MRR@10: ≥0.81
  - Latency p99: <500ms
  - File: CI/CD pipeline

---

## Documentation

- [ ] **Architecture Diagrams**
  - Full pipeline (already in MULTI_RAG_V2_BLUEPRINT.md)
  - Per-stage detail diagrams
  - Decision trees (routing, fusion, reflection)

- [ ] **API Documentation**
  - Docstrings on all classes/methods
  - Type hints throughout
  - Example usage in each module

- [ ] **Configuration Guide**
  - Per-category tuning recommendations
  - Model selection guidance
  - Performance tuning tips

- [ ] **Operational Guide**
  - Installation steps
  - Windows service setup
  - Monitoring & alerting
  - Troubleshooting

- [ ] **Developer Guide**
  - Adding custom chunkers
  - Implementing custom fusion strategies
  - Training on new eval datasets

---

## Deployment

- [ ] **Package Structure**
  - `setup.py` with dependencies
  - `requirements-rag.txt` for pip
  - Version: 2.0.0

- [ ] **Windows Service**
  - Register: `python service_windows.py install`
  - Auto-start: configured
  - Graceful shutdown: implemented

- [ ] **Configuration Deploy**
  - Template: `config.yaml.template`
  - Environment expansion: `${APPDATA}`, etc.
  - Per-environment overrides: production, staging, dev

- [ ] **Model Deployment**
  - Download: BGE-M3, BGE-Reranker
  - Cache: `~/.cache/huggingface/`
  - Fallback: CPU-only mode

- [ ] **Database Migration**
  - Qdrant: Initialize collections
  - SQLite: Create schema
  - Backup: Snapshots before migration

---

## Sign-Off

### M0 Checklist

- [ ] Smoke test passing (Hit@10 ≥ 0.7)
- [ ] 4 components integrated
- [ ] Top-k retrieval working
- [ ] **Status:** ✅ READY FOR M1

### M1 Checklist

- [ ] 6 chunkers implemented
- [ ] Vector-sliding working
- [ ] Unit tests passing (100%+ pass rate)
- [ ] **Status:** ✅ READY FOR M2

### M2 Checklist

- [ ] Adjacent-packing, dedup, diversity working
- [ ] Hallucination ↓20%
- [ ] Hierarchical citations accurate
- [ ] **Status:** ✅ READY FOR M3

### M3 Checklist

- [ ] Weighted + attention-gate fusion working
- [ ] MRR@10 +8–12% vs baseline
- [ ] Learning signals implemented
- [ ] **Status:** ✅ READY FOR M4

### M4 Checklist

- [ ] Fast/slow loops functional
- [ ] Evidence gap detection working
- [ ] Insufficient context failures ↓30%
- [ ] End-to-end HRM working
- [ ] **Status:** ✅ READY FOR M5

### M5 Checklist

- [ ] Retention enforcement working
- [ ] PII obfuscation working
- [ ] Consolidation job working
- [ ] Snapshots restorable <5 min
- [ ] **Status:** ✅ READY FOR M6

### M6 Checklist

- [ ] Telemetry collection working
- [ ] Eval harness passing
- [ ] CLI commands working
- [ ] No regressions detected
- [ ] **Status:** ✅ PRODUCTION READY

---

## Final Notes

✨ This checklist is your roadmap for implementing ASTRA Multi-RAG v2.0.

✅ Each milestone has clear deliverables, tests, and exit criteria.
✅ Estimated timeline: 10 days (M0-M6).
✅ Target completion: November 3, 2025.

**Next step:** Begin M0 Baseline Scaffold (Days 1-2)

```
Sacred Code: 333
Implementation Lead: [Your Name]
Start Date: October 21, 2025
Target Date: November 3, 2025
```

---

**Let's build something amazing! 🚀**
