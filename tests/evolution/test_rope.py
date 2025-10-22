"""Tests for RoPE parameter adjustment functionality."""

import pytest
import numpy as np
from pathlib import Path
import json
from typing import Dict, Any, Tuple

from evolution.core.rope import (
    RoPEConfig,
    RoPEAdjuster,
    RoPEError,
    validate_rope_config
)
from evolution.core.tensor import Tensor
from evolution.core.validation import ValidationMetrics

@pytest.fixture
def test_tensors():
    """Create test rotary position embedding tensors."""
    seq_len = 512
    dim = 128
    
    # Create sample position encodings
    freqs = 1.0 / (10000.0 ** (np.arange(0, dim, 2) / dim))
    phases = np.outer(np.arange(seq_len), freqs)
    
    cos_values = np.cos(phases)
    sin_values = np.sin(phases)
    
    return {
        "cos": Tensor(
            name="rope_cos",
            data=cos_values,
            dtype=np.float32
        ),
        "sin": Tensor(
            name="rope_sin", 
            data=sin_values,
            dtype=np.float32
        )
    }

@pytest.fixture
def adjuster(test_tensors) -> RoPEAdjuster:
    """Create a RoPEAdjuster instance."""
    return RoPEAdjuster(
        config=RoPEConfig(
            target_ctx_len=2048,
            alpha=2.0,
            compress_ratio=0.5
        ),
        original_tensors=test_tensors
    )

class TestRoPEValidation:
    """Test RoPE parameter validation."""
    
    def test_valid_config(self):
        """Test validation with valid config."""
        config = {
            "target_ctx_len": 2048,
            "alpha": 2.0,
            "compress_ratio": 0.5
        }
        assert validate_rope_config(config) is None
        
    def test_invalid_context_length(self):
        """Test validation with invalid context length."""
        config = {
            "target_ctx_len": 0,  # Invalid
            "alpha": 2.0,
            "compress_ratio": 0.5
        }
        with pytest.raises(RoPEError, match="Invalid context length"):
            validate_rope_config(config)
            
    def test_invalid_alpha(self):
        """Test validation with invalid alpha."""
        config = {
            "target_ctx_len": 2048,
            "alpha": -1.0,  # Invalid
            "compress_ratio": 0.5
        }
        with pytest.raises(RoPEError, match="Invalid alpha"):
            validate_rope_config(config)
            
    def test_invalid_compression(self):
        """Test validation with invalid compression ratio."""
        config = {
            "target_ctx_len": 2048,
            "alpha": 2.0,
            "compress_ratio": 1.5  # Invalid
        }
        with pytest.raises(RoPEError, match="Invalid compression ratio"):
            validate_rope_config(config)

class TestRoPEComputation:
    """Test RoPE computation functionality."""
    
    def test_basic_adjustment(self, adjuster):
        """Test basic RoPE parameter adjustment."""
        result = adjuster.adjust_tensors()
        
        assert "cos" in result
        assert "sin" in result
        assert isinstance(result["cos"], Tensor)
        assert isinstance(result["sin"], Tensor)
        
    def test_shape_preservation(self, adjuster):
        """Test shape preservation in adjusted tensors."""
        result = adjuster.adjust_tensors()
        
        for key in ["cos", "sin"]:
            assert result[key].data.shape == adjuster.original_tensors[key].data.shape
            
    def test_value_ranges(self, adjuster):
        """Test that adjusted values stay in valid ranges."""
        result = adjuster.adjust_tensors()
        
        for key in ["cos", "sin"]:
            values = result[key].data
            assert np.all(np.abs(values) <= 1.0)
            assert not np.any(np.isnan(values))
            assert not np.any(np.isinf(values))
            
    @pytest.mark.parametrize("alpha", [0.5, 1.0, 2.0, 4.0])
    def test_scaling_behavior(self, test_tensors, alpha):
        """Test scaling behavior with different alphas."""
        config = RoPEConfig(
            target_ctx_len=2048,
            alpha=alpha,
            compress_ratio=1.0  # No compression
        )
        adjuster = RoPEAdjuster(config, test_tensors)
        result = adjuster.adjust_tensors()
        
        # Check that frequencies are scaled by alpha
        orig_freqs = np.fft.fft2(test_tensors["cos"].data)
        new_freqs = np.fft.fft2(result["cos"].data)
        
        # Compare dominant frequencies
        orig_peak = np.unravel_index(np.argmax(np.abs(orig_freqs)), orig_freqs.shape)
        new_peak = np.unravel_index(np.argmax(np.abs(new_freqs)), new_freqs.shape)
        
        ratio = new_peak[1] / orig_peak[1] if orig_peak[1] != 0 else 1
        assert abs(ratio - alpha) < 0.1

