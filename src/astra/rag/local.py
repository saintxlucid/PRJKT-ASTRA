"""
FAISS-based local vector index implementation.
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import structlog
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from astra.rag.indexes import DenseIndex

logger = structlog.get_logger()

class LocalIndex(DenseIndex):
    """Local vector index using FAISS."""

    def __init__(
        self,
        index_path: str = "data/index/local.faiss",
        batch_size: int = 100,
        cache_dir: str = "data/cache/local_index",
        vector_size: int = 1024,
    ):
        """Initialize local index."""
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu package required for LocalIndex")

        # Create output directories
        index_dir = Path(index_path).parent
        index_dir.mkdir(parents=True, exist_ok=True)

        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = Path(index_path)
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self.vector_size = vector_size

        # Initialize or load FAISS index
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            logger.info("local_index_loaded", path=str(self.index_path))
        else:
            self.index = faiss.IndexFlatIP(vector_size)  # Inner product index
            logger.info("local_index_created", path=str(self.index_path))

    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search local index."""
        try:
            # Convert query to numpy array
            query = np.array(query_vector).reshape(1, -1).astype('float32')

            # Search index
            D, I = self.index.search(query, k)

            # Convert to standard format
            # For now, we'll just return IDs and scores since we don't store metadata
            results = [
                {
                    "id": str(idx),
                    "score": float(score),
                    "payload": {}
                }
                for idx, score in zip(I[0], D[0])
            ]

            return results

        except Exception as e:
            logger.error("local_search_failed", error=str(e))
            return []

    async def upsert(
        self,
        vectors: List[List[float]],
        collection: str,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Add vectors to local index."""
        try:
            vectors_np = np.array(vectors).astype('float32')
            self.index.add(vectors_np)

            # Save index after update
            faiss.write_index(self.index, str(self.index_path))
            logger.info("local_vectors_added", count=len(vectors))
            return True

        except Exception as e:
            logger.error("local_upsert_failed", error=str(e))
            return False

    async def delete(
        self,
        collection: str,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete vectors from local index."""
        try:
            if ids is None and filter_metadata is None:
                # Reset the entire index
                self.index = faiss.IndexFlatIP(self.vector_size)
                faiss.write_index(self.index, str(self.index_path))
                logger.info("local_index_reset")
                return True

            # For specific deletions, we need to do a full copy
            # FAISS doesn't support individual vector removal
            logger.warning("local_delete_not_supported")
            return False

        except Exception as e:
            logger.error("local_delete_failed", error=str(e))
            return False