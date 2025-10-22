"""
Vector storage abstraction.
Supports JSON (local file) and Qdrant backends.
"""
import os
import json
import numpy as np
from typing import List, Dict, Any, Optional


class VectorStore:
    """Vector store with pluggable backends."""
    
    def __init__(self, backend: str = 'json', **kwargs):
        """Initialize with backend (json|qdrant|chroma)."""
        self.backend = backend
        self.kwargs = kwargs
        if backend == 'json':
            os.makedirs('./index', exist_ok=True)
    
    def upsert(self, collection: str, vectors: np.ndarray, payloads: List[Dict[str, Any]]):
        """Upsert vectors and metadata."""
        if self.backend == 'json':
            path = f'./index/{collection}.npz'
            meta = f'./index/{collection}.meta.json'
            
            if os.path.exists(path):
                old = np.load(path)['v']
                vectors = np.vstack([old, vectors])
                with open(meta, 'r', encoding='utf-8') as f:
                    pl = json.load(f)
                pl.extend(payloads)
            else:
                pl = payloads
            
            np.savez_compressed(path, v=vectors)
            with open(meta, 'w', encoding='utf-8') as f:
                json.dump(pl, f, ensure_ascii=False, indent=2)
            return
        
        # TODO: Implement Qdrant/Chroma bindings
        raise NotImplementedError(f"Backend {self.backend} not yet implemented")
    
    def search(self, collection: str, query_vec: np.ndarray, limit: int = 50, 
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        if self.backend == 'json':
            path = f'./index/{collection}.npz'
            meta = f'./index/{collection}.meta.json'
            
            if not os.path.exists(path):
                return []
            
            V = np.load(path)['v']
            with open(meta, 'r', encoding='utf-8') as f:
                P = json.load(f)
            
            # Cosine similarity
            q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
            Vn = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-8)
            sims = (Vn @ q).reshape(-1)
            
            idx = np.argsort(-sims)[:limit]
            out = []
            for i in idx:
                item = dict(P[i])
                item['score'] = float(sims[i])
                out.append(item)
            
            return out
        
        return []
