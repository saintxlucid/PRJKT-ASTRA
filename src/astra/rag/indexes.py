"""
ASTRA Dense Index Interfaces
Provides vector-based search capabilities through pluggable backends.
"""
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np
import structlog

logger = structlog.get_logger()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
    from qdrant_client.http.models import Filter as QdrantFilter
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed - QdrantIndex disabled")

# Import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not installed - LocalIndex will be limited")

class DenseIndex(ABC):
    """Base class for vector similarity search indexes."""

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DenseIndex':
        """Create index instance from config dict."""
        index_type = config.get('dense_index', {}).get('type', 'local')
        index_config = config.get('dense_index', {}).get('config', {})
        
        if index_type == 'qdrant':
            if QDRANT_AVAILABLE:
                return QdrantIndex(**index_config)
            else:
                logger.warning("qdrant_unavailable_using_local")
                return LocalIndex(**index_config)
        else:
            return LocalIndex(**index_config)

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the index.

        Args:
            query_vector: Query embedding vector
            collection: Name of collection/index to search
            k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of results with payload and score
        """
        pass

    @abstractmethod
    async def upsert(
        self,
        vectors: List[List[float]],
        collection: str,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add or update vectors in the index.

        Args:
            vectors: List of embedding vectors to insert/update
            collection: Name of collection/index to modify
            ids: Optional list of IDs for the vectors (must match length)
            metadata: Optional metadata for each vector (must match length)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Delete vectors from the index.

        Args:
            collection: Name of collection/index to modify
            ids: Optional list of specific IDs to delete
            filter_metadata: Optional metadata filters for deletion

        Returns:
            True if successful
        """
        pass

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


class DenseIndex(ABC):
    """Base class for vector similarity search indexes."""

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'DenseIndex':
        """Create index instance from config dict."""
        index_type = config.get('dense_index', {}).get('type', 'local')
        index_config = config.get('dense_index', {}).get('config', {})
        
        if index_type == 'qdrant':
            if QDRANT_AVAILABLE:
                return QdrantIndex(**index_config)
            else:
                logger.warning("qdrant_unavailable_using_local")
                return LocalIndex(**index_config)
        else:
            return LocalIndex(**index_config)

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the index.

        Args:
            query_vector: Query embedding vector
            collection: Name of collection/index to search
            k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of results with payload and score
        """
        pass

    @abstractmethod
    async def upsert(
        self,
        vectors: List[List[float]],
        collection: str,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add or update vectors in the index.

        Args:
            vectors: List of embedding vectors to insert/update
            collection: Name of collection/index to modify
            ids: Optional list of IDs for the vectors (must match length)
            metadata: Optional metadata for each vector (must match length)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Delete vectors from the index.

        Args:
            collection: Name of collection/index to modify
            ids: Optional list of specific IDs to delete
            filter_metadata: Optional metadata filters for deletion

        Returns:
            True if successful
        """
        pass


class QdrantIndex(DenseIndex):
    """Qdrant vector database implementation of DenseIndex."""

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        vector_size: int = 384,  # Default for MiniLM
        distance: str = "Cosine"
    ):
        """
        Initialize Qdrant client and config.

        Args:
            url: Qdrant server URL
            api_key: Optional API key for authentication
            vector_size: Dimension of vectors (must match embedder)
            distance: Distance metric (Cosine, Dot, Euclidean)
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client package required for QdrantIndex")

        self.client = QdrantClient(url=url, api_key=api_key)
        self.vector_size = vector_size
        self.distance = getattr(Distance, distance.upper())
        logger.info("qdrant_index_initialized", url=url, vector_size=vector_size)

    async def _ensure_collection(self, name: str) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections()
            names = [c.name for c in collections.collections]
            if name not in names:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance
                    )
                )
                logger.info("qdrant_collection_created", name=name)
        except Exception as e:
            logger.error("qdrant_collection_setup_failed", error=str(e))
            raise

    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Qdrant."""
        try:
            await self._ensure_collection(collection)

            # Convert metadata filter to Qdrant format
            query_filter = None
            if filter_metadata:
                query_filter = QdrantFilter(**filter_metadata)

            results = self.client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=k,
                query_filter=query_filter
            )

            # Convert to standard format
            return [
                {
                    "id": str(r.id),
                    "score": float(r.score),
                    "payload": r.payload or {}
                }
                for r in results
            ]

        except Exception as e:
            logger.error("qdrant_search_failed", collection=collection, error=str(e))
            return []

    async def upsert(
        self,
        vectors: List[List[float]],
        collection: str,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Add or update vectors in Qdrant."""
        try:
            await self._ensure_collection(collection)

            # Generate sequential IDs if not provided
            if ids is None:
                ids = [str(i) for i in range(len(vectors))]

            # Convert to Qdrant points
            points = []
            for i, vec in enumerate(vectors):
                point = PointStruct(
                    id=ids[i],
                    vector=vec,
                    payload=metadata[i] if metadata else None
                )
                points.append(point)

            # Batch upsert
            self.client.upsert(
                collection_name=collection,
                points=points
            )
            logger.info("qdrant_upserted", collection=collection, count=len(vectors))
            return True

        except Exception as e:
            logger.error("qdrant_upsert_failed", collection=collection, error=str(e))
            return False

    async def delete(
        self,
        collection: str,
        ids: Optional[List[str]] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Delete vectors from Qdrant."""
        try:
            # Convert metadata filter to Qdrant format
            points_selector = None
            if filter_metadata:
                points_selector = QdrantFilter(**filter_metadata)

            if ids:
                self.client.delete(
                    collection_name=collection,
                    points_selector=ids
                )
            elif points_selector:
                self.client.delete(
                    collection_name=collection,
                    points_filter=points_selector
                )
            else:
                # Delete entire collection
                self.client.delete_collection(collection_name=collection)

            logger.info("qdrant_deleted", collection=collection)
            return True

        except Exception as e:
            logger.error("qdrant_delete_failed", collection=collection, error=str(e))
            return False