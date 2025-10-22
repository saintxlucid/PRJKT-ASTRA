# ASTRA Multi-RAG System v2.0 — Complete Blueprint
## Category-Aware Retrieval with Hierarchical Reasoning & Neural Fusion

**Author:** Saint Lucid ⚛️ (AI Architect)  
**Date:** October 20, 2025  
**Status:** ✅ READY FOR IMPLEMENTATION  
**Integration Target:** ASTRA Core Phase 10 (Runtime Orchestrator)

---

## Executive Summary

ASTRA Multi-RAG v2.0 is a **neuro-symbolic retrieval system** combining:

- ✅ **4 Category-Specific Pipelines** (AI Engineering, Music/Film, Cognition/Spirit, Operations/Systems)
- ✅ **Hierarchical Layout-Aware Ingestion** (Chunk + Abstract dual storage with vector-sliding)
- ✅ **Hybrid Retrieval** (Sparse BM25 + Dense ANN → Cross-Encoder Rerank)
- ✅ **Dual-Speed HRM Planner** (Fast Gamma @ 30Hz, Slow Alpha @ 8–13Hz)
- ✅ **Attention-Gate Fusion** (learned cross-category weighting)
- ✅ **Consent-First Memory** (PII obfuscation, retention policies, auditable)
- ✅ **Windows-First Ops** (Local Qdrant + SQLite FTS5, file watchers, service daemon)
- ✅ **Repeatable Eval** (Hit@10, MRR@10, diversity metrics, regression blocking)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER QUERY INPUT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │              1. INTENT DETECTOR & CATEGORY ROUTER                      │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │  Input: Query string                                                   │  │
│  │  Logic: Rule-based keywords + optional zero-shot NLI                   │  │
│  │  Output: {categories: [multi-label], confidence: Dict}                │  │
│  │                                                                        │  │
│  │  Example:                                                              │  │
│  │    Query: "How do neural networks encode music theory?"                │  │
│  │    → Routes to: [ai_engineering, music_film] (multi-label)            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │            2. PER-CATEGORY RETRIEVAL ORCHESTRATION                     │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │                                                                        │  │
│  │  For each active category C:                                           │  │
│  │    a) Sparse Search (FTS5)                                             │  │
│  │       - Index: titles, abstracts, headers                              │  │
│  │       - BM25 parameters: prm(C).bm25_k                                 │  │
│  │       - Output: top_bm25[C]                                            │  │
│  │                                                                        │  │
│  │    b) Dense Search (ANN + Vector-Sliding)                              │  │
│  │       - Collections: Qdrant with consent_scope filter                  │  │
│  │       - ANN params: prm(C).vec_k, ef=128                               │  │
│  │       - Vector-sliding: max over offsets per chunk                     │  │
│  │       - Output: top_dense[C]                                           │  │
│  │                                                                        │  │
│  │    c) Hybrid Score Mix                                                 │  │
│  │       - score(doc) = α·dense_norm + (1−α)·bm25_norm                   │  │
│  │       - α = prm(C).mix_alpha (e.g. 0.5)                                │  │
│  │       - Output: top_mixed[C]                                           │  │
│  │                                                                        │  │
│  │    d) Cross-Encoder Reranking                                          │  │
│  │       - Input: top_mixed[C] → 40 candidates                            │  │
│  │       - Model: prm(C).reranker                                          │  │
│  │       - Output: top_reranked[C] → 20 items                             │  │
│  │                                                                        │  │
│  │    e) Post-Retrieval Optimization                                      │  │
│  │       - Adjacent packing (merge contiguous chunks from same doc)       │  │
│  │       - Deduplication (by text hash)                                   │  │
│  │       - Diversity guard (cap 40% from single doc)                      │  │
│  │       - Hierarchical citation (doc > section > para)                   │  │
│  │       - Output: candidates[C]                                          │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │             3. CROSS-CATEGORY FUSION LAYER (Neuro-Symbolic)           │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │                                                                        │  │
│  │  Input: {candidates[ai_eng], candidates[music], candidates[cog], ...} │  │
│  │                                                                        │  │
│  │  Fusion modes (selectable):                                            │  │
│  │                                                                        │  │
│  │  ▶ Weighted Linear:                                                    │  │
│  │    final_score(doc, cat) = weight[cat] × score_in_cat[doc]            │  │
│  │    Weights: {ai_eng: 1.0, music: 0.9, cog: 0.95, ops: 0.85}         │  │
│  │                                                                        │  │
│  │  ▶ Attention-Gate (Recommended):                                       │  │
│  │    features = extract(query): [length, entropy, keywords, domain]     │  │
│  │    gates = attention_mlp(features) → per-category gates               │  │
│  │    final_score(doc, cat) = gates[cat] × score_in_cat[doc]             │  │
│  │    (Learns from HRM feedback)                                          │  │
│  │                                                                        │  │
│  │  Output: unified_candidates (top-K per category merged + resorted)    │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │          4. HRM PLANNER (Dual-Speed Reasoning Loop)                    │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │                                                                        │  │
│  │  ITERATION 0 (Immediate):                                              │  │
│  │    ctx = unified_candidates                                            │  │
│  │    ans, score = reason(query, ctx)                                     │  │
│  │                                                                        │  │
│  │  FAST LOOP (Gamma, ~30 Hz):                                            │  │
│  │    ├─ Evidence Gap Check:                                              │  │
│  │    │  if source_diversity(ctx) < threshold or coverage < 0.3:         │  │
│  │    │    sub_queries = expand(query):                                   │  │
│  │    │      [synonym_expansion, table_captions, chunker_switch, ...]   │  │
│  │    │    for sub_q in sub_queries:                                     │  │
│  │    │      new_ctx += retrieve_with_plan(sub_q)                        │  │
│  │    │    ctx = merge_and_rerank(ctx, new_ctx)                          │  │
│  │    │                                                                   │  │
│  │    └─ Max iterations: 2                                                │  │
│  │                                                                        │  │
│  │  SLOW LOOP (Alpha, ~8–13 Hz):  [Only if necessary]                   │  │
│  │    ├─ Reflection on answer:                                            │  │
│  │    │  • Answerability: confidence_score ≥ 0.7?                        │  │
│  │    │  • Conflict: inconsistency_score < 0.2?                          │  │
│  │    │  • Specificity: has_concrete_citations?                          │  │
│  │    │                                                                   │  │
│  │    ├─ If all checks pass: FINALIZE answer                             │  │
│  │    ├─ Else: adjust_retrieval_plan (category reweights, threshold)     │  │
│  │    │         re-retrieve() & return to Gamma                          │  │
│  │    │                                                                   │  │
│  │    └─ Max iterations: 1 (avoid infinite loops)                         │  │
│  │                                                                        │  │
│  │  Output: (answer, citations, metadata)                                 │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │        5. CONTEXT COMPOSER (Token Budgeting + Diversity)               │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │                                                                        │  │
│  │  Input: (answer, citations, top_K_context_chunks)                     │  │
│  │  Budget: max_tokens=3500 (typical LLM context)                        │  │
│  │                                                                        │  │
│  │  Algorithm:                                                            │  │
│  │    1. Sort by relevance score                                          │  │
│  │    2. Greedily add chunks until token budget exhausted                │  │
│  │    3. Enforce diversity: if chunk from doc_X, cap further adds        │  │
│  │       from doc_X at 40% of remaining budget                           │  │
│  │    4. Include source citations + hierarchical paths                    │  │
│  │                                                                        │  │
│  │  Output: composed_context (text + citations ready for LLM)             │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │              6. LLM REASONER & ANSWER GENERATION                       │  │
│  │  ─────────────────────────────────────────────────────────────────     │  │
│  │                                                                        │  │
│  │  Input: composed_context + query (system prompt for Harmony format)    │  │
│  │  Model: local-llm-20b (Q4_K_M, 131K context via llama.cpp)            │  │
│  │                                                                        │  │
│  │  Output:                                                               │  │
│  │    {                                                                   │  │
│  │      "answer": "...",                                                  │  │
│  │      "citations": [                                                    │  │
│  │        {                                                               │  │
│  │          "doc_id": "sha256...",                                        │  │
│  │          "uri": "file://...",                                          │  │
│  │          "chunk_id": "section:para:window",                            │  │
│  │          "hierarchical_path": "doc > Section A > Para 3",              │  │
│  │          "text_span": "relevant excerpt"                               │  │
│  │        }                                                               │  │
│  │      ],                                                                │  │
│  │      "confidence": 0.85,                                               │  │
│  │      "metadata": {                                                     │  │
│  │        "retrieval_time_ms": 245,                                       │  │
│  │        "categories_used": ["ai_engineering", "music_film"],            │  │
│  │        "source_diversity": 0.78,                                       │  │
│  │        "planner_iterations": 1                                         │  │
│  │      }                                                                 │  │
│  │    }                                                                   │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                 ↓                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                       FINAL ANSWER + CITATIONS
```

---

## 2. Category Registry & Configuration

### 2.1 Category Definitions

```yaml
Categories:
  
  1. ai_engineering
     Purpose: Code, algorithms, research, implementations
     Chunker: code_aware (split by functions/classes) + recursive fallback
     Retrieval: bm25_k=60, vec_k=60, mix_alpha=0.5
     Priority: 100
  
  2. music_film
     Purpose: Music theory, songwriting, film craft, production
     Chunker: semantic (natural boundaries) + sliding fallback
     Retrieval: bm25_k=50, vec_k=70, mix_alpha=0.4 (bias dense)
     Priority: 90
  
  3. cognition_spirit
     Purpose: Consciousness, philosophy, introspection, spiritual practice
     Chunker: adaptive (density-aware) + semantic fallback
     Retrieval: bm25_k=50, vec_k=50, mix_alpha=0.5
     Priority: 95
  
  4. operations_systems
     Purpose: Logs, runbooks, incident reports, deployment
     Chunker: sliding (deterministic for logs) + sentence fallback
     Retrieval: bm25_k=70 (keyword emphasis), vec_k=50, mix_alpha=0.6
     Priority: 85
