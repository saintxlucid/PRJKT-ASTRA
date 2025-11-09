"""
Vector store adapters: Chroma, Qdrant, and a simple JSON local fallback for dev.
Designed to be dependency-light: imports optional heavy clients at runtime.
"""

from __future__ import annotations
import os, json, time, hashlib, logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("astra.vector_stores")
logger.setLevel(logging.INFO)

# optional imports
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from chromadb.utils import embedding_functions
    _has_chroma = True
except Exception:
    _has_chroma = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    _has_qdrant = True
except Exception:
    _has_qdrant = False

# Utility
def sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ------------------------------
# Base Interface
# ------------------------------
class BaseVectorStore:
    def add(self, id: str, embedding: List[float], metadata: Dict):
        raise NotImplementedError()
    def query(self, embedding: List[float], top_k: int = 8, filter: Optional[Dict] = None) -> List[Dict]:
        raise NotImplementedError()
    def get(self, id: str) -> Optional[Dict]:
        raise NotImplementedError()
    def delete(self, id: str):
        raise NotImplementedError()
    def info(self) -> Dict:
        raise NotImplementedError()

# ------------------------------
# Chroma implementation
# ------------------------------
class ChromaStore(BaseVectorStore):
    def __init__(self, collection_name: str = "astra_memory", persist_dir: Optional[str] = None, embedding_function=None):
        if not _has_chroma:
            raise RuntimeError("chromadb not installed: pip install chromadb")
        persist_dir = persist_dir or os.environ.get("ASTRA_CHROMA_DIR", "./.chroma")
        settings = ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir)
        self.client = chromadb.Client(settings=settings)
        self.collection_name = collection_name
        if collection_name in [c.name for c in self.client.list_collections()]:
            self.col = self.client.get_collection(collection_name)
        else:
            self.col = self.client.create_collection(collection_name, embedding_function=embedding_function)
        self.embedding_fn = embedding_function

    def add(self, id: str, embedding: List[float], metadata: Dict):
        self.col.add(ids=[id], embeddings=[embedding], metadatas=[metadata], documents=[metadata.get("text_preview","")])
        return {"id": id}

    def query(self, embedding: List[float], top_k: int = 8, filter: Optional[Dict] = None):
        # chroma supports metadata filters as dict
        res = self.col.query(query_embeddings=[embedding], n_results=top_k, where=filter or {})
        items = []
        # map results
        for ids, docs, metadatas, distances in zip(res["ids"], res["documents"], res["metadatas"], res["distances"]):
            for i, _id in enumerate(ids):
                items.append({
                    "id": _id,
                    "text_preview": metadatas[i].get("text_preview"),
                    "metadata": metadatas[i],
                    "distance": distances[i]
                })
        return items

    def get(self, id: str):
        # chroma has get by id
        try:
            obj = self.col.get(ids=[id])
            if obj and obj.get("metadatas"):
                return {"id": id, "metadata": obj["metadatas"][0], "document": obj["documents"][0]}
            return None
        except Exception:
            return None

    def delete(self, id: str):
        self.col.delete(ids=[id])
        return {"id": id, "deleted": True}

    def info(self):
        return {"type": "chroma", "collection": self.collection_name}

# ------------------------------
# Qdrant implementation
# ------------------------------
class QdrantStore(BaseVectorStore):
    def __init__(self, collection_name: str = "astra_memory", url: Optional[str] = None, api_key: Optional[str] = None, prefer_grpc: bool = False):
        if not _has_qdrant:
            raise RuntimeError("qdrant-client not installed: pip install qdrant-client")
        url = url or os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection_name = collection_name
        # create if not exists (lightweight)
        try:
            self.client.get_collection(collection_name)
        except Exception:
            self.client.recreate_collection(collection_name, vectors_size=1536, distance=qmodels.Distance.COSINE)
        self.dim = 1536

    def add(self, id: str, embedding: List[float], metadata: Dict):
        payload = {"metadata": metadata}
        self.client.upsert(collection_name=self.collection_name, points=[qmodels.PointStruct(id=id, vector=embedding, payload=metadata)])
        return {"id": id}

    def query(self, embedding: List[float], top_k: int = 8, filter: Optional[Dict] = None):
        # qdrant filter works via payload as a boolean expression - we'll pass none for now
        res = self.client.search(collection_name=self.collection_name, query_vector=embedding, limit=top_k)
        items = []
        for p in res:
            items.append({"id": str(p.id), "metadata": p.payload, "distance": getattr(p, "score", None)})
        return items

    def get(self, id: str):
        r = self.client.retrieve(self.collection_name, [id])
        if r and len(r) > 0:
            p = r[0]
            return {"id": str(p.id), "metadata": p.payload}
        return None

    def delete(self, id: str):
        self.client.delete(self.collection_name, [id])
        return {"id": id, "deleted": True}

    def info(self):
        return {"type": "qdrant", "collection": self.collection_name}

# ------------------------------
# Simple local fallback (JSON)
# ------------------------------
class SimpleVecDB(BaseVectorStore):
    def __init__(self, path: str = "./vecstore.json"):
        self.path = path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.store = json.load(f)
            except Exception:
                self.store = {}
        else:
            self.store = {}

    def _persist(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False, indent=2)

    def add(self, id: str, embedding: List[float], metadata: Dict):
        self.store[id] = {"embedding": embedding, "metadata": metadata, "added_at": time.time()}
        self._persist()
        return {"id": id}

    def query(self, embedding: List[float], top_k: int = 8, filter: Optional[Dict] = None):
        # naive cosine similarity
        from math import sqrt
        def dot(a,b): return sum(x*y for x,y in zip(a,b))
        def norm(v): return sqrt(sum(x*x for x in v))
        items = []
        for _id, v in self.store.items():
            emb = v.get("embedding")
            if not emb: continue
            try:
                score = dot(emb, embedding) / (norm(emb)*norm(embedding))
            except Exception:
                score = 0.0
            items.append({"id": _id, "score": float(score), "metadata": v["metadata"]})
        items = sorted(items, key=lambda x: x.get("score",0), reverse=True)[:top_k]
        return items

    def get(self, id: str):
        return self.store.get(id)

    def delete(self, id: str):
        if id in self.store: del self.store[id]; self._persist(); return {"id": id, "deleted": True}
        return {"id": id, "deleted": False}

    def info(self):
        return {"type": "simple", "count": len(self.store)}