class TestRoPECompression:
    """Test RoPE compression functionality."""
    
    def test_basic_compression(self, adjuster):
        """Test basic compression behavior."""
        result = adjuster.adjust_tensors()
        
        # Check that high frequency components are reduced
        orig_freqs = np.fft.fft2(adjuster.original_tensors["cos"].data)
        new_freqs = np.fft.fft2(result["cos"].data)
        
        # Higher frequencies should have lower magnitude
        high_freq_ratio = (
            np.abs(new_freqs[:, -10:]).mean() /
            np.abs(orig_freqs[:, -10:]).mean()
        )
        assert high_freq_ratio < 1.0
        
    @pytest.mark.parametrize("ratio", [0.25, 0.5, 0.75])
    def test_compression_ratios(self, test_tensors, ratio):
        """Test different compression ratios."""
        config = RoPEConfig(
            target_ctx_len=2048,
            alpha=1.0,
            compress_ratio=ratio
        )
        adjuster = RoPEAdjuster(config, test_tensors)
        result = adjuster.adjust_tensors()
        
        # Check frequency content reduction
        orig_power = np.abs(np.fft.fft2(test_tensors["cos"].data)).sum()
        new_power = np.abs(np.fft.fft2(result["cos"].data)).sum()
        
        power_ratio = new_power / orig_power
        assert abs(power_ratio - ratio) < 0.1
        
    def test_orthogonality(self, adjuster):
        """Test preservation of orthogonality properties."""
        result = adjuster.adjust_tensors()
        
        # Check cos^2 + sin^2 ≈ 1
        sum_squares = (
            np.square(result["cos"].data) +
            np.square(result["sin"].data)
        )
        np.testing.assert_allclose(sum_squares, 1.0, rtol=1e-5)

class TestContextExtension:
    """Test context length extension capabilities."""
    
    def test_context_extension(self, test_tensors):
        """Test extending context length."""
        config = RoPEConfig(
            target_ctx_len=1024,  # 2x original
            alpha=1.0,
            compress_ratio=1.0
        )
        adjuster = RoPEAdjuster(config, test_tensors)
        result = adjuster.adjust_tensors()
        
        # Check extrapolation quality
        for key in ["cos", "sin"]:
            orig_len = test_tensors[key].data.shape[0]
            extended = result[key].data[orig_len:]
            
            # Should follow similar pattern
            pattern_error = np.abs(
                extended - result[key].data[:orig_len]
            ).mean()
            assert pattern_error < 0.1
            
    def test_very_long_context(self, test_tensors):
        """Test extension to very long context."""
        config = RoPEConfig(
            target_ctx_len=8192,  # 16x original
            alpha=1.0,
            compress_ratio=1.0
        )
        adjuster = RoPEAdjuster(config, test_tensors)
        result = adjuster.adjust_tensors()
        
        # Check numerical stability
        for key in ["cos", "sin"]:
            values = result[key].data
            assert not np.any(np.isnan(values))
            assert not np.any(np.isinf(values))
            assert np.all(np.abs(values) <= 1.0)

class TestNumericalStability:
    """Test numerical stability of RoPE adjustments."""
    
    def test_extreme_alpha(self, adjuster):
        """Test stability with extreme alpha values."""
        adjuster.config.alpha = 100.0
        result = adjuster.adjust_tensors()
        
        for tensor in result.values():
            assert not np.any(np.isnan(tensor.data))
            assert not np.any(np.isinf(tensor.data))
            
    def test_extreme_compression(self, adjuster):
        """Test stability with extreme compression."""
        adjuster.config.compress_ratio = 0.01
        result = adjuster.adjust_tensors()
        
        for tensor in result.values():
            assert not np.any(np.isnan(tensor.data))
            assert not np.any(np.isinf(tensor.data))
            
    def test_precision_preservation(self, adjuster):
        """Test preservation of numerical precision."""
        result = adjuster.adjust_tensors()
        
        # Check that small differences are preserved
        eps = np.finfo(np.float32).eps
        delta = eps * 100
        
        for key in ["cos", "sin"]:
            original = adjuster.original_tensors[key].data
            modified = original + delta
            
            # Create new tensors with small difference
            tensors1 = {key: Tensor(key, original, np.float32)}
            tensors2 = {key: Tensor(key, modified, np.float32)}
            
            # Adjust both
            adj1 = RoPEAdjuster(adjuster.config, tensors1)
            adj2 = RoPEAdjuster(adjuster.config, tensors2)
            
            result1 = adj1.adjust_tensors()
            result2 = adj2.adjust_tensors()
            
            # Check that difference is preserved
            assert np.any(result1[key].data != result2[key].data)

class TestPerformance:
    """Test performance characteristics of RoPE adjustments."""
    
    @pytest.mark.benchmark
    def test_adjustment_speed(self, adjuster, benchmark):
        """Benchmark adjustment speed."""
        def adjust():
            return adjuster.adjust_tensors()
            
        result = benchmark(adjust)
        assert result.stats.mean < 1.0  # Should take less than 1 second
        
    def test_memory_usage(self, adjuster):
        """Test memory usage during adjustment."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        adjuster.adjust_tensors()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Should use reasonable memory
        input_size = sum(
            t.data.nbytes for t in adjuster.original_tensors.values()
        ) / (1024 * 1024)
        assert memory_increase < input_size * 3  # No more than 3x input
        
    def test_batch_processing(self, adjuster):
        """Test performance with batch processing."""
        # Create multiple sets of tensors
        tensor_sets = [
            adjuster.original_tensors.copy() for _ in range(10)
        ]
        
        import time
        start_time = time.time()
        
        results = adjuster.adjust_tensor_sets(tensor_sets)
        
        duration = time.time() - start_time
        assert len(results) == len(tensor_sets)
        assert duration < 2.0  # Should complete in under 2 seconds