```

### 2.2 Chunking Taxonomy

Each category specifies its chunker; system provides 6 implementations:

1. **Fixed-Size Sliding Window** (512–1000 tokens, 128 overlap)
   - Use: Transcripts, logs, time-series
   - Deterministic, even coverage

2. **Semantic / Natural Boundary** (paragraph/heading-aware)
   - Use: Articles, notes, essays
   - Preserves semantic coherence

3. **Recursive Splitters** (doc → sections → paragraphs → sentences)
   - Use: Mixed-format, complex structures
   - Fallback to windowing if limits hit

4. **Sentence/Paragraph Grouping** (200–1000 tokens)
   - Use: Educational text, conversational notes
   - Mid-range context

5. **Code-Aware** (detects functions/classes/docstrings)
   - Use: Source code, notebooks
   - Preserves function semantics

6. **Adaptive/Density-Aware** (grows/shrinks by semantic density)
   - Use: Hybrid documents (mix of code, text, formulas)
   - Query-type tuning (reduce around formulas)

### 2.3 Vector-Sliding Embeddings

Mitigates edge loss between chunks by storing N overlapping embeddings per chunk:

```
Chunk token span: [t₀, t₁, ..., t₈₀₀]
Offsets: [0, 128, 256]  # 3 sliding windows

