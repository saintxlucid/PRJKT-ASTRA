"""Tests for benchmarking utilities."""
import json
import time
from pathlib import Path
from typing import List
import pytest
from unittest.mock import Mock, patch

from astra.bench.core import (
    Benchmarker,
    BenchmarkConfig,
    QueryResult,
    BenchmarkResult
)
from astra.rag.documents import Document

@pytest.fixture
def mock_pipeline():
    """Create mock RAG pipeline."""
    pipeline = Mock()
    
    # Simulate retrieval with timing
    def mock_retrieve(query: str, k: int) -> List[Document]:
        time.sleep(0.1)  # Simulate work
        return [
            Document(
                id=f"doc{i}",
                text=f"Result {i} for {query}"
            )
            for i in range(k)
        ]
    
    pipeline.retrieve = mock_retrieve
    pipeline.cache = {}
    return pipeline

@pytest.fixture
def mock_event_logger():
    """Create mock event logger."""
    return Mock()

@pytest.fixture
def benchmarker(mock_pipeline, mock_event_logger):
    """Create benchmarker instance."""
    config = BenchmarkConfig(
        k_bm25=10,
        k_dense=5,
        target_p95_ms=200.0
    )
    return Benchmarker(
        pipeline=mock_pipeline,
        event_logger=mock_event_logger,
        config=config
    )

def test_benchmark_config():
    """Test benchmark configuration."""
    config = BenchmarkConfig(
        k_bm25=15,
        k_dense=8,
        fusion_method="rrf",
        rrf_k=50.0
    )
    assert config.k_bm25 == 15
    assert config.k_dense == 8
    assert config.fusion_method == "rrf"
    assert config.rrf_k == 50.0

def test_single_query(benchmarker):
    """Test running a single query."""
    result = benchmarker._run_query("test query")
    
    assert isinstance(result, QueryResult)
    assert result.query == "test query"
    assert result.duration_ms > 0
    assert result.num_results == benchmarker.config.k_dense
    assert len(result.top_k_ids) == result.num_results

def test_complete_benchmark(benchmarker):
    """Test complete benchmark run."""
    # Use small query set
    queries = [
        "query 1",
        "query 2",
        "query 3"
    ]
    
    results = benchmarker.run_benchmark(
        queries=queries,
        runs=2
    )
    
    assert isinstance(results, BenchmarkResult)
    assert len(results.queries) == len(queries) * 2
    assert results.p50_ms > 0
    assert results.p95_ms >= results.p50_ms
    assert 0 <= results.cache_hit_rate <= 1.0
    assert 0 <= results.mean_overlap <= 1.0

def test_overlap_calculation(benchmarker):
    """Test result overlap calculation."""
    results = [
        QueryResult("q1", 100, 2, False, ["doc1", "doc2"]),
        QueryResult("q1", 120, 2, True, ["doc1", "doc3"]),
        QueryResult("q2", 110, 2, False, ["doc4", "doc5"])
    ]
    
    overlap = benchmarker._calculate_overlap(results)
    assert 0 <= overlap <= 1.0

def test_parameter_tuning(benchmarker):
    """Test parameter tuning logic."""
    # Create results that need tuning
    results = BenchmarkResult(
        config=benchmarker.config,
        queries=[],
        p95_ms=400.0,  # Above target
        p50_ms=200.0,
        cache_hit_rate=0.4,  # Below target
        mean_overlap=0.3  # Low overlap
    )
    
    new_config = benchmarker.tune_parameters(results)
    
    # Verify tuning adjustments
    assert new_config.k_dense < benchmarker.config.k_dense
    assert new_config.cache_ttl > benchmarker.config.cache_ttl
    assert new_config.rrf_k > benchmarker.config.rrf_k

def test_save_results(benchmarker, tmp_path):
    """Test saving results to file."""
    results = BenchmarkResult(
        config=benchmarker.config,
        queries=[
            QueryResult("test", 100.0, 5, False, ["doc1", "doc2"])
        ],
        p50_ms=100.0,
        p95_ms=150.0,
        cache_hit_rate=0.5,
        mean_overlap=0.6
    )
    
    output_path = tmp_path / "results.json"
    benchmarker.save_results(results, str(output_path))
    
    # Verify file contents
    assert output_path.exists()
    with open(output_path) as f:
        data = json.load(f)
        assert "config" in data
        assert "summary" in data
        assert "queries" in data
        assert len(data["queries"]) == 1

def test_cache_detection(benchmarker):
    """Test cache hit detection."""
    # First query - no cache
    result1 = benchmarker._run_query("test")
    assert not result1.cache_hit
    
    # Same query - should hit cache
    result2 = benchmarker._run_query("test")
    assert result2.cache_hit