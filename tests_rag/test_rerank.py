"""
Tests for RAG Fusion v2 reranking.
"""

from datetime import datetime, timedelta
import numpy as np
import pytest
from astra.rag.rerank import ResultReranker, RankedResult

@pytest.fixture
def reranker():
    """Create reranker instance for tests"""
    return ResultReranker(
        mmr_lambda=0.7,
        recency_boost=0.3,
        max_age_days=365
    )

@pytest.fixture
def sample_results():
    """Create sample ranked results"""
    now = datetime.now()
    return [
        RankedResult(
            content="First result about AI",
            score=0.9,
            timestamp=now - timedelta(days=10),
            citation={"id": 1},
            embedding=np.array([1.0, 0.0, 0.0])
        ),
        RankedResult(
            content="Second result about AI",
            score=0.8,
            timestamp=now - timedelta(days=100),
            citation={"id": 2},
            embedding=np.array([0.9, 0.1, 0.0])  # Similar to first
        ),
        RankedResult(
            content="Result about databases",
            score=0.7,
            timestamp=now - timedelta(days=50),
            citation={"id": 3},
            embedding=np.array([0.0, 0.0, 1.0])  # Different topic
        ),
    ]

@pytest.mark.asyncio
async def test_mmr_reranking(reranker, sample_results):
    """Test MMR promotes diversity"""
    reranked = await reranker.rerank("test query", sample_results, top_k=3)
    
    # Should prefer diverse results over similar high scores
    assert reranked[0].citation["id"] == 1  # Highest score
    assert reranked[1].citation["id"] == 3  # Different topic
    assert reranked[2].citation["id"] == 2  # Similar to first

@pytest.mark.asyncio
async def test_recency_blending(reranker, sample_results):
    """Test recency affects final ranking"""
    reranked = await reranker.rerank("test query", sample_results, top_k=3)
    
    # Recent results should get a boost
    assert reranked[0].citation["id"] == 1  # Most recent
    
    # Older results should be penalized
    old_result = [r for r in reranked if r.citation["id"] == 2][0]
    assert old_result.score < 0.8  # Original score decreased

@pytest.mark.asyncio
async def test_empty_results(reranker):
    """Test handling empty result set"""
    reranked = await reranker.rerank("test query", [], top_k=3)
    assert len(reranked) == 0