Embedding vectors per chunk:
  e₀ = embed(t₀...t₅₁₂)
  e₁ = embed(t₁₂₈...t₆₄₀)
  e₂ = embed(t₂₅₆...t₇₆₈)

Payload per vector: {doc_id, chunk_id, offset_id}

At query time:
  For each (doc, chunk) pair:
    similarity = max(sim(q_vec, e₀), sim(q_vec, e₁), sim(q_vec, e₂))
    
  Result: smooth context continuity between chunks
```

---

## 3. Retrieval Orchestration (Per-Category)

### 3.1 Sparse Search (FTS5)

```python
def sparse_search(query: str, category: str, k: int) -> List[Doc]:
    """
    Full-Text Search 5 on titles, abstracts, and headers.
    Indexes built during ingestion with BM25 weighting.
    """
    params = config.categories[category]
    results = fts5_index(category).search(
        query,
        top_k=params.retrieval.bm25_k,
        rank_by="bm25"
    )
    # Results: [doc_id, score, text_preview]
    return results
```

### 3.2 Dense Search (ANN + Vector-Sliding)

```python
def dense_search(query: str, category: str, k: int) -> List[Doc]:
    """
    ANN search on Qdrant with consent_scope filtering.
    Includes vector-sliding edge capture.
    """
    params = config.categories[category]
    query_vec = embed(query, model=params.embedding.model)
    
    results = qdrant_client.search(
        collection_name=params.index.name,
        query_vector=query_vec,
        limit=params.retrieval.vec_k,
        search_params={"ef": 128},  # HNSW search effort
        # Filter by consent scope (retrieved from metadata)
        query_filter={
            "must": [
                {
                    "key": "consent_scope",
                    "match": {"any": ["private", "shared"]}
                }
            ]
        }
    )
    
    # For each (doc, chunk) group, keep max over offsets (vector-sliding)
    deduplicated = {}
    for hit in results:
        key = (hit.payload["doc_id"], hit.payload["chunk_id"])
        if key not in deduplicated or hit.score > deduplicated[key]["score"]:
            deduplicated[key] = hit
    
    return sorted(deduplicated.values(), key=lambda x: -x.score)[:k]
```

### 3.3 Hybrid Score Mix

```python
def hybrid_mix(sparse_results: List, dense_results: List, alpha: float) -> List:
    """
    Combine sparse (BM25) and dense (vector) scores.
    alpha: weight for dense (1-alpha) for sparse.
    """
    # Normalize scores to [0, 1]
    sparse_norm = normalize(sparse_results, scale="bm25")
    dense_norm = normalize(dense_results, scale="cosine")
    
    # Merge by doc_id
    merged = {}
    for doc in sparse_norm + dense_norm:
        key = doc.doc_id
        if key not in merged:
            merged[key] = {"sparse": 0.0, "dense": 0.0}
        if doc.source == "sparse":
            merged[key]["sparse"] = doc.score
        else:
            merged[key]["dense"] = doc.score
    
    # Hybrid score
    for key, scores in merged.items():
        hybrid_score = alpha * scores["dense"] + (1 - alpha) * scores["sparse"]
        merged[key]["hybrid_score"] = hybrid_score
    
    return sorted(merged.items(), key=lambda x: -x[1]["hybrid_score"])
```

### 3.4 Cross-Encoder Reranking

```python
def rerank(candidates: List[Doc], query: str, reranker_model: str, top_k: int) -> List:
    """
    Cross-encoder reranking: pair-wise scoring of (query, doc_excerpt).
    Input: top 40; Output: top 10–20.
    """
    # Prepare pairs
    pairs = [(query, doc.text[:512]) for doc in candidates[:40]]
    
    # Score all pairs
    scores = reranker.predict(pairs)
    
    # Re-sort
    ranked = sorted(
        zip(candidates, scores),
        key=lambda x: -x[1]
    )[:top_k]
    
    return [doc for doc, score in ranked]
