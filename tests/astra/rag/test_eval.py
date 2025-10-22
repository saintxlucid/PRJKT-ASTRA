"""Test suite for RAG evaluation metrics."""
import pytest
from pathlib import Path
import tempfile
import json
from datetime import datetime

from astra.rag.eval import RAGEvaluator, EvalMetrics

@pytest.fixture
def sample_results():
    """Sample retrieval results for testing."""
    return [
        {
            "query": "test query 1",
            "docs": [
                {"id": "doc1", "source": "kb", "category": "tech", 
                 "content": "test document one"},
                {"id": "doc2", "source": "web", "category": "general",
                 "content": "test document two"}
            ],
            "context": "combined context for docs",
            "latency_ms": 150,
            "confidence": 0.85
        },
        {
            "query": "test query 2", 
            "docs": [
                {"id": "doc3", "source": "kb", "category": "tech",
                 "content": "test document three"}
            ],
            "context": "single doc context",
            "latency_ms": 100,
            "confidence": 0.95
        }
    ]

@pytest.fixture
def ground_truth():
    """Sample ground truth document IDs."""
    return ["doc1", "doc3"]

@pytest.fixture
def temp_baseline():
    """Create temporary baseline file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        baseline = {
            "hit_at_k": 0.8,
            "mrr_at_k": 0.7,
            "context_tokens": 10,
            "diversity": 0.8,
            "latency_p95": 0.2,
            "confidence_mean": 0.9,
            "timestamp": datetime.now().isoformat(),
            "category_coverage": {"tech": 0.8, "general": 0.7}
        }
        json.dump(baseline, f)
        return Path(f.name)

def test_compute_metrics(sample_results, ground_truth):
    """Test basic metrics computation."""
    evaluator = RAGEvaluator()
    metrics = evaluator.compute_metrics(sample_results, ground_truth)
    
    assert isinstance(metrics, EvalMetrics)
    assert metrics.hit_at_k == 1.0  # Both queries hit ground truth
    assert metrics.mrr_at_k == 1.0  # Both found in first position
    assert metrics.context_tokens == 3  # Average tokens per result
    assert abs(metrics.diversity - 0.67) < 0.01  # 2 unique / 3 total sources
    assert 0.1 <= metrics.latency_p95 <= 0.2  # Converted to seconds
    assert 0.85 <= metrics.confidence_mean <= 0.95
    
    # Category coverage
    assert metrics.category_coverage["tech"] == 1.0
    assert metrics.category_coverage["general"] == 1.0

def test_regression_detection(sample_results, temp_baseline):
    """Test regression detection against baseline."""
    evaluator = RAGEvaluator(baseline_path=temp_baseline)
    metrics = evaluator.compute_metrics(sample_results)
    
    # Should detect regression in some metrics
    regressions = evaluator.detect_regression(metrics)
    assert regressions is not None
    assert any(change < -0.05 for change in regressions.values())

def test_baseline_persistence(sample_results, tmp_path):
    """Test saving and loading baseline metrics."""
    baseline_path = tmp_path / "baseline.json"
    evaluator = RAGEvaluator()
    
    # Compute and save metrics
    metrics = evaluator.compute_metrics(sample_results)
    evaluator.save_baseline(metrics, baseline_path)
    
    # Load and verify
    assert baseline_path.exists()
    with open(baseline_path) as f:
        saved = json.load(f)
        assert "hit_at_k" in saved
        assert "timestamp" in saved
        assert saved["diversity"] == metrics.diversity

def test_no_ground_truth(sample_results):
    """Test metrics computation without ground truth."""
    evaluator = RAGEvaluator()
    metrics = evaluator.compute_metrics(sample_results)
    
    assert metrics.hit_at_k == -1  # Undefined without ground truth
    assert metrics.mrr_at_k == -1  # Undefined without ground truth
    assert metrics.context_tokens > 0  # Still computes other metrics
    assert 0 <= metrics.diversity <= 1
    
def test_empty_results():
    """Test handling of empty result set."""
    evaluator = RAGEvaluator()
    metrics = evaluator.compute_metrics([])
    
    assert metrics.hit_at_k == -1
    assert metrics.mrr_at_k == -1
    assert metrics.context_tokens == 0
    assert metrics.diversity == 0
    assert not metrics.category_coverage  # Empty dict