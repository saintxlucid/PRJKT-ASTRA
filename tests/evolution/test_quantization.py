"""Tests for model quantization functionality."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
from typing import Dict, Any

from evolution.core.quantization import (
    QuantizationConfig,
    ModelQuantizer,
    QuantizationError,
    validate_quantization_params
)
from evolution.core.formats import Format
from evolution.core.validation import ValidationMetrics
from evolution.core.tensor import Tensor

def create_test_tensor(shape: tuple, dtype: np.dtype) -> Tensor:
    """Create a test tensor with normal distribution."""
    return Tensor(
        name="test_tensor",
        data=np.random.normal(0, 1, shape).astype(dtype),
        dtype=dtype
    )

@pytest.fixture
def mock_model_path(tmp_path) -> Path:
    """Create a mock model file."""
    model_path = tmp_path / "model.bin"
    with open(model_path, "wb") as f:
        f.write(b"MOCK_MODEL")
    return model_path

@pytest.fixture
def quantizer(mock_model_path) -> ModelQuantizer:
    """Create a ModelQuantizer instance."""
    return ModelQuantizer(
        model_path=mock_model_path,
        config=QuantizationConfig(
            format=Format.Q4_K_M,
            compute_dtype="float16",
            strict=True
        )
    )

class TestQuantizationValidation:
    """Test quantization parameter validation."""
    
    def test_valid_format(self):
        """Test validation with valid format."""
        params = {
            "format": "Q4_K_M",
            "compute_dtype": "float16",
            "strict": True
        }
        assert validate_quantization_params(params) is None
        
    def test_invalid_format(self):
        """Test validation with invalid format."""
        params = {
            "format": "INVALID",
            "compute_dtype": "float16",
            "strict": True
        }
        with pytest.raises(QuantizationError, match="Invalid format"):
            validate_quantization_params(params)
            
    def test_invalid_compute_dtype(self):
        """Test validation with invalid compute dtype."""
        params = {
            "format": "Q4_K_M",
            "compute_dtype": "float128",
            "strict": True
        }
        with pytest.raises(QuantizationError, match="Invalid compute_dtype"):
            validate_quantization_params(params)
            
    @pytest.mark.parametrize("format,min_bits", [
        ("Q4_K_M", 4),
        ("Q5_K_M", 5),
        ("Q6_K", 6),
        ("Q8_0", 8)
    ])
    def test_format_bit_depths(self, format: str, min_bits: int):
        """Test format bit depth requirements."""
        params = {
            "format": format,
            "compute_dtype": "float16",
            "strict": True
        }
        assert validate_quantization_params(params) is None

class TestQuantizationConversion:
    """Test quantization conversion operations."""
    
    def test_small_tensor_quantization(self, quantizer):
        """Test quantization of small tensor."""
        tensor = create_test_tensor((32, 32), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        
        assert quantized.dtype == np.int8
        assert quantized.data.shape == tensor.data.shape
        
    def test_large_tensor_quantization(self, quantizer):
        """Test quantization of large tensor."""
        tensor = create_test_tensor((1024, 1024), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        
        assert quantized.dtype == np.int8
        assert quantized.data.shape == tensor.data.shape
        
    def test_tensor_round_trip(self, quantizer):
        """Test quantize-dequantize round trip."""
        tensor = create_test_tensor((64, 64), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        dequantized = quantizer.dequantize_tensor(quantized)
        
        # Allow for small numerical differences
        np.testing.assert_allclose(
            tensor.data,
            dequantized.data,
            rtol=1e-2,
            atol=1e-2
        )
        
    @pytest.mark.parametrize("shape", [
        (32, 32),
        (64, 64),
        (128, 128)
    ])
    def test_shape_preservation(self, quantizer, shape):
        """Test shape preservation across quantization."""
        tensor = create_test_tensor(shape, np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        assert quantized.data.shape == shape

class TestQuantizationGuardrails:
    """Test quantization safety guardrails."""
    
    def test_value_range_check(self, quantizer):
        """Test handling of values outside expected range."""
        tensor = create_test_tensor((32, 32), np.float32)
        tensor.data *= 1e6  # Create very large values
        
        with pytest.raises(QuantizationError, match="Value range"):
            quantizer.quantize_tensor(tensor)
            
    def test_nan_detection(self, quantizer):
        """Test detection of NaN values."""
        tensor = create_test_tensor((32, 32), np.float32)
        tensor.data[0, 0] = np.nan
        
        with pytest.raises(QuantizationError, match="NaN values"):
            quantizer.quantize_tensor(tensor)
            
    def test_inf_detection(self, quantizer):
        """Test detection of infinite values."""
        tensor = create_test_tensor((32, 32), np.float32)
        tensor.data[0, 0] = np.inf
        
        with pytest.raises(QuantizationError, match="Infinite values"):
            quantizer.quantize_tensor(tensor)
            
    def test_dtype_compatibility(self, quantizer):
        """Test dtype compatibility checks."""
        tensor = create_test_tensor((32, 32), np.complex64)
        
        with pytest.raises(QuantizationError, match="Unsupported dtype"):
            quantizer.quantize_tensor(tensor)

class TestQuantizationMetrics:
    """Test quantization quality metrics."""
    
    def test_accuracy_preservation(self, quantizer):
        """Test accuracy preservation after quantization."""
        tensor = create_test_tensor((128, 128), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        dequantized = quantizer.dequantize_tensor(quantized)
        
        metrics = ValidationMetrics.compute_metrics(
            original=tensor.data,
            quantized=dequantized.data
        )
        
        assert metrics.accuracy > 0.95  # 95% accuracy threshold
        
    def test_cosine_similarity(self, quantizer):
        """Test cosine similarity after quantization."""
        tensor = create_test_tensor((128, 128), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        dequantized = quantizer.dequantize_tensor(quantized)
        
        metrics = ValidationMetrics.compute_metrics(
            original=tensor.data,
            quantized=dequantized.data
        )
        
        assert metrics.cosine_similarity > 0.98  # 98% similarity threshold
        
    def test_relative_error(self, quantizer):
        """Test relative error after quantization."""
        tensor = create_test_tensor((128, 128), np.float32)
        quantized = quantizer.quantize_tensor(tensor)
        dequantized = quantizer.dequantize_tensor(quantized)
        
        metrics = ValidationMetrics.compute_metrics(
            original=tensor.data,
            quantized=dequantized.data
        )
        
        assert metrics.relative_error < 0.1  # 10% max error threshold

class TestQuantizationPerformance:
    """Test quantization performance characteristics."""
    
    @pytest.mark.benchmark
    def test_quantization_speed(self, quantizer, benchmark):
        """Benchmark quantization speed."""
        tensor = create_test_tensor((1024, 1024), np.float32)
        
        def quantize():
            return quantizer.quantize_tensor(tensor)
            
        result = benchmark(quantize)
        assert result.stats.mean < 1.0  # Should take less than 1 second
        
    @pytest.mark.benchmark
    def test_memory_usage(self, quantizer):
        """Test memory usage during quantization."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        tensor = create_test_tensor((2048, 2048), np.float32)
        quantizer.quantize_tensor(tensor)
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Should not use more than 2x the tensor size
        assert memory_increase < (tensor.data.nbytes / (1024 * 1024)) * 2
        
    def test_parallel_quantization(self, quantizer):
        """Test parallel quantization of multiple tensors."""
        tensors = [
            create_test_tensor((512, 512), np.float32)
            for _ in range(4)
        ]
        
        import time
        start_time = time.time()
        
        quantized = quantizer.quantize_tensors_parallel(tensors)
        
        duration = time.time() - start_time
        assert len(quantized) == len(tensors)
        assert duration < 2.0  # Should complete in under 2 seconds