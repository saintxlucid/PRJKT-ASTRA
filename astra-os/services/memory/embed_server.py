"""
ASTRA Dream Grove — Local Embeddings Service
Provides fast local embedding generation and vector search using FAISS.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
import time
from pathlib import Path

# Try importing Cython kernels, fallback to pure Python
CYTHON_OK = False
try:
    from astra_cykernels.kernels import batched_cosine
    CYTHON_OK = True
    print("✓ Cython kernels loaded")
except ImportError:
    from astra_cykernels.fallback import batched_cosine
    print("⚠ Cython unavailable, using fallback")

app = FastAPI(title="Dream Grove Memory Service")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize model
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# Initialize FAISS index
index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product for cosine similarity
memories: list[dict] = []

# Persistence
INDEX_PATH = Path(__file__).parent / "index.faiss"
MEMORIES_PATH = Path(__file__).parent / "memories.json"


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    vectors: list[list[float]]
    latency_ms: float


class AddMemoryRequest(BaseModel):
    text: str
    metadata: dict | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    id: int
    text: str
    score: float
    decay: float
    value: float
    metadata: dict | None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    latency_ms: float


@app.on_event("startup")
async def load_index():
    """Load persisted index and memories on startup"""
    global index, memories
    
    if INDEX_PATH.exists() and MEMORIES_PATH.exists():
        try:
            index = faiss.read_index(str(INDEX_PATH))
            with open(MEMORIES_PATH, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            print(f"✓ Loaded {len(memories)} memories from disk")
        except Exception as e:
            print(f"⚠ Could not load index: {e}")
            index = faiss.IndexFlatIP(EMBEDDING_DIM)
            memories = []
    else:
        print("✓ Starting with empty index")


@app.on_event("shutdown")
async def save_index():
    """Persist index and memories on shutdown"""
    try:
        faiss.write_index(index, str(INDEX_PATH))
        with open(MEMORIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2)
        print(f"✓ Saved {len(memories)} memories to disk")
    except Exception as e:
        print(f"⚠ Could not save index: {e}")


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """Generate embeddings for input texts"""
    start = time.perf_counter()
    
    try:
        vectors = model.encode(request.texts).tolist()
        latency = (time.perf_counter() - start) * 1000
        
        return EmbedResponse(vectors=vectors, latency_ms=round(latency, 2))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/add")
async def add_memory(request: AddMemoryRequest):
    """Add a new memory fragment to the index"""
    start = time.perf_counter()
    
    try:
        # Generate embedding
        vector = model.encode([request.text])[0]
        
        # Normalize for cosine similarity
        faiss.normalize_L2(vector.reshape(1, -1))
        
        # Add to FAISS
        index.add(vector.reshape(1, -1))
        
        # Store metadata
        memory = {
            "id": len(memories),
            "text": request.text,
            "timestamp": time.time(),
            "decay": 1.0,
            "score": 100.0,
            "metadata": request.metadata or {}
        }
        memories.append(memory)
        
        latency = (time.perf_counter() - start) * 1000
        
        return {
            "id": memory["id"],
            "latency_ms": round(latency, 2),
            "index_size": len(memories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """Search memories by semantic similarity"""
    start = time.perf_counter()
    
    if len(memories) == 0:
        return SearchResponse(results=[], latency_ms=0)
    
    try:
        # Generate query embedding
        query_vector = model.encode([request.query])[0]
        faiss.normalize_L2(query_vector.reshape(1, -1))
        
        # Search FAISS
        k = min(request.top_k, len(memories))
        distances, indices = index.search(query_vector.reshape(1, -1), k)
        
        # Build results with decay
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            
            mem = memories[idx]
            
            # Calculate decay based on age (simple exponential)
            age_hours = (time.time() - mem["timestamp"]) / 3600
            decay = max(0.1, np.exp(-age_hours / 168))  # 7-day half-life
            
            value = mem["score"] * decay
            
            results.append(SearchResult(
                id=mem["id"],
                text=mem["text"],
                score=float(distances[0][i]),
                decay=float(decay),
                value=float(value),
                metadata=mem.get("metadata")
            ))
        
        latency = (time.perf_counter() - start) * 1000
        
        return SearchResponse(results=results, latency_ms=round(latency, 2))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats")
async def get_stats():
    """Get memory index statistics"""
    if len(memories) == 0:
        return {
            "index_size": 0,
            "avg_decay": 0,
            "low_value_count": 0
        }
    
    # Calculate decay for all memories
    decays = []
    low_value = 0
    
    for mem in memories:
        age_hours = (time.time() - mem["timestamp"]) / 3600
        decay = max(0.1, np.exp(-age_hours / 168))
        decays.append(decay)
        
        if decay < 0.3:
            low_value += 1
    
    return {
        "index_size": len(memories),
        "avg_decay": round(np.mean(decays), 3),
        "low_value_count": low_value,
        "embedding_dim": EMBEDDING_DIM
    }


@app.post("/memory/purge")
async def purge_low_value(threshold: float = 0.3):
    """Remove memories below value threshold"""
    global memories, index
    
    if len(memories) == 0:
        return {"removed": 0, "remaining": 0}
    
    # Calculate which memories to keep
    to_keep = []
    kept_indices = []
    
    for i, mem in enumerate(memories):
        age_hours = (time.time() - mem["timestamp"]) / 3600
        decay = max(0.1, np.exp(-age_hours / 168))
        
        if decay >= threshold:
            to_keep.append(mem)
            kept_indices.append(i)
    
    removed = len(memories) - len(to_keep)
    
    if removed > 0:
        # Rebuild index with kept vectors
        new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
        
        for idx in kept_indices:
            # Re-encode and add
            vector = model.encode([memories[idx]["text"]])[0]
            faiss.normalize_L2(vector.reshape(1, -1))
            new_index.add(vector.reshape(1, -1))
        
        # Update global state
        index = new_index
        memories = to_keep
        
        # Update IDs
        for i, mem in enumerate(memories):
            mem["id"] = i
    
    return {
        "removed": removed,
        "remaining": len(memories)
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "all-MiniLM-L6-v2",
        "index_size": len(memories),
        "embedding_dim": EMBEDDING_DIM
    }


@app.post("/cosine")
async def cosine_benchmark():
    """
    Benchmark endpoint for Cython kernel performance.
    Returns timing and kernel status for batched cosine similarity.
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
    import uvicorn
    print("🌌 Starting Dream Grove Memory Service...")
    print("📍 Listening on http://127.0.0.1:7007")
    uvicorn.run(app, host="127.0.0.1", port=7007, log_level="info")
