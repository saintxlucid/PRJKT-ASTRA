"""
Ingest pipeline:
- text chunking
- embedding (sentence-transformers default)
- nutrition scoring (calorie computation)
- storing to vector store adapter (Chroma/Qdrant/Simple)
- returns provenance record
"""

from __future__ import annotations
import os, time, json, logging, math
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from .vector_stores import ChromaStore, QdrantStore, SimpleVecDB
from hashlib import sha256 as _sha256

logger = logging.getLogger("astra.ingest")
logger.setLevel(logging.INFO)

# default model name
EMBED_MODEL_NAME = os.environ.get("ASTRA_EMBED_MODEL", "all-mpnet-base-v2")

# chunker
def chunk_text(text: str, max_chars: int = 800) -> List[str]:
    # naive chunker by sentences / fall back to windows
    sentences = text.split(". ")
    chunks = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) + 2 <= max_chars:
            cur = cur + (". " if cur else "") + s
        else:
            if cur:
                chunks.append(cur.strip())
            cur = s
    if cur:
        chunks.append(cur.strip())
    # final safe trim
    return [c.strip() for c in chunks if c.strip()]

# nutrition scoring formula
def nutrition_score(text: str, meta: Dict = None) -> Dict:
    meta = meta or {}
    cred = float(meta.get("credibility", 0.5))
    # novelty: token-based uniq words heuristic
    words = [w.strip(".,!?:;()[]\"'").lower() for w in text.split()]
    uniq = len(set(words))
    nov = min(1.0, uniq / max(1, min(200, len(words))))
    # emotional density: simple lexicon
    EMO_LEXICON = set(["love","hate","pain","cry","joy","rage","sacred","burn","fire","night","lost","home","bless","tears","fear"])
    emo = min(1.0, sum(1 for w in words if w in EMO_LEXICON) / 8.0)
    rel = float(meta.get("relevance", 0.5))
    fresh = float(meta.get("freshness", 0.5))
    energy = 0.25*cred + 0.20*nov + 0.20*emo + 0.20*rel + 0.15*fresh
    return {
        "credibility": round(cred, 4),
        "novelty": round(nov, 4),
        "emotional_density": round(emo, 4),
        "relevance_to_astora_intents": round(rel, 4),
        "freshness": round(fresh, 4),
        "energy_score": round(min(1.0, energy), 4)
    }

# choose store factory
def make_store(kind: str = "auto", **kwargs):
    kind = kind or os.environ.get("ASTRA_VECTOR_BACKEND", "auto")
    if kind == "auto":
        # prefer chroma if available, else qdrant, else simple
        try:
            return ChromaStore(**kwargs)
        except Exception:
            try:
                return QdrantStore(**kwargs)
            except Exception:
                return SimpleVecDB(**kwargs)
    if kind == "chroma":
        return ChromaStore(**kwargs)
    if kind == "qdrant":
        return QdrantStore(**kwargs)
    return SimpleVecDB(**kwargs)

# embedder
class Embedder:
    def __init__(self, model_name: str = EMBED_MODEL_NAME):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        # dimension known from model
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str]):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

# ingestion high-level
class Ingestor:
    def __init__(self, store: Optional[object] = None, embedder: Optional[Embedder] = None):
        self.store = store or make_store()
        self.embedder = embedder or Embedder()
        self.ingest_agent = os.environ.get("ASTRA_INGEST_AGENT", "ingest-v1")

    def ingest_text(self, text: str, source: str = "user_upload", metadata: Dict = None, chunk_chars: int = 800) -> Dict:
        metadata = metadata or {}
        chunks = chunk_text(text, max_chars=chunk_chars)
        embeddings = self.embedder.embed(chunks)
        records = []
        session_id = metadata.get("session_id", None) or f"session-{int(time.time())}"
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            vid = _sha256(chunk + str(time.time()) + str(idx))
            prov = {
                "author": metadata.get("author"),
                "source_url": metadata.get("source_url"),
                "ingest_agent": self.ingest_agent,
                "session_id": session_id,
                "signature": metadata.get("signature")
            }
            nutr = nutrition_score(chunk, metadata)
            meta = {
                "text_preview": chunk[:200],
                "source": source,
                "type": metadata.get("type", "text"),
                "chunk_index": idx,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "embedding_model": self.embedder.model_name,
                "embedding_dim": self.embedder.dim,
                "nutrition": nutr,
                "provenance": prov,
                "tags": metadata.get("tags", []),
                "consent": {"user_approved": metadata.get("user_approved", True)}
            }
            # store
            try:
                self.store.add(vid, emb, meta)
            except Exception as e:
                logger.exception("store.add failed: %s", e)
            records.append({"id": vid, "metadata": meta})
        return {"session_id": session_id, "chunks": records}

    def retrieve_by_text(self, query_text: str, top_k: int = 8, filter: Optional[Dict]=None):
        q_emb = self.embedder.embed([query_text])[0]
        return self.store.query(q_emb, top_k=top_k, filter=filter)

    def get(self, vid: str):
        return self.store.get(vid)