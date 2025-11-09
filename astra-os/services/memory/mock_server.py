"""
ASTRA Dream Grove — Mock Memory Service (No ML Dependencies)
Lightweight FastAPI server for testing UI without heavy ML models.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

app = FastAPI(title="Dream Grove Memory Service (Mock)")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock in-memory storage
memories: list[dict] = []


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


@app.post("/memory/add")
async def add_memory(request: AddMemoryRequest):
    """Add a new memory fragment"""
    start = time.perf_counter()
    
    memory_id = len(memories)
    memory = {
        "id": memory_id,
        "text": request.text,
        "timestamp": time.time(),
        "metadata": request.metadata or {}
    }
    memories.append(memory)
    
    latency = (time.perf_counter() - start) * 1000
    
    return {
        "id": memory_id,
        "index_size": len(memories),
        "latency_ms": round(latency, 2)
    }


@app.post("/memory/search", response_model=SearchResponse)
async def search_memories(request: SearchRequest):
    """Search memories (mock - returns random matches)"""
    start = time.perf_counter()
    
    # Simple mock: return memories that contain query words
    query_lower = request.query.lower()
    matches = []
    
    for mem in memories:
        if query_lower in mem["text"].lower():
            matches.append(SearchResult(
                id=mem["id"],
                text=mem["text"],
                score=0.85,  # Mock score
                decay=0.9,  # Mock decay
                value=76.5,  # Mock value
                metadata=mem.get("metadata")
            ))
    
    # If no matches, return most recent memories
    if not matches and memories:
        for mem in memories[-min(request.top_k, len(memories)):]:
            matches.append(SearchResult(
                id=mem["id"],
                text=mem["text"],
                score=0.65,
                decay=0.8,
                value=52.0,
                metadata=mem.get("metadata")
            ))
    
    latency = (time.perf_counter() - start) * 1000
    
    return SearchResponse(
        results=matches[:request.top_k],
        latency_ms=round(latency, 2)
    )


@app.get("/memory/stats")
async def get_stats():
    """Get memory index statistics"""
    return {
        "index_size": len(memories),
        "avg_decay": 0.85,
        "low_value_count": 0,
        "embedding_dim": 384,
        "mode": "mock"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "mock (no ML)",
        "index_size": len(memories),
        "mode": "testing"
    }


if __name__ == "__main__":
    import uvicorn
    print("🌌 Starting Dream Grove Memory Service (Mock Mode)")
    print("📍 Listening on http://127.0.0.1:7007")
    print("⚡ No ML models loaded - lightweight testing mode")
    uvicorn.run(app, host="127.0.0.1", port=7007, log_level="info")
