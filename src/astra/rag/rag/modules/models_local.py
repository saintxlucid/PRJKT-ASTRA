"""
Local model stubs for embedding and reranking.
Replace with actual BGE-M3 + BGE-Reranker when ready.
Uses deterministic pseudo-random seeding from text content.
"""
import numpy as np
import hashlib
from typing import List


def _seed_from_text(text: str) -> int:
    """Generate stable pseudo-random seed from text content."""
    h = hashlib.sha256(text.encode('utf-8', 'ignore')).hexdigest()
    return int(h[:8], 16)


def embed_dense(texts: List[str], dims: int = 128) -> np.ndarray:
    """
    Generate deterministic embeddings from texts.
    Replace with BGE-M3 later:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('BAAI/bge-m3')
        return model.encode(texts, normalize_embeddings=True)
    """
    vecs = []
    for text in texts:
        rng = np.random.default_rng(_seed_from_text(text))
        vec = rng.normal(size=(dims,)).astype('float32')
        vecs.append(vec)
    return np.stack(vecs, axis=0)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    if a.ndim == 2:
        a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
    else:
        a = a / (np.linalg.norm(a) + 1e-8)
    
    if b.ndim == 2:
        b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
    else:
        b = b / (np.linalg.norm(b) + 1e-8)
    
    return float(np.dot(a, b)) if a.ndim == 1 else a @ b.T


def rerank_score(query: str, passages: List[str]) -> List[float]:
    """
    Score passages against query.
    Replace with BGE-Reranker:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder('BAAI/bge-reranker-large')
        return model.predict([[query, p] for p in passages]).tolist()
    """
    qv = embed_dense([query])[0]
    pv = embed_dense(passages)
    sims = pv @ (qv / (np.linalg.norm(qv) + 1e-8))
    return sims.tolist()
