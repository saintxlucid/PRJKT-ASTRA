"""
Tests for dense index interfaces
"""
import pytest
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from astra.rag.indexes import DenseIndex, QdrantIndex, QDRANT_AVAILABLE


class MockDenseIndex(DenseIndex):
    """Mock implementation for testing base interface."""
    
    def __init__(self):
        self.vectors: Dict[str, List[List[float]]] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
    
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        if collection not in self.vectors:
            return []
        
        # Simple dot product similarity
        results = []
        for i, vec in enumerate(self.vectors[collection]):
            score = sum(q * v for q, v in zip(query_vector, vec))
            meta = self.metadata[collection][i] if collection in self.metadata else {}
            results.append({
                "id": str(i),
                "score": score,
                "payload": meta
            })
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]
    
    async def upsert(
        self,
        vectors: List[List[float]],
        collection: str,
        ids: List[str] = None,
        metadata: List[Dict[str, Any]] = None
    ) -> bool:
        self.vectors[collection] = vectors
        if metadata:
            self.metadata[collection] = metadata
        return True
    
    async def delete(
        self,
        collection: str,
        ids: List[str] = None,
        filter_metadata: Dict[str, Any] = None
    ) -> bool:
        if collection in self.vectors:
            del self.vectors[collection]
            if collection in self.metadata:
                del self.metadata[collection]
        return True


@pytest.mark.asyncio
async def test_mock_dense_index():
    """Test the mock implementation."""
    index = MockDenseIndex()
    
    # Test upserting vectors
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    metadata = [{"type": "a"}, {"type": "b"}]
    assert await index.upsert(vectors, "test", metadata=metadata)
    
    # Test searching
    results = await index.search([1.0, 0.0], "test", k=1)
    assert len(results) == 1
    assert results[0]["score"] == 1.0  # Perfect match
    assert results[0]["payload"] == {"type": "a"}
    
    # Test deletion
    assert await index.delete("test")
    results = await index.search([1.0, 0.0], "test", k=1)
    assert len(results) == 0


@pytest.mark.skipif(not QDRANT_AVAILABLE, reason="qdrant-client not installed")
@pytest.mark.asyncio
async def test_qdrant_index():
    """Test the Qdrant implementation with mocked client."""
    with patch("astra.rag.indexes.QdrantClient") as mock_client:
        # Setup mock responses
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_client.return_value.get_collections.return_value = mock_collections
        
        # Initialize index
        index = QdrantIndex("http://localhost:6333", vector_size=2)
        
        # Test collection creation
        mock_client.return_value.create_collection.assert_not_called()
        await index._ensure_collection("test")
        mock_client.return_value.create_collection.assert_called_once()
        
        # Test upserting vectors
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        metadata = [{"type": "a"}, {"type": "b"}]
        assert await index.upsert(vectors, "test", metadata=metadata)
        mock_client.return_value.upsert.assert_called_once()
        
        # Test searching
        mock_search_result = [
            MagicMock(id="0", score=0.9, payload={"type": "a"})
        ]
        mock_client.return_value.search.return_value = mock_search_result
        
        results = await index.search([1.0, 0.0], "test", k=1)
        assert len(results) == 1
        assert results[0]["score"] == 0.9
        assert results[0]["payload"] == {"type": "a"}
        
        # Test deletion
        assert await index.delete("test")
        mock_client.return_value.delete_collection.assert_called_once_with(collection_name="test")