# pyright: reportMissingImports=false, reportMissingTypeStubs=false
# services/documents/api.py
import os
import time
import json
import hashlib
import importlib
from typing import Optional, List, Dict, cast
from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ---------- CONFIG ----------
BRIDGE_KEYS_FILE = os.environ.get("BRIDGE_KEYS_FILE", "/run/secrets/bridge_keys")
FALLBACK_API_KEY = os.environ.get("BRIDGE_API_KEY")
USE_QDRANT = os.environ.get("USE_QDRANT", "true").lower() in ("1", "true", "yes")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "astra_docs")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DOC_INDEX_DIR = os.environ.get("DOC_INDEX_DIR", "/data/index")
CHUNK_SIZE = int(os.environ.get("DOC_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("DOC_CHUNK_OVERLAP", "100"))

os.makedirs(DOC_INDEX_DIR, exist_ok=True)

# ---------- METRICS ----------
DOCS_INGEST_TOTAL = Counter("docs_ingest_total", "Number of documents ingested")
DOCS_INGEST_DURATION = Histogram("docs_ingest_duration_seconds", "Docs ingest duration")
DOCS_SEARCH_TOTAL = Counter("docs_search_total", "Number of semantic searches")
DOCS_SEARCH_DURATION = Histogram("docs_search_duration_seconds", "Docs search duration")

# ---------- APP ----------
app = FastAPI(title="ASTRA Documents Service", version="0.3.0")

# ---------- KEYS / RBAC ----------
def load_keys() -> Dict[str, Dict[str, object]]:
    if os.path.exists(BRIDGE_KEYS_FILE):
        try:
            with open(BRIDGE_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return cast(Dict[str, Dict[str, object]], data)
                return {}
        except Exception:
            return {}
    return {}

KEYS = load_keys()

def check_api_key(x_api_key: Optional[str], required_scope: Optional[str] = None) -> bool:
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key")
    if FALLBACK_API_KEY and x_api_key == FALLBACK_API_KEY:
        return True
    if KEYS:
        info = KEYS.get(x_api_key)
        if not info:
            raise HTTPException(status_code=403, detail="Invalid API key")
        if required_scope and required_scope not in info.get("scopes", []):
            raise HTTPException(status_code=403, detail="Insufficient scope")
        return True
    raise HTTPException(status_code=403, detail="Invalid API key (no keys configured)")

# ---------- EMBEDDINGS + QDRANT CLIENT ----------
embedder = None
qdrant = None
if USE_QDRANT:
    try:
        st_mod = importlib.import_module("sentence_transformers")
        SentenceTransformer = getattr(st_mod, "SentenceTransformer")
        embedder = SentenceTransformer(EMBEDDING_MODEL)
    except Exception:
        embedder = None
    try:
        qd_mod = importlib.import_module("qdrant_client")
        QdrantClient = getattr(qd_mod, "QdrantClient")
        http_models = importlib.import_module("qdrant_client.http.models")
        Distance = getattr(http_models, "Distance")
        VectorParams = getattr(http_models, "VectorParams")
        qdrant = QdrantClient(url=QDRANT_URL)
        # ensure collection exists
        if QDRANT_COLLECTION not in [c.name for c in qdrant.get_collections().collections]:
            # default dim 384 for MiniLM; adapt if you change model
            qdrant.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
    except Exception:
        qdrant = None

# ---------- UTILITIES ----------
def extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        fitz = importlib.import_module("fitz")
    except Exception:
        raise HTTPException(status_code=500, detail="pymupdf (fitz) not installed")
    doc = fitz.open(stream=data, filetype="pdf")  # type: ignore[attr-defined]
    pages = [p.get_text("text") for p in doc]
    return "\n".join(pages)

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    tokens = text.split()
    chunks = []
    i = 0
    L = len(tokens)
    while i < L:
        chunk = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += max(1, chunk_size - overlap)
    return chunks

def embed_texts(texts: List[str]) -> List[List[float]]:
    if embedder:
        vecs = embedder.encode(texts, show_progress_bar=False).tolist()
        return cast(List[List[float]], vecs)
    # fallback pseudo-embedding (not semantic)
    return cast(List[List[float]], [[float(int(hashlib.sha256(t.encode()).hexdigest()[:8], 16) % 1000) / 1000.0 for _ in range(384)] for t in texts])

# ---------- MODELS ----------
class IngestResponse(BaseModel):
    ingested_chunks: int
    collection: str

class SearchResult(BaseModel):
    id: str
    text: str
    score: float

# ---------- ENDPOINTS ----------
@app.get("/health")
def health() -> Dict[str, object]:
    return {"ok": True, "version": "0.3.0", "qdrant": bool(qdrant), "embedder": bool(embedder)}

@app.post("/v1/documents/ingest", response_model=IngestResponse)
def ingest_document(file: UploadFile = File(...), api_key: Optional[str] = Header(None, alias="x-api-key")) -> IngestResponse:
    check_api_key(api_key, required_scope="docs:ingest")
    start = time.time()
    data = file.file.read()
    text = extract_text_from_pdf_bytes(data)
    chunks = chunk_text(text)
    n = 0
    if USE_QDRANT and qdrant and embedder:
        vecs = embed_texts(chunks)
        points = []
        for i, (c, v) in enumerate(zip(chunks, vecs)):
            pid = f"{file.filename}::{i}"
            points.append({
                "id": pid,
                "vector": v,
                "payload": {"text": c, "source": file.filename}
            })
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)
        n = len(points)
    else:
        os.makedirs(DOC_INDEX_DIR, exist_ok=True)
        idx_path = os.path.join(DOC_INDEX_DIR, f"{QDRANT_COLLECTION}.jsonl")
        with open(idx_path, "a", encoding="utf-8") as f:
            for i, c in enumerate(chunks):
                rec = {"id": f"{file.filename}::{i}", "text": c, "source": file.filename}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
    DOCS_INGEST_TOTAL.inc(n)
    DOCS_INGEST_DURATION.observe(time.time() - start)
    return IngestResponse(ingested_chunks=n, collection=QDRANT_COLLECTION)

@app.get("/v1/documents/search", response_model=List[SearchResult])
def search_documents(q: str, top: int = 5, api_key: Optional[str] = Header(None, alias="x-api-key")) -> List[SearchResult]:
    check_api_key(api_key, required_scope="docs:search")
    start = time.time()
    DOCS_SEARCH_TOTAL.inc()
    results: List[SearchResult] = []
    if USE_QDRANT and qdrant and embedder:
        vec = embedder.encode([q])[0].tolist()
        hits = qdrant.search(collection_name=QDRANT_COLLECTION, query_vector=vec, limit=top)
        for h in hits:
            payload = h.payload or {}
            results.append(SearchResult(id=str(h.id), text=payload.get("text", ""), score=float(h.score or 0.0)))
    else:
        idx_path = os.path.join(DOC_INDEX_DIR, f"{QDRANT_COLLECTION}.jsonl")
        if os.path.exists(idx_path):
            scored = []
            with open(idx_path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    score = rec["text"].lower().count(q.lower())
                    if score > 0:
                        scored.append((score, rec))
            scored.sort(key=lambda x: x[0], reverse=True)
            for s, rec in scored[:top]:
                results.append(SearchResult(id=rec["id"], text=rec["text"], score=float(s)))
    DOCS_SEARCH_DURATION.observe(time.time() - start)
    return results

@app.get("/metrics")
def metrics() -> JSONResponse:
    data = generate_latest()
    return JSONResponse(content=(data.decode() if isinstance(data, (bytes, bytearray)) else data), media_type=CONTENT_TYPE_LATEST)
