"""Unit tests for RAG calibrator."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from astra.rag.tuning.calibrator import RagCalibrator, CalibrationResult
from astra.rag.multi_rag import MultiRagFusion

@pytest.fixture
def mock_golden_set(tmp_path):
    """Create a mock golden set file."""
    golden_set = [
        {
            "query": "What is RAG?",
            "relevant_docs": ["doc1", "doc2", "doc3"]
        },
        {
            "query": "How does vector search work?",
            "relevant_docs": ["doc4", "doc5"]
        }
    ]
    
    path = tmp_path / "golden_set.json"
    with open(path, "w") as f:
        json.dump(golden_set, f)
    return path

@pytest.fixture
def mock_config_dir(tmp_path):
    """Create a mock config directory."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    
    # Create a mock existing config
    config = {
        "version": 1,
        "timestamp": datetime.now().isoformat(),
        "weights": {"semantic": 0.7, "keyword": 0.3},
        "metrics": {"ndcg": 0.85, "mrr": 0.75}
    }
    
    with open(config_dir / "rag_config_v1.json", "w") as f:
        json.dump(config, f)
        
    return config_dir

@pytest.fixture
def mock_rag_fusion():
    """Create a mock MultiRagFusion."""
    class MockMultiRagFusion:
        def __init__(self):
            self.weights = {"semantic": 0.7, "keyword": 0.3}
            
        def get_weights(self):
            return self.weights
            
        def set_weights(self, weights):
            self.weights = weights
            
        async def retrieve(self, query, limit=10):
            class MockResult:
                def __init__(self, doc_id):
                    self.doc_id = doc_id
                    
            # Return mock results based on query
            if query == "What is RAG?":
                return [MockResult(f"doc{i}") for i in range(1, 4)]
            else:
                return [MockResult(f"doc{i}") for i in range(4, 6)]
                
    return MockMultiRagFusion()

@pytest.mark.asyncio
async def test_calibration(mock_golden_set, mock_config_dir, mock_rag_fusion):
    """Test basic calibration workflow."""
    calibrator = RagCalibrator(
        rag_fusion=mock_rag_fusion,
        golden_set_path=mock_golden_set,
        config_dir=mock_config_dir,
        max_versions=3
    )
    
    # Run calibration
    result = await calibrator.calibrate()
    
    assert isinstance(result, CalibrationResult)
    assert result.version == 2  # Since we had version 1 in mock
    assert all(0.1 <= w <= 1.0 for w in result.weights.values())
    assert 0 <= result.ndcg <= 1
    assert 0 <= result.mrr <= 1
    
    # Check config file was created
    config_path = mock_config_dir / f"rag_config_v{result.version}.json"
    assert config_path.exists()
    
@pytest.mark.asyncio
async def test_rollback(mock_golden_set, mock_config_dir, mock_rag_fusion):
    """Test configuration rollback."""
    calibrator = RagCalibrator(
        rag_fusion=mock_rag_fusion,
        golden_set_path=mock_golden_set,
        config_dir=mock_config_dir
    )
    
    # Should roll back to version 1
    success = await calibrator.rollback()
    assert success
    
    # Check weights were restored
    current_weights = mock_rag_fusion.get_weights()
    assert current_weights == {"semantic": 0.7, "keyword": 0.3}

@pytest.mark.asyncio
async def test_ab_testing(mock_golden_set, mock_config_dir, mock_rag_fusion):
    """Test A/B testing functionality."""
    calibrator = RagCalibrator(
        rag_fusion=mock_rag_fusion,
        golden_set_path=mock_golden_set,
        config_dir=mock_config_dir
    )
    
    test_weights = {"semantic": 0.6, "keyword": 0.4}
    control_metrics, test_metrics = await calibrator.start_ab_test(
        test_weights,
        duration_hours=24
    )
    
    assert isinstance(control_metrics, dict)
    assert isinstance(test_metrics, dict)
    assert "ndcg" in control_metrics
    assert "mrr" in control_metrics
    assert "ndcg" in test_metrics
    assert "mrr" in test_metrics

@pytest.mark.asyncio
async def test_version_cleanup(mock_golden_set, mock_config_dir, mock_rag_fusion):
    """Test old version cleanup."""
    calibrator = RagCalibrator(
        rag_fusion=mock_rag_fusion,
        golden_set_path=mock_golden_set,
        config_dir=mock_config_dir,
        max_versions=2
    )
    
    # Create multiple versions
    for _ in range(3):
        await calibrator.calibrate()
        
    # Should only have 2 latest versions
    configs = list(mock_config_dir.glob("rag_config_v*.json"))
    assert len(configs) == 2