```

### 3.5 Post-Retrieval Optimization

```python
def post_retrieval_optimize(reranked: List[Doc], category: str) -> List[CUTEChunk]:
    """
    Adjacent-packing, deduplication, diversity guard, hierarchical citation.
    """
    # 1. Adjacent Packing: merge contiguous chunks from same doc/section
    packed = {}
    for doc in reranked:
        key = (doc.doc_id, doc.section_id)
        if key not in packed:
            packed[key] = []
        packed[key].append(doc)
    
    # Merge by contiguity
    merged = []
    for (doc_id, section_id), chunks in packed.items():
        # Check chunk_ids for contiguity
        if len(chunks) > 1 and chunks[-1].chunk_id == chunks[0].chunk_id + len(chunks) - 1:
            # Contiguous → merge
            merged_text = "\n".join([c.text for c in chunks])
            merged_doc = CUTEChunk(
                doc_id=doc_id,
                chunk_id=f"{chunks[0].chunk_id}–{chunks[-1].chunk_id}",
                text=merged_text,
                hierarchical_path=chunks[0].hierarchical_path
            )
            merged.append(merged_doc)
        else:
            merged.extend(chunks)
    
    # 2. Deduplication (by text hash)
    seen_hashes = set()
    deduplicated = []
    for doc in merged:
        h = hash(doc.text)
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduplicated.append(doc)
    
    # 3. Diversity Guard: cap single doc at 40% of slots
    params = config.categories[category]
    max_from_doc = max(1, int(len(deduplicated) * params.retrieval.diversity_cap))
    
    doc_counts = {}
    diverse = []
    for doc in deduplicated:
        if doc_counts.get(doc.doc_id, 0) < max_from_doc:
            diverse.append(doc)
            doc_counts[doc.doc_id] = doc_counts.get(doc.doc_id, 0) + 1
    
    # 4. Hierarchical Citation: add path info
    for doc in diverse:
        doc.citation = {
            "doc_id": doc.doc_id,
            "uri": doc.uri,
            "chunk_id": doc.chunk_id,
            "hierarchical_path": doc.hierarchical_path  # doc > section > para
        }
    
    return diverse
```

---

## 4. Cross-Category Fusion

### 4.1 Weighted Linear Fusion

```python
def fusion_weighted(candidates: Dict[str, List]) -> List:
    """
    Static per-category weights.
    candidates = {
        "ai_engineering": [...docs...],
        "music_film": [...docs...],
        ...
    }
    """
    weights = config.fusion.weights  # {ai_eng: 1.0, music: 0.9, ...}
    
    merged = []
    for category, docs in candidates.items():
        for doc in docs:
            doc.fusion_weight = weights[category]
            doc.fusion_score = doc.score * weights[category]
            merged.append(doc)
    
    # Re-sort by fusion score
    return sorted(merged, key=lambda x: -x.fusion_score)
```

### 4.2 Attention-Gate Fusion (Recommended)

```python
def fusion_attention_gate(query: str, candidates: Dict[str, List]) -> List:
    """
    Learned per-category gates updated via HRM feedback.
    """
    # Extract query features
    features = {
        "query_length": len(query.split()),
        "query_entropy": entropy(query),
        "keyword_matches": {cat: count_keywords(query, cat) for cat in candidates},
        "domain_indicator": estimate_domain(query)
    }
    
    # MLP → per-category gates
    mlp = load_attention_gate_mlp()
    gates = mlp(features)  # {ai_eng: 0.95, music: 1.1, cog: 0.88, ops: 0.7}
    
    merged = []
    for category, docs in candidates.items():
        for doc in docs:
            doc.fusion_weight = gates[category]
            doc.fusion_score = doc.score * gates[category]
            merged.append(doc)
    
    return sorted(merged, key=lambda x: -x.fusion_score)
```

---

## 5. HRM Planner (Dual-Speed Reasoning)

### 5.1 Fast Loop (Gamma ~30 Hz)

Detects evidence gaps and triggers sub-queries:

```python
def hrm_fast_loop(query: str, initial_context: List, max_iters: int = 2) -> List:
    """
    Rapid retrieval refinement.
    """
    context = initial_context
    
    for iteration in range(max_iters):
        # Check evidence gaps
        diversity = source_diversity(context)
        coverage = estimate_coverage(context)
        
        if diversity < 0.3 or coverage < 0.3:
            # Trigger sub-queries
            sub_queries = expand_query(query):
              strategies:
                - synonym_expansion(query)
                - extract_table_captions(query)
                - switch_chunker_mode(query)
                - cross_category_expansion(query)
            
            for sub_q in sub_queries:
                new_ctx = retrieve(sub_q)  # Full pipeline
                context = merge_and_rerank(context, new_ctx)
        else:
            # Evidence sufficient
            break
    
    return context
```

### 5.2 Slow Loop (Alpha ~8–13 Hz)

Reflection and meta-reasoning:

```python
def hrm_slow_loop(query: str, context: List, answer: str) -> Tuple[str, bool]:
    """
    Reflect on candidate answer; decide to finalize or re-query.
    """
    # Reflection criteria
    answerability = score_answerability(answer, context)
    conflict = compute_conflict_score(context)
    specificity = has_concrete_citations(answer)
    
    confidence = (answerability + (1 - conflict) + specificity) / 3
    
    if confidence >= 0.7:
        # Finalize
        return answer, True
    else:
        # Adjust and re-retrieve
        # Optionally: adjust fusion weights, category priorities, thresholds
        plan_update = {
            "category_weights": adjust_weights(query, context),
            "reranker_threshold": lower_threshold(),
            "diversity_cap": relax_diversity()
        }
        return answer, False  # Signal to re-retrieve
