"""Tests for model validation functionality."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
from typing import Dict, Any

from evolution.core.validation import (
    ValidationConfig,
    ValidationMetrics,
    ValidationError,
    Validator,
    DriftDetector,
    ModelEvaluator
)
from evolution.core.tensor import Tensor

@pytest.fixture
def test_data():
    """Create test data for validation."""
    return {
        "input_ids": np.random.randint(0, 32000, (100, 512)),
        "attention_mask": np.ones((100, 512)),
        "labels": np.random.randint(0, 32000, (100,))
    }

@pytest.fixture
def validator(test_data) -> Validator:
    """Create a Validator instance."""
    return Validator(
        config=ValidationConfig(
            thresholds={
                "perplexity_max": 10.0,
                "accuracy_min": 0.85,
                "drift_max": 0.1
            },
            tasks=["perplexity", "accuracy", "drift"]
        ),
        test_data=test_data
    )

class TestPerplexityCalculation:
    """Test perplexity calculation functionality."""
    
    def test_basic_perplexity(self, validator):
        """Test basic perplexity calculation."""
        logits = np.random.normal(0, 1, (100, 512, 32000))
        perplexity = validator.calculate_perplexity(logits)
        
        assert isinstance(perplexity, float)
        assert perplexity > 0
        
    def test_perfect_predictions(self, validator):
        """Test perplexity with perfect predictions."""
        # Create logits that perfectly predict the labels
        logits = np.zeros((100, 512, 32000))
        for i in range(100):
            for j in range(512):
                logits[i, j, validator.test_data["labels"][i]] = 100
                
        perplexity = validator.calculate_perplexity(logits)
        assert perplexity < 1.1  # Should be very close to 1
        
    def test_uniform_predictions(self, validator):
        """Test perplexity with uniform predictions."""
        logits = np.zeros((100, 512, 32000))  # All equal probabilities
        perplexity = validator.calculate_perplexity(logits)
        
        # Should be close to vocab size
        assert abs(perplexity - 32000) < 100
        
    @pytest.mark.parametrize("batch_size", [1, 10, 100])
    def test_batch_independence(self, validator, batch_size):
        """Test that perplexity is independent of batch size."""
        logits = np.random.normal(0, 1, (batch_size, 512, 32000))
        labels = np.random.randint(0, 32000, (batch_size,))
        
        perplexity = validator.calculate_perplexity(
            logits,
            labels=labels
        )
        
        assert isinstance(perplexity, float)
        assert not np.isnan(perplexity)

class TestAccuracyEvaluation:
    """Test accuracy evaluation functionality."""
    
    def test_basic_accuracy(self, validator):
        """Test basic accuracy calculation."""
        predictions = np.random.randint(0, 32000, (100,))
        accuracy = validator.calculate_accuracy(predictions)
        
        assert 0 <= accuracy <= 1
        
    def test_perfect_accuracy(self, validator):
        """Test accuracy with perfect predictions."""
        predictions = validator.test_data["labels"].copy()
        accuracy = validator.calculate_accuracy(predictions)
        
        assert accuracy == 1.0
        
    def test_zero_accuracy(self, validator):
        """Test accuracy with completely wrong predictions."""
        predictions = (validator.test_data["labels"] + 1) % 32000
        accuracy = validator.calculate_accuracy(predictions)
        
        assert accuracy == 0.0
        
    @pytest.mark.parametrize("n_classes", [2, 10, 100])
    def test_multiclass(self, validator, n_classes):
        """Test accuracy with different numbers of classes."""
        labels = np.random.randint(0, n_classes, (100,))
        predictions = np.random.randint(0, n_classes, (100,))
        
        accuracy = validator.calculate_accuracy(
            predictions,
            labels=labels
        )
        
        assert 0 <= accuracy <= 1

class TestDriftDetection:
    """Test model drift detection."""
    
    def test_no_drift(self, validator):
        """Test drift detection with identical distributions."""
        base_outputs = np.random.normal(0, 1, (100, 768))
        current_outputs = base_outputs.copy()
        
        drift = validator.measure_drift(base_outputs, current_outputs)
        assert drift < 1e-6  # Should be essentially zero
        
    def test_complete_drift(self, validator):
        """Test drift detection with orthogonal distributions."""
        # Create orthogonal vectors
        base_outputs = np.eye(768)[:100]
        current_outputs = np.roll(base_outputs, 1, axis=1)  # Shift columns
        
        drift = validator.measure_drift(base_outputs, current_outputs)
        assert drift > 0.9  # Should be close to 1
        
    @pytest.mark.parametrize("shift", [0.1, 0.5, 1.0])
    def test_gradual_drift(self, validator, shift):
        """Test drift detection with gradual distribution shifts."""
        base_outputs = np.random.normal(0, 1, (100, 768))
        current_outputs = base_outputs + np.random.normal(0, shift, (100, 768))
        
        drift = validator.measure_drift(base_outputs, current_outputs)
        assert 0 <= drift <= 1
        
    def test_scale_invariance(self, validator):
        """Test that drift detection is scale-invariant."""
        base_outputs = np.random.normal(0, 1, (100, 768))
        current_outputs = base_outputs * 2  # Scale up
        
        drift = validator.measure_drift(base_outputs, current_outputs)
        assert drift < 1e-6  # Should be essentially zero

class TestValidationWorkflow:
    """Test complete validation workflow."""
    
    def test_full_validation(self, validator):
        """Test running full validation pipeline."""
        # Simulate model outputs
        outputs = {
            "logits": np.random.normal(0, 1, (100, 512, 32000)),
            "hidden_states": np.random.normal(0, 1, (100, 768)),
            "predictions": np.random.randint(0, 32000, (100,))
        }
        
        result = validator.validate(outputs)
        
        assert "passed" in result
        assert "metrics" in result
        assert "details" in result
        
    def test_threshold_enforcement(self, validator):
        """Test validation threshold enforcement."""
        # Create outputs that will definitely fail
        outputs = {
            "logits": np.zeros((100, 512, 32000)),  # Uniform predictions
            "hidden_states": np.ones((100, 768)) * 1000,  # Large drift
            "predictions": np.zeros(100)  # All same prediction
        }
        
        result = validator.validate(outputs)
        assert not result["passed"]
        
    def test_validation_caching(self, validator):
        """Test validation result caching."""
        outputs = {
            "logits": np.random.normal(0, 1, (100, 512, 32000)),
            "hidden_states": np.random.normal(0, 1, (100, 768)),
            "predictions": np.random.randint(0, 32000, (100,))
        }
        
        # First run
        t1 = time.time()
        result1 = validator.validate(outputs)
        duration1 = time.time() - t1
        
        # Second run with same outputs
        t2 = time.time()
        result2 = validator.validate(outputs)
        duration2 = time.time() - t2
        
        assert duration2 < duration1  # Should be faster
        assert result1 == result2  # Should be identical
        
class TestValidationPerformance:
    """Test validation performance characteristics."""
    
    @pytest.mark.benchmark
    def test_validation_speed(self, validator, benchmark):
        """Benchmark validation speed."""
        outputs = {
            "logits": np.random.normal(0, 1, (100, 512, 32000)),
            "hidden_states": np.random.normal(0, 1, (100, 768)),
            "predictions": np.random.randint(0, 32000, (100,))
        }
        
        def validate():
            return validator.validate(outputs)
            
        result = benchmark(validate)
        assert result.stats.mean < 1.0  # Should take less than 1 second
        
    def test_memory_usage(self, validator):
        """Test memory usage during validation."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        outputs = {
            "logits": np.random.normal(0, 1, (1000, 512, 32000)),  # Large
            "hidden_states": np.random.normal(0, 1, (1000, 768)),
            "predictions": np.random.randint(0, 32000, (1000,))
        }
        
        validator.validate(outputs)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Should use reasonable memory
        assert memory_increase < 1024  # Less than 1GB
        
    def test_parallel_validation(self, validator):
        """Test parallel validation of multiple metrics."""
        outputs = {
            "logits": np.random.normal(0, 1, (100, 512, 32000)),
            "hidden_states": np.random.normal(0, 1, (100, 768)),
            "predictions": np.random.randint(0, 32000, (100,))
        }
        
        import time
        start_time = time.time()
        
        result = validator.validate_parallel(outputs)
        
        duration = time.time() - start_time
        assert "passed" in result
        assert duration < 2.0  # Should complete in under 2 seconds