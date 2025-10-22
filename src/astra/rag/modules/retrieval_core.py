"""
Core retrieval orchestration: BM25 (FTS5) + Dense (ANN) + Hybrid Mix + Reranking.
"""
import sqlite3
import yaml
import numpy as np
from typing import List, Dict, Any

from budget import Budget
from cache import query_cache, ann_cache, rerank_cache

from storage import VectorStore
from models_local import embed_dense, rerank_score
from router import route_categories, retriever_params
from optimizers import dedupe_hits, pack_adjacent, enforce_diversity


def bm25_fts(con: sqlite3.Connection, query: str, k: int) -> List[Dict[str, Any]]:
    """BM25 full-text search via FTS5."""
    cache_key = f"bm25:{query}:{k}"
    cached = query_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        rows = con.execute(
            "SELECT doc_id, chunk_id, text, header, path FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT ?",
            (query, k)
        ).fetchall()
        result = [
            {
                'doc_id': d,
                'chunk_id': c,
                'text': t,
                'header': h,
                'uri': p,
                'score': 0.0
            }
            for (d, c, t, h, p) in rows
        ]
        query_cache.set(cache_key, result)
        return result
    except Exception as e:
        print(f"BM25 error: {e}")
        return []


def dense_search(vs: VectorStore, collection: str, query: str, k: int, dims: int) -> List[Dict[str, Any]]:
    """Dense vector search via ANN."""
    cache_key = f"ann:{collection}:{query}:{k}:{dims}"
    cached = ann_cache.get(cache_key)
    if cached is not None:
        return cached
    qv = embed_dense([query], dims=dims)[0]
    result = vs.search(collection, qv, limit=k)
    ann_cache.set(cache_key, result)
    return result


def mix_scores(bm_hits: List[Dict[str, Any]], vec_hits: List[Dict[str, Any]], alpha: float = 0.5):
    """Mix BM25 and dense scores."""
    out = []
    
    # Normalize sparse scores by rank
    bm_norm = {(h['doc_id'], h['chunk_id']): 1.0 - i / max(1, len(bm_hits)) for i, h in enumerate(bm_hits)}
    
    for h in vec_hits:
        key = (h['doc_id'], h['chunk_id'])
        s = alpha * h.get('score', 0.0) + (1 - alpha) * bm_norm.get(key, 0.0)
        hh = dict(h)
        hh['score'] = float(s)
        out.append(hh)
    
    # Add remaining BM25 hits
    for h in bm_hits:
        key = (h['doc_id'], h['chunk_id'])
        if not any((x['doc_id'], x['chunk_id']) == key for x in out):
            hh = dict(h)
            hh['score'] = float((1 - alpha) * bm_norm.get(key, 0.0))
            out.append(hh)
    
    out.sort(key=lambda x: x['score'], reverse=True)
    return out


def rerank(query: str, hits: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """Cross-encoder reranking."""
    texts = [h['text'] for h in hits[:max(40, top_k * 3)]]
    cache_key = f"rerank:{query}:{hash(tuple(texts))}:{top_k}"
    cached = rerank_cache.get(cache_key)
    if cached is not None:
        return cached
    scores = rerank_score(query, texts)
    rescored = []
    for i, h in enumerate(hits[:len(texts)]):
        hh = dict(h)
        hh['score'] = float(scores[i])
        rescored.append(hh)
    rescored.sort(key=lambda x: x['score'], reverse=True)
    result = rescored[:top_k * 2]
    rerank_cache.set(cache_key, result)
    return result


def retrieve_category(con: sqlite3.Connection, vs: VectorStore, cfg: Dict[str, Any], 
                      category: str, query: str) -> List[Dict[str, Any]]:
    """Retrieve from single category (5-stage pipeline)."""
    prm = retriever_params(category)
    collection = f"{cfg['memory']['vector']['collection_prefix']}{category}"
    # Read latency budget from config
    latency_budget = cfg.get('system', {}).get('latency_budget_ms', 1500)
    budget = Budget(latency_budget)

    # Dynamic candidate sizes based on budget and query length
    easy = len(query) < 60
    bm25_k = prm['bm25_k']
    vec_k = prm['vec_k']
    top_k = prm['top_k']
    base_ef = cfg.get('system', {}).get('policies', {}).get('ann', {}).get('base_ef', 96)
    base_k = cfg.get('system', {}).get('policies', {}).get('ann', {}).get('base_k', 60)
    # Smart switch for ANN params
    if budget.left() < 300:
        vec_k = max(16, base_k // 2)
        ef = max(32, base_ef // 2)
    elif easy:
        vec_k = base_k // 2
        ef = base_ef // 2
    else:
        ef = base_ef

    import time
    t_start = time.perf_counter()
    # Stage 1: BM25
    bm = bm25_fts(con, query, bm25_k)

    # Stage 2: Dense ANN
    dv = dense_search(vs, collection, query, vec_k, cfg['memory']['vector']['dims'])

    # Stage 3: Hybrid mix
    mixed = mix_scores(bm, dv, alpha=prm.get('mix_alpha', 0.5))

    # Stage 4: Rerank (cascade, budget-aware)
    rerank_depth = 24 if budget.left() > 600 else 12
    reranked = rerank(query, mixed, min(top_k, rerank_depth))

    # Stage 5: Post-optimization
    packed = pack_adjacent(dedupe_hits(reranked))[:top_k]

    # Telemetry logging
    t_end = time.perf_counter()
    latency_ms = int(1000 * (t_end - t_start))
    margin = 0.0
    if packed:
        margin = packed[0]['score'] - packed[min(1, len(packed)-1)]['score']
    diversity = len({h['doc_id'] for h in packed}) / max(1, len(packed)) if packed else 0.0
    print(f"[TELEMETRY] category={category} latency_ms={latency_ms} bm25_k={bm25_k} vec_k={vec_k} rerank_depth={rerank_depth} margin={margin:.3f} diversity={diversity:.3f}")

    return packed


def retrieve_multi(query: str, categories: List[str] = None, backend: str = None) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieve from multiple categories (orchestration point)."""
    cfg = yaml.safe_load(open('config.yaml', 'r', encoding='utf-8'))
    con = sqlite3.connect(cfg['memory']['db_path'])
    vs = VectorStore(backend=backend or cfg['memory']['vector']['backend'])
    
    cats = categories or route_categories(query)
    out = {}
    active_cats = ','.join(cats)
    print(f"[TELEMETRY] active_categories={active_cats}")
    for c in cats:
        out[c] = retrieve_category(con, vs, cfg, c, query)
    return out