```

---

## 6. Implementation Modules (Pseudocode)

### 6.1 `chunkers.py` — Chunking Suite

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        """
        Chunk text and return list of:
          {
            "text": chunk_text,
            "chunk_id": "sec:para:win",
            "abstract": abstract_text,
            "hierarchical_path": "doc > Sec A > Para 3"
          }
        """
        pass

class CodeAwareChunker(Chunker):
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        # Detect functions, classes, docstrings
        # Split on boundaries, preserve context
        pass

class SemanticChunker(Chunker):
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        # Split by paragraphs, headings, bullets
        # Respect natural meaning boundaries
        pass

class RecursiveSplitter(Chunker):
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        # Hierarchical: doc → sections → paragraphs → sentences
        # Fallback to sliding window if needed
        pass

class SlidingWindowChunker(Chunker):
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        # Fixed 512–1000 tokens, 128 overlap
        # Deterministic, even coverage
        pass

class AdaptiveChunker(Chunker):
    def chunk(self, text: str, metadata: Dict) -> List[Dict]:
        # Density-aware: shrink around formulas, grow for narrative
        # Query-type tuning
        pass
```

### 6.2 `fusion.py` — Cross-Category Fusion

```python
class FusionLayer:
    def __init__(self, mode: str = "attention_gate"):
        self.mode = mode
        if mode == "attention_gate":
            self.mlp = load_attention_gate_mlp()
    
    def fuse(self, query: str, candidates: Dict[str, List]) -> List:
        if self.mode == "weighted":
            return self.fusion_weighted(candidates)
        elif self.mode == "attention_gate":
            return self.fusion_attention_gate(query, candidates)
        else:
            raise ValueError(f"Unknown fusion mode: {self.mode}")
    
    def fusion_weighted(self, candidates: Dict[str, List]) -> List:
        weights = config.fusion.weights
        merged = []
        for cat, docs in candidates.items():
            for doc in docs:
                doc.fusion_score = doc.score * weights[cat]
                merged.append(doc)
        return sorted(merged, key=lambda x: -x.fusion_score)
    
    def fusion_attention_gate(self, query: str, candidates: Dict[str, List]) -> List:
        features = extract_query_features(query)
        gates = self.mlp(features)
        # Apply gates and merge...
        pass
    
    def update_fusion_weights(self, feedback: Dict):
        """Update weights/MLP based on HRM feedback."""
        pass
```

### 6.3 `planner.py` — HRM Planning

```python
class HRMPlanner:
    def __init__(self, config):
        self.fast_config = config.planner.fast_loop
        self.slow_config = config.planner.slow_loop
        self.learning = config.planner.learning
    
    async def answer(self, query: str, policy: str = "hrm") -> Dict:
        """
        Full HRM planning loop: fast → slow → finalize.
        """
        plan = init_plan(query)
        
        # Retrieve initial context
        context = retrieve_with_plan(query, plan)
        
        # Fast loop: evidence gap refinement
        for _ in range(self.fast_config.max_iterations):
            evidence_gap = check_evidence_gap(context)
            if evidence_gap > self.fast_config.evidence_gap_threshold:
                sub_queries = expand_query(query)
                for sub_q in sub_queries:
                    new_context = retrieve_with_plan(sub_q, plan)
                    context = merge_and_rerank(context, new_context)
            else:
                break
        
        # Reason
        answer, confidence = reason(query, context)
        
        # Slow loop: reflection (optional)
        if self.slow_config.enabled:
            if confidence >= self.slow_config.decision_threshold:
                return {
                    "answer": answer,
                    "citations": extract_citations(context),
                    "confidence": confidence,
                    "metadata": {
                        "planner_mode": "hrm",
                        "fast_loops": _,
                        "slow_loops": 0
                    }
                }
            else:
                # Reflect and adjust
                plan = refine_plan(plan, context, confidence)
                context = retrieve_with_plan(query, plan)
                answer, confidence = reason(query, context)
                return {
                    "answer": answer,
                    "citations": extract_citations(context),
                    "confidence": confidence,
                    "metadata": {
                        "planner_mode": "hrm",
                        "fast_loops": _,
                        "slow_loops": 1
                    }
                }
        else:
            return {
                "answer": answer,
                "citations": extract_citations(context),
                "confidence": confidence,
                "metadata": {
                    "planner_mode": "fast_only",
                    "fast_loops": _,
                    "slow_loops": 0
                }
            }
```

### 6.4 `optimizers.py` — Post-Retrieval Optimization

```python
class PostRetrievalOptimizer:
    def optimize(self, reranked: List, category: str) -> List:
        """Adjacent-packing, dedupe, diversity, hierarchical cite."""
        # 1. Adjacent packing
        packed = self.pack_adjacent(reranked)
        # 2. Deduplication
        deduplicated = self.deduplicate(packed)
        # 3. Diversity guard
        diverse = self.apply_diversity_cap(deduplicated, category)
        # 4. Hierarchical citation
        cited = self.add_hierarchical_paths(diverse)
        return cited
    
    def pack_adjacent(self, docs: List) -> List:
        # Merge contiguous chunks from same doc/section
        pass
    
    def deduplicate(self, docs: List) -> List:
        # Remove duplicates by text hash
        pass
    
    def apply_diversity_cap(self, docs: List, category: str) -> List:
        # Cap single doc at X% of slots
        pass
    
    def add_hierarchical_paths(self, docs: List) -> List:
        # Add citation paths: doc > section > para
        pass
```

### 6.5 `models_local.py` — Local Model Bindings

