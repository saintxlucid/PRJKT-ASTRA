"""Unit tests for cross-encoder reranker."""
import pytest
import torch
import numpy as np
from pathlib import Path

from astra.rag.rerank.cross_encoder import CrossEncoder, RerankerConfig

@pytest.fixture
def reranker():
    """Initialize reranker for tests."""
    config = RerankerConfig(
        model_name="BAAI/bge-reranker-base",
        max_length=512,
        batch_size=4,
        use_fp16=False,  # Use FP32 for testing
        cache_dir="tests/data/cache/reranker"
    )
    return CrossEncoder(config)

def test_basic_reranking(reranker):
    """Test basic reranking functionality."""
    query = "What is machine learning?"
    results = [
        {"text": "Machine learning is a subset of artificial intelligence.", "metadata": {}},
        {"text": "Data science uses statistical methods.", "metadata": {}},
        {"text": "Deep learning uses neural networks.", "metadata": {}}
    ]
    
    reranked = reranker.rerank(query, results)
    assert len(reranked) == len(results)
    assert isinstance(reranked[0], dict)

def test_diversity_bonus(reranker):
    """Test section/heading diversity bonus."""
    query = "What is Python?"
    results = [
        {
            "text": "Python basics", 
            "metadata": {"section_id": "intro", "heading": "Introduction"}
        },
        {
            "text": "More Python basics", 
            "metadata": {"section_id": "intro", "heading": "Introduction"}
        },
        {
            "text": "Advanced Python", 
            "metadata": {"section_id": "advanced", "heading": "Advanced Topics"}
        }
    ]
    
    reranked = reranker.rerank(query, results, return_scores=True)
    # Check diversity bonus applied
    first_score = reranked[0]["rerank_score"]
    last_score = reranked[-1]["rerank_score"]
    assert abs(first_score - last_score) < 0.5  # Scores should be closer due to diversity

def test_explanation_generation(reranker):
    """Test explanation generation."""
    query = "What is deep learning?"
    result = {
        "text": "Deep learning is a subset of machine learning that uses multiple layers of neural networks to learn hierarchical representations of data."
    }
    
    explanation = reranker.get_explanation(query, result)
    assert "matched_spans" in explanation
    assert len(explanation["matched_spans"]) > 0
    
def test_batch_scoring(reranker):
    """Test batched inference."""
    query = "What is artificial intelligence?"
    # Create 10 results
    results = [
        {"text": f"Result {i}", "metadata": {}} for i in range(10)
    ]
    
    # Rerank with small batch size
    reranked = reranker.rerank(query, results)
    assert len(reranked) == len(results)

def test_error_handling(reranker):
    """Test error handling."""
    query = "Test query"
    results = [{"invalid": "no text field"}]  # Invalid result
    
    # Should handle gracefully and return original results
    reranked = reranker.rerank(query, results)
    assert reranked == results

@pytest.mark.parametrize("test_case", [
    # Short but relevant
    ("Python tutorial", "This is a quick Python guide", 0.8),
    # Long but less relevant
    ("Python tutorial", "This document discusses various programming languages like Java, C++, and contains a brief mention of Python", 0.4),
    # Perfect match
    ("Python tutorial", "Comprehensive Python programming tutorial and guide", 0.9)
])
def test_length_impact(reranker, test_case):
    """Test length-aware reranking."""
    query, text, min_score = test_case
    result = reranker.rerank(query, [{"text": text}], return_scores=True)[0]
    assert result["rerank_score"] >= min_score

def test_answer_span_weighting():
    """Test answer span detection and weighting."""
    config = RerankerConfig(
        model_name="BAAI/bge-reranker-base",
        max_length=512
    )
    reranker = CrossEncoder(config)
    
    query = "What is the capital of France?"
    results = [
        {"text": "Paris is the capital city of France."},  # Direct answer
        {"text": "France is a country in Europe with many cities."},  # No answer
    ]
    
    reranked = reranker.rerank(query, results, return_scores=True)
    assert reranked[0]["text"].startswith("Paris")  # Direct answer should rank higher

def test_performance_benchmarking(reranker):
    """Test reranker performance."""
    query = "What is machine learning?"
    results = [{"text": f"Result {i}"} for i in range(100)]
    
    import time
    start = time.time()
    reranked = reranker.rerank(query, results)
    duration = time.time() - start
    
    # Performance assertions
    assert len(reranked) == len(results)
    assert duration < 5.0  # Should complete within 5 seconds

def test_hybrid_score_fusion(reranker):
    """Test hybrid score fusion."""
    query = "What is deep learning?"
    results = [
        {
            "text": "Deep learning uses neural networks",
            "bm25_score": 0.9,
            "vector_score": 0.8
        },
        {
            "text": "Machine learning basics",
            "bm25_score": 0.7,
            "vector_score": 0.6
        }
    ]
    
    reranked = reranker.rerank(query, results, return_scores=True)
    # Check scores are fused
    assert all("rerank_score" in r for r in reranked)
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_historical_query_boosting(reranker):
    """Test historical query boosting."""
    # Simulate historical queries
    history = [
        "What is deep learning?",
        "How do neural networks work?"
    ]
    current_query = "Explain backpropagation"
    
    results = [
        {"text": "Backpropagation is how neural networks learn"},
        {"text": "Backpropagation explained without neural networks"}
    ]
    
    # Add history to metadata
    for r in results:
        r["metadata"] = {"query_history": history}
    
    reranked = reranker.rerank(current_query, results)
    assert "neural networks" in reranked[0]["text"]  # Relevant to history

def test_query_doc_interaction(reranker):
    """Test query-document interaction analysis."""
    query = "What causes climate change?"
    results = [
        {
            "text": "Climate change is primarily caused by greenhouse gas emissions.",
            "metadata": {"type": "definition"}
        },
        {
            "text": "The weather was unusually warm today.",
            "metadata": {"type": "observation"}
        }
    ]
    
    explanation = reranker.get_explanation(query, results[0])
    assert len(explanation["matched_spans"]) > 0
    assert explanation["overall_score"] > 0.5

def test_config_validation():
    """Test configuration validation."""
    # Invalid model name
    with pytest.raises(Exception):
        config = RerankerConfig(model_name="invalid/model")
        CrossEncoder(config)
    
    # Invalid batch size
    with pytest.raises(ValueError):
        config = RerankerConfig(batch_size=0)
        CrossEncoder(config)
        
    # Invalid max length
    with pytest.raises(ValueError):
        config = RerankerConfig(max_length=0)
        CrossEncoder(config)