# services/memory/server.py - FastAPI embeddings + FAISS service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
import uvicorn, numpy as np
import faiss, os, json
import time

# Try importing Cython kernels, fallback to pure Python
CYTHON_OK = False
try:
    from astra_cykernels.kernels import batched_cosine
    CYTHON_OK = True
    print("✓ Cython kernels loaded")
except ImportError:
    from astra_cykernels.fallback import batched_cosine
    print("⚠ Cython unavailable, using fallback")

MODEL_NAME = os.environ.get("ASTRA_EMBED_MODEL", "all-MiniLM-L6-v2")
INDEX_PATH = "services/memory/index.faiss"
META_PATH  = "services/memory/meta.jsonl"

app = FastAPI(title="ASTRA Memory Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading embedding model...")
model = SentenceTransformer(MODEL_NAME)
d = 384  # all-MiniLM-L6-v2 dimension
index = faiss.IndexFlatIP(d)
meta: List[dict] = []

if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = [json.loads(x) for x in f]
    print(f"✓ Loaded {len(meta)} memories from disk")

class AddPayload(BaseModel):
    texts: List[str]
    meta: List[dict] = []

class QueryPayload(BaseModel):
    texts: List[str]
    k: int = 5

@app.post("/embed")
def embed(p: AddPayload):
    vecs = model.encode(p.texts, normalize_embeddings=True)
    return {"vectors": np.asarray(vecs).tolist()}

@app.post("/add")
def add(p: AddPayload):
    vecs = model.encode(p.texts, normalize_embeddings=True)
    index.add(np.asarray(vecs, dtype="float32"))
    with open(META_PATH, "a", encoding="utf-8") as f:
        for m in (p.meta or [{}] * len(p.texts)):
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    meta.extend(p.meta or [{}] * len(p.texts))
    faiss.write_index(index, INDEX_PATH)
    return {"ok": True, "count": index.ntotal}

@app.post("/search")
def search(p: QueryPayload):
    if index.ntotal == 0:
        return {"results": [], "count": 0}
    
    q = model.encode(p.texts, normalize_embeddings=True).astype("float32")
    D, I = index.search(q, min(p.k, index.ntotal))
    results = []
    for row_i, (drow, irow) in enumerate(zip(D, I)):
        hits = []
        for dist, idx in zip(drow.tolist(), irow.tolist()):
            if idx < 0 or idx >= len(meta): 
                continue
            hits.append({"score": float(dist), "meta": meta[idx]})
        results.append(hits)
    return {"results": results, "count": index.ntotal}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "index_size": index.ntotal,
        "embedding_dim": d
    }

@app.post("/cosine")
def cosine_benchmark():
    """
    Benchmark endpoint for Cython kernel performance
    Returns timing and kernel status
    """
    # Generate test data: 10k vectors of 768 dimensions
    n, dim = 10000, 768
    queries = np.random.randn(n, dim).astype("float32")
    corpus = np.random.randn(n, dim).astype("float32")
    
    # Normalize for cosine similarity
    queries = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    corpus = corpus / np.linalg.norm(corpus, axis=1, keepdims=True)
    
    # Time the computation
    start = time.perf_counter()
    _ = batched_cosine(queries, corpus)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    return {
        "ms": round(elapsed_ms, 2),
        "cython": CYTHON_OK,
        "shape": f"{n}x{dim}",
        "kernel": "cython" if CYTHON_OK else "numpy_fallback"
    }

if __name__ == "__main__":
    print("🧠 Starting ASTRA Memory Service...")
    print("📍 Listening on http://127.0.0.1:7007")
    uvicorn.run(app, host="127.0.0.1", port=7007, log_level="info")