```python
from sentence_transformers import SentenceTransformer, CrossEncoder

class LocalEmbedder:
    def __init__(self, model_name: str = "bge-m3"):
        self.model = SentenceTransformer(model_name)
    
    def embed(self, text: str) -> List[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()

class LocalReranker:
    def __init__(self, model_name: str = "bge-reranker-large"):
        self.model = CrossEncoder(model_name)
    
    def rerank(self, query: str, docs: List[str]) -> List[Tuple[int, float]]:
        pairs = [(query, doc) for doc in docs]
        scores = self.model.predict(pairs)
        return sorted(enumerate(scores), key=lambda x: -x[1])

class LocalLLM:
    def __init__(self, model_path: str):
        from llama_cpp import Llama
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=8
        )
    
    async def reason(self, prompt: str) -> str:
        response = self.llm(prompt, max_tokens=2048)
        return response["choices"][0]["text"]
```

### 6.6 `service_windows.py` — Windows Service & Daemon

```python
import win32serviceutil
from pywin32 import servicebase

class AstraMultiRAGService(servicebase.ServiceFramework):
    _svc_name_ = "AstraMultiRAGService"
    _svc_display_name_ = "ASTRA Multi-RAG System"
    _svc_description_ = "Category-aware retrieval with hierarchical reasoning"
    
    def __init__(self, args):
        servicebase.ServiceFramework.__init__(self, args)
    
    def SvcDoRun(self):
        # Ingestion daemon
        ingestion_daemon = IngestionDaemon(config.service.ingestion_daemon)
        ingestion_daemon.start()
        
        # HRM planner service
        planner_service = PlannerService(config.service.planner_service)
        planner_service.start()
    
    def SvcStop(self):
        # Graceful shutdown
        pass

class IngestionDaemon:
    def __init__(self, config):
        self.config = config
        self.watchers = []
    
    def start(self):
        for watch_dir in self.config.watch_directories:
            watcher = FileWatcher(watch_dir, self.on_file_change)
            watcher.start()
            self.watchers.append(watcher)
    
    def on_file_change(self, file_path: str):
        # Trigger ingestion
        ingest(file_path, self.config.batch_interval_sec)
```

### 6.7 `astra_rag_cli.py` — Traceable CLI

```python
#!/usr/bin/env python3
"""ASTRA Multi-RAG CLI with full tracing."""

import click
from pathlib import Path
import json

@click.command()
@click.option('--query', '-q', required=True, help='Query string')
@click.option('--categories', '-c', multiple=True, help='Filter to categories')
@click.option('--policy', '-p', default='hrm', help='Retrieval policy')
@click.option('--trace', '-t', is_flag=True, help='Verbose trace output')
def query_cmd(query: str, categories: list, policy: str, trace: bool):
    """Execute a query with full RAG pipeline."""
    
    planner = HRMPlanner(config)
    
    result = planner.answer(query, policy=policy)
    
    # Pretty-print result
    print(f"Answer: {result['answer']}\n")
    print(f"Confidence: {result['confidence']:.2%}\n")
    
    print("Citations:")
    for i, cite in enumerate(result['citations'], 1):
        print(f"  [{i}] {cite['hierarchical_path']}")
        print(f"       URI: {cite['uri']}")
        print(f"       Span: {cite['text_span'][:80]}...\n")
    
    if trace:
        print("Metadata:")
        print(json.dumps(result['metadata'], indent=2))

@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--category', '-c', required=True, help='Category for ingestion')
@click.option('--consent', default='private', help='Consent scope')
@click.option('--pii', is_flag=True, help='Mark as containing PII')
def ingest_cmd(file_path: str, category: str, consent: str, pii: bool):
    """Ingest a document."""
    
    doc_id = ingest_document(
        path=file_path,
        category=category,
        consent=consent,
        pii_flag=pii
    )
    
    print(f"✅ Ingested: {doc_id}")

@click.group()
def cli():
    pass

cli.add_command(query_cmd, name='query')
cli.add_command(ingest_cmd, name='ingest')

if __name__ == '__main__':
    cli()
```

---

## 7. Consent & Retention Policies

### 7.1 Document Metadata

Every ingested document carries:

```python
{
    "doc_id": "sha256_hash[:16]",
    "consent_scope": "private",  # private | shared | public
    "retention_days": 365,
    "pii_flag": False,
    "created_at": "2025-10-20T12:00:00Z",
    "uri": "file://...",
    "tags": ["ai_engineering", "research"]
}
```

### 7.2 Consolidation Job (Daily)

```python
async def consolidation_job():
    """Run daily at 02:00 UTC."""
    
    # 1. Expire old documents
    expired = query_docs(retention_expired=True)
    for doc in expired:
        delete_document(doc.doc_id)
    
    # 2. Obfuscate PII
    pii_docs = query_docs(pii_flag=True, last_obfuscate=older_than_1_day)
    for doc in pii_docs:
        obfuscate_pii_in_store(doc.doc_id)
    
    # 3. Generate Daily Brief
    daily_content = summarize_ingested_24h()
    store_memory(
        doc_id=f"daily_brief_{today}",
        text=daily_content,
        category="operations_systems"
    )
    
    # 4. Snapshot Qdrant
    snapshot_qdrant()
    
    # 5. VACUUM SQLite
    vacuum_sqlite()
```

---

## 8. Observability & Eval

### 8.1 Telemetry Per Query

