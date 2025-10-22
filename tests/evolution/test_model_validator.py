"""
Tests for model validation functionality.
"""

import json
import pytest
import numpy as np
from pathlib import Path
from astra.evolution.backend.model_validator import (
    ModelValidator, 
    ValidationConfig,
    ValidationResult,
    ValidationError
)

@pytest.fixture
def sample_config():
    """Create test validation config."""
    return ValidationConfig(
        ppl_sample_size=128,
        ppl_context_size=32,
        drift_sample_size=50,
        drift_hidden_layers=[0, 6, 11],
        show_progress=False
    )

@pytest.fixture
def validator(sample_config):
    """Create ModelValidator instance."""
    return ModelValidator(sample_config)

@pytest.fixture
def sample_dataset(tmp_path):
    """Create test dataset file."""
    dataset = {
        "samples": [
            "This is a test sample",
            "Another test sample",
            "Third test sample for validation"
        ]
    }
    dataset_path = tmp_path / "test_dataset.json"
    with open(dataset_path, "w") as f:
        json.dump(dataset, f)
    return str(dataset_path)

@pytest.fixture
def base_model(tmp_path):
    """Create base model file for testing."""
    model_path = tmp_path / "base_model.gguf"
    model_path.touch()  # Create empty file
    return str(model_path)

@pytest.fixture
def evolved_model(tmp_path):
    """Create evolved model file for testing."""
    model_path = tmp_path / "evolved_model.gguf"
    model_path.touch()  # Create empty file
    return str(model_path)

class TestModelValidator:
    def test_calculate_perplexity(self, validator, base_model):
        """Test perplexity calculation."""
        ppl, details = validator.calculate_perplexity(
            base_model,
            ["Test sample text"]
        )
        assert 0 < ppl < float("inf")
        assert "samples" in details
        assert "tokens" in details

    def test_evaluate_accuracy(self, validator, evolved_model, sample_dataset):
        """Test accuracy evaluation."""
        accuracy, details = validator.evaluate_accuracy(
            evolved_model,
            sample_dataset
        )
        assert 0 <= accuracy <= 1.0
        assert "samples" in details

    def test_measure_drift(self, validator, base_model, evolved_model):
        """Test model drift measurement."""
        drift, details = validator.measure_drift(
            base_model,
            evolved_model
        )
        assert 0 <= drift <= 1.0
        assert "samples" in details
        assert "layers" in details

    def test_early_stopping_on_high_ppl(self, validator):
        """Test early stopping on high perplexity increase."""
        should_stop, reason = validator.check_early_stopping(
            base_ppl=8.0,
            evolved_ppl=10.0,  # 25% increase
            accuracy=0.9,
            drift=0.05
        )
        assert should_stop
        assert "Perplexity increased" in reason

    def test_early_stopping_on_low_accuracy(self, validator):
        """Test early stopping on low accuracy."""
        should_stop, reason = validator.check_early_stopping(
            base_ppl=8.0,
            evolved_ppl=8.5,
            accuracy=0.85,  # Below min threshold
            drift=0.05
        )
        assert should_stop
        assert "Accuracy" in reason

    def test_early_stopping_on_high_drift(self, validator):
        """Test early stopping on high drift."""
        should_stop, reason = validator.check_early_stopping(
            base_ppl=8.0,
            evolved_ppl=8.5,
            accuracy=0.9,
            drift=0.08  # Above max threshold
        )
        assert should_stop
        assert "Drift" in reason

    def test_successful_validation(self, validator, base_model, evolved_model, sample_dataset):
        """Test successful full validation."""
        result = validator.validate(base_model, evolved_model, sample_dataset)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.perplexity, float)
        assert isinstance(result.accuracy, float)
        assert isinstance(result.drift, float)
        assert isinstance(result.passed, bool)
        assert isinstance(result.logs, list)
        assert isinstance(result.details, dict)

    def test_validation_error_handling(self, validator, base_model):
        """Test validation error handling."""
        with pytest.raises(ValidationError):
            # Invalid evolved model path
            validator.validate(base_model, "nonexistent.gguf")

    def test_create_default_validator(self):
        """Test creating validator with default config."""
        from astra.evolution.backend.model_validator import create_default_validator
        validator = create_default_validator()
        assert isinstance(validator, ModelValidator)
        assert isinstance(validator.config, ValidationConfig)