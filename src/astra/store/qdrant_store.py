"""
Qdrant vector store integration for ASTRA
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, SearchRequest
from qdrant_client.http.exceptions import UnexpectedResponse

from ..core.resilience import circuit_breaker, retry_with_backoff
from ..core.types import Document, SearchResult
from ..telemetry.metrics import STORE_OPS_COUNTER, STORE_LATENCY

logger = logging.getLogger(__name__)

@dataclass
class QdrantConfig:
    host: str
    port: int
    collection: str
    distance: str = "Cosine"
    dim: int = 1024

class QdrantStore:
    """Qdrant vector store implementation"""
    
    def __init__(self, config: QdrantConfig):
        self.config = config
        self.client = QdrantClient(host=config.host, port=config.port)
        self._ensure_collection()
        
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            if not any(c.name == self.config.collection for c in collections.collections):
                self.client.create_collection(
                    collection_name=self.config.collection,
                    vectors_config=VectorParams(
                        size=self.config.dim,
                        distance=Distance[self.config.distance]
                    )
                )
                logger.info(f"Created collection {self.config.collection}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    @circuit_breaker(failure_threshold=5, reset_timeout=30)
    @retry_with_backoff(max_retries=3)
    def upsert(self, documents: List[Document]) -> None:
        """Upsert documents into vector store"""
        with STORE_LATENCY.time():
            try:
                points = []
                for doc in documents:
                    point = PointStruct(
                        id=doc.id,
                        vector=doc.embedding,
                        payload={
                            "text": doc.text,
                            "metadata": doc.metadata
                        }
                    )
                    points.append(point)
                
                self.client.upsert(
                    collection_name=self.config.collection,
                    points=points
                )
                STORE_OPS_COUNTER.labels(operation="upsert").inc(len(documents))
                logger.info(f"Upserted {len(documents)} documents")
            except Exception as e:
                logger.error(f"Failed to upsert documents: {e}")
                raise

    @circuit_breaker(failure_threshold=5, reset_timeout=30)
    @retry_with_backoff(max_retries=3)
    def search(self, query_vector: List[float], k: int = 5) -> List[SearchResult]:
        """Search for similar vectors"""
        with STORE_LATENCY.time():
            try:
                results = self.client.search(
                    collection_name=self.config.collection,
                    query_vector=query_vector,
                    limit=k,
                    search_params={"exact": False}  # Use HNSW index
                )
                
                search_results = []
                for res in results:
                    result = SearchResult(
                        id=str(res.id),
                        text=res.payload["text"],
                        metadata=res.payload["metadata"],
                        score=float(res.score)
                    )
                    search_results.append(result)
                
                STORE_OPS_COUNTER.labels(operation="search").inc()
                return search_results
            except Exception as e:
                logger.error(f"Search failed: {e}")
                raise

    def delete(self, doc_ids: List[str]) -> None:
        """Delete documents by ID"""
        with STORE_LATENCY.time():
            try:
                self.client.delete(
                    collection_name=self.config.collection,
                    points_selector={"ids": doc_ids}
                )
                STORE_OPS_COUNTER.labels(operation="delete").inc(len(doc_ids))
                logger.info(f"Deleted {len(doc_ids)} documents")
            except Exception as e:
                logger.error(f"Failed to delete documents: {e}")
                raise

    def health_check(self) -> bool:
        """Check if Qdrant is available"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception:
            return False