```json
{
    "query_id": "uuid",
    "query": "How do neural networks encode music theory?",
    "categories_routed": ["ai_engineering", "music_film"],
    "retrieval_time_ms": 245,
    "sparse": {
        "time_ms": 35,
        "bm25_k": 60,
        "results": 45
    },
    "dense": {
        "time_ms": 50,
        "vec_k": 60,
        "results": 52
    },
    "rerank": {
        "time_ms": 40,
        "input_count": 40,
        "output_count": 10
    },
    "fusion": {
        "mode": "attention_gate",
        "weights": {"ai_eng": 1.0, "music": 0.9},
        "gates": {"ai_eng": 0.95, "music": 1.1}
    },
    "planner": {
        "fast_loops": 1,
        "slow_loops": 0,
        "evidence_gap_detected": false
    },
    "source_diversity": 0.78,
    "hit_overlap_ratio": 0.15,
    "answer_confidence": 0.85,
    "final_context_tokens": 2847
}
```

### 8.2 RAG Eval Harness

```python
class RAGEvaluator:
    def __init__(self, datasets: Dict[str, str]):
        self.datasets = datasets  # {category: path_to_qa_jsonl}
    
    async def evaluate(self) -> Dict:
        """Run eval across all categories."""
        metrics = {}
        
        for category, dataset_path in self.datasets.items():
            qa_pairs = load_jsonl(dataset_path)
            
            results = []
            for qa in qa_pairs:
                answer = planner.answer(qa['question'], policy='eval')
                results.append({
                    "hit@10": answer in qa['gold_answers'][:10],
                    "mrr@10": compute_mrr(answer, qa['gold_answers'][:10]),
                    "context_tokens": answer['metadata']['final_context_tokens'],
                    "diversity": answer['metadata']['source_diversity']
                })
            
            metrics[category] = {
                "hit@10": mean([r["hit@10"] for r in results]),
                "mrr@10": mean([r["mrr@10"] for r in results]),
                "avg_context_tokens": mean([r["context_tokens"] for r in results]),
                "avg_diversity": mean([r["diversity"] for r in results])
            }
        
        # Regression check
        baseline = load_baseline_metrics()
        for cat, cat_metrics in metrics.items():
            for metric, value in cat_metrics.items():
                baseline_val = baseline[cat][metric]
                if (value - baseline_val) / baseline_val < -0.05:
                    raise RuntimeError(f"Regression detected: {cat}/{metric}")
        
        return metrics
```

---

## 9. Integration with ASTRA Core

### 9.1 Memory Bridge Integration

```python
from astra.bridge.memory_bridge import MemoryBridgeService

class MultiRAGMemoryAdapter:
    def __init__(self, memory_bridge: MemoryBridgeService):
        self.bridge = memory_bridge
    
    def store_retrieved_context(self, query: str, answer_result: Dict):
        """
        After answering a query, store the result in episodic memory.
        """
        fact = {
            "subject": "rag_query",
            "predicate": "answered",
            "object": query,
            "context": answer_result['citations'],
            "confidence": answer_result['confidence']
        }
        
        self.bridge.record_interpretation(
            safe_text=answer_result['answer'],
            meta={
                "query": query,
                "categories": answer_result['metadata']['categories_used'],
                "confidence": answer_result['confidence']
            }
        )
    
    def search_prior_answers(self, query: str):
        """
        Query episodic memory for prior answers on related queries.
        """
        # Retrieve similar past queries and answers
        pass
```

### 9.2 Orchestrator Integration

```python
from astra.core.orchestrator import RuntimeOrchestrator

class MultiRAGOrchestrationAction:
    """
    Action type for Runtime Orchestrator to trigger Multi-RAG queries.
    """
    
    action_type = "multi_rag_query"
    
    def __init__(self, planner: HRMPlanner):
        self.planner = planner
    
    async def execute(self, query: str, policy: str = "hrm") -> Dict:
        result = await self.planner.answer(query, policy=policy)
        
        # Log to orchestrator
        return {
            "status": "success",
            "result": result,
            "action_id": generate_id()
        }
```

---

## 10. Operational Runbook (Windows)

### 10.1 Installation

```bash
# 1. Install dependencies
pip install qdrant-client sentence-transformers chromadb sqlalchemy

# 2. Create data directories
mkdir %APPDATA%\ASTRA\data
mkdir %APPDATA%\ASTRA\vectors
mkdir %APPDATA%\ASTRA\logs

# 3. Download models
huggingface-cli download sentence-transformers/bge-m3
huggingface-cli download cross-encoders/bge-reranker-large

# 4. Initialize Qdrant (local mode)
python -m qdrant_client.setup_local_db --path %APPDATA%\ASTRA\vectors\qdrant_storage

# 5. Register Windows Service
python service_windows.py install
python service_windows.py start
```

### 10.2 Configuration

Edit `%APPDATA%\ASTRA\config.yaml` (provided above).

### 10.3 Query Commands

```bash
# Simple query
python astra_rag_cli.py query -q "How do neural networks learn?" -t

# Query with category filter
python astra_rag_cli.py query -q "Neural networks" -c ai_engineering -c cognition_spirit

# Ingest a document
python astra_rag_cli.py ingest /path/to/document.pdf -c ai_engineering

# Ingest with PII flag
python astra_rag_cli.py ingest /path/to/survey.pdf -c music_film --pii

# Run evaluation
python -m astra.rag.eval
```

---

## 11. Milestones & Exit Criteria

### M0 — Baseline Scaffold
- **Deliverable:** Ingest → Retrieve (dense+FTS) → Print top-k
- **Exit:** Hit@10 ≥ 0.7 on smoke test (20 Q/A pairs)

