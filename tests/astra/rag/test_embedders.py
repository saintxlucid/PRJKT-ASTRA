"""
Tests for embedder implementations.
"""

import pytest
import numpy as np
from typing import List

from astra.rag.embedders import (
    l2_normalize,
    EmbedderConfig,
    BaseEmbedder,
    BGEM3Embedder
)


def test_l2_normalization():
    """Test L2 normalization utility."""
    # Test with random vectors
    vectors = np.random.randn(10, 5)  # 10 vectors of dimension 5
    normalized = l2_normalize(vectors)
    
    # Check norms are ~1.0
    norms = np.linalg.norm(normalized, axis=1)
    assert np.allclose(norms, 1.0)
    
    # Test with zero vector
    vectors = np.array([[0.0, 0.0, 0.0]])
    normalized = l2_normalize(vectors)
    assert not np.any(np.isnan(normalized))


class MockEmbedder(BaseEmbedder):
    """Mock embedder for testing."""
    
    def __init__(self, config: EmbedderConfig):
        super().__init__(config)
        self.query_calls: List[str] = []
        self.doc_calls: List[List[str]] = []
    
    async def embed_query(self, query: str) -> List[float]:
        self.query_calls.append(query)
        # Return deterministic vector based on query length
        return [float(i) / len(query) for i in range(self.config.dimension)]
    
    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        self.doc_calls.append(documents)
        # Return deterministic vectors based on document lengths
        return [
            [float(i) / len(doc) for i in range(self.config.dimension)]
            for doc in documents
        ]


@pytest.fixture
def mock_embedder():
    """Create mock embedder."""
    config = EmbedderConfig(
        model_name="mock",
        dimension=4,
        normalize=True
    )
    return MockEmbedder(config)


@pytest.mark.asyncio
async def test_base_embedder_interface(mock_embedder):
    """Test base embedder interface."""
    # Test query embedding
    query = "test query"
    vector = await mock_embedder.embed_query(query)
    assert len(vector) == mock_embedder.config.dimension
    assert query in mock_embedder.query_calls
    
    # Test document embedding
    docs = ["doc1", "doc2"]
    vectors = await mock_embedder.embed_documents(docs)
    assert len(vectors) == len(docs)
    assert all(len(v) == mock_embedder.config.dimension for v in vectors)
    assert docs in mock_embedder.doc_calls


@pytest.mark.asyncio
async def test_embedder_actions(mock_embedder):
    """Test embedder action registration."""
    # Test query embedding action
    query = "test query"
    vector = await mock_embedder.registry.execute(
        "embedder.embed_query",
        query
    )
    assert len(vector) == mock_embedder.config.dimension
    
    # Test document embedding action
    docs = ["doc1", "doc2"]
    vectors = await mock_embedder.registry.execute(
        "embedder.embed_documents",
        docs
    )
    assert len(vectors) == len(docs)
    assert all(len(v) == mock_embedder.config.dimension for v in vectors)


@pytest.mark.asyncio
@pytest.mark.skipif(
    True,  # Skip by default - requires FlagEmbedding package
    reason="Requires FlagEmbedding package and BGE-M3 model"
)
async def test_bge_m3_embedder():
    """Test BGE-M3 embedder implementation."""
    config = EmbedderConfig(
        model_name="BAAI/bge-m3",
        dimension=1024,
        normalize=True,
        use_fp16=True,
        device="cpu",
        batch_size=2
    )
    
    embedder = BGEM3Embedder(config)
    
    # Test query embedding
    query = "What is machine learning?"
    vector = await embedder.embed_query(query)
    assert len(vector) == config.dimension
    assert isinstance(vector, list)
    assert all(isinstance(x, float) for x in vector)
    
    # Test document embedding
    docs = [
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks are inspired by biological brains."
    ]
    vectors = await embedder.embed_documents(docs)
    assert len(vectors) == len(docs)
    assert all(len(v) == config.dimension for v in vectors)
    assert all(isinstance(v, list) for v in vectors)
    assert all(isinstance(x, float) for v in vectors for x in v)