### M1 — Chunking Suite
- **Deliverable:** All 6 chunker implementations (code-aware, semantic, recursive, sliding, adaptive, sentence)
- **Exit:** Unit tests pass; all modes work on diverse content types

### M2 — Post-Retrieval Optimizer
- **Deliverable:** Adjacent-packing, dedup, diversity, hierarchical citations
- **Exit:** 20% fewer hallucinated spans in eval; citations are accurate

### M3 — Fusion Layer
- **Deliverable:** Weighted + attention-gate fusion across categories
- **Exit:** Macro MRR@10 +8–12% vs single-category baseline

### M4 — HRM Planner
- **Deliverable:** Fast/slow loops, re-query logic, answerability heuristic
- **Exit:** Reduces "insufficient context" failures ≥30%

### M5 — Consent & Consolidation
- **Deliverable:** Retention enforcement, snapshots, PII obfuscation
- **Exit:** PII tests pass; snapshots restorable in under 5 min

### M6 — Observability & CLI
- **Deliverable:** Metrics, logs, CLI with full tracing
- **Exit:** One-command debug capture; eval harness passes regression tests

---

## 12. Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| **Edge loss between chunks** | Vector-sliding embeddings capture context at chunk boundaries |
| **Over-concentration on single doc** | Diversity guard caps doc at 40% of result slots |
| **Router misclassification** | Multi-label routing + fallback to zero-shot classifier + attention fusion |
| **PII bleed into embeddings** | Redactors for emails/phones before embedding; obfuscation on consolidation job |
| **Slow retrieval latency** | Cache query embeddings; pre-compute category index metadata; HNSW ef tuning |
| **Eval regression** | Blocking release on regression; continuous benchmark suite |
| **Qdrant disk space** | Automated snapshots + pruning; retention policies |

---

## Next Steps (Immediate)

1. **M0 — Scaffold** (Day 1–2)
   - Create `multi_rag_core.py` with basic ingest/retrieve/rank
   - Load Qdrant + FTS5 index
   - Test on smoke dataset

2. **M1 — Chunking** (Day 3–4)
   - Implement all 6 chunkers
   - Add vector-sliding logic
   - Unit test each chunker

3. **M2 — Post-Retrieval** (Day 5)
   - Adjacent-packing, dedup, diversity, hierarchical cite
   - Integration test with chunker output

4. **M3 — Fusion** (Day 6)
   - Weighted fusion baseline
   - Attention-gate MLP (mock weights initially)
   - Cross-category eval

5. **M4 — HRM Planner** (Day 7–8)
   - Fast loop with evidence-gap detection
   - Slow loop with reflection
   - End-to-end integration test

6. **M5–M6** (Days 9–10)
   - Consent/retention policies
   - Windows service + CLI
   - Full eval harness

---

## Appendix: Example End-to-End Query Flow

**Query:** "How can I apply Q-learning in music composition?"

**Routing:**
```
Router detects keywords: Q-learning (ai_eng) + music composition (music_film)
Categories: [ai_engineering, music_film]
```

**Sparse Search (FTS5):**
```
ai_engineering: BM25 top 60 → titles + abstracts mention "Q-learning", "algorithm"
music_film: BM25 top 50 → titles mention "composition", "generative"
```

**Dense Search (ANN + Vector-Sliding):**
```
Query embedding: embed("How can I apply Q-learning in music composition?")
ai_eng results (vec_k=60): papers on RL, algorithm implementations
music_film results (vec_k=70): music theory PDFs, production guides
Vector-sliding: max over offsets for edge-context preservation
```

**Hybrid Mix:**
```
ai_eng: α=0.5 → 0.5*dense + 0.5*sparse (balanced)
music_film: α=0.4 → 0.4*dense + 0.6*sparse (bias keyword)
Rerank top 40 → top 20 per category
```

**Cross-Category Fusion (Attention-Gate):**
```
Query features: [length=10, entropy=0.75, keywords={ai_eng:4, music:3}, domain=hybrid]
MLP gates: {ai_eng: 0.95, music_film: 1.1}
Fused scores: 0.95 * ai_eng_scores + 1.1 * music_scores
Unified top-K
```

**HRM Planner Fast Loop:**
```
Iteration 1: Source diversity = 0.65 (sufficient)
No re-query needed → Proceed to reasoning
```

**Reasoning:**
```
LLM receives:
- Query: "How can I apply Q-learning in music composition?"
- Context (packed, diverse, ~2800 tokens):
  [1] ai_engineering/research_paper_12 > Section 3 > Para 2: "Q-learning algorithm..."
  [2] music_film/composition_guide_5 > Chapter 7 > Para 1: "Generative music techniques..."
  [3] ai_engineering/code_repo_3 > Function: "def q_learning_agent()..."

Output: "Q-learning applies to music composition via state-action reward models...
  - Compose state: current note sequence + harmonic context
  - Action space: next note candidates
  - Reward: musical coherence + theory adherence
  Citations: [1], [2], [3]
  Confidence: 0.87"
```

**Observability:**
```json
{
  "query_id": "q_abc123",
  "retrieval_time_ms": 285,
  "categories_routed": ["ai_engineering", "music_film"],
  "source_diversity": 0.65,
  "planner_iterations": 1,
  "final_confidence": 0.87
}
```

---

**🎉 End of Blueprint. Ready to implement!**

For questions or customization requests, refer to the configuration (`config.yaml`) and module interfaces (`chunkers.py`, `fusion.py`, `planner.py`, etc.).

