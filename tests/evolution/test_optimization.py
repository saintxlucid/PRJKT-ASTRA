"""Tests for performance optimization functionality."""

import pytest
import numpy as np
import torch
import time
from typing import Dict, List, Tuple, Optional
from unittest.mock import Mock, patch

from evolution.core.optimization import (
    PerformanceOptimizer,
    OptimizationConfig,
    OptimizationMetrics,
    DeviceProfile,
    ProfilerData,
    OptimizationError
)

@pytest.fixture
def sample_model():
    """Create a sample model for testing."""
    return torch.nn.Sequential(
        torch.nn.Linear(100, 50),
        torch.nn.ReLU(),
        torch.nn.Linear(50, 10)
    )

@pytest.fixture
def optimizer(sample_model):
    """Create a PerformanceOptimizer instance."""
    return PerformanceOptimizer(
        model=sample_model,
        config=OptimizationConfig(
            target_latency_ms=10,
            target_memory_mb=1000,
            enable_cuda_graphs=True,
            enable_tensorrt=False
        )
    )

@pytest.fixture
def sample_input():
    """Generate sample input tensor."""
    return torch.randn(1, 100)

class TestOptimizationConfig:
    """Test optimization configuration validation."""
    
    def test_valid_config(self):
        """Test valid configuration."""
        config = OptimizationConfig(
            target_latency_ms=10,
            target_memory_mb=1000,
            enable_cuda_graphs=True,
            enable_tensorrt=False
        )
        assert config.target_latency_ms == 10
        assert config.target_memory_mb == 1000
        
    def test_invalid_targets(self):
        """Test invalid target values."""
        with pytest.raises(OptimizationError):
            OptimizationConfig(
                target_latency_ms=-1,  # Invalid
                target_memory_mb=1000,
                enable_cuda_graphs=True,
                enable_tensorrt=False
            )
            
        with pytest.raises(OptimizationError):
            OptimizationConfig(
                target_latency_ms=10,
                target_memory_mb=-100,  # Invalid
                enable_cuda_graphs=True,
                enable_tensorrt=False
            )

class TestDeviceProfiler:
    """Test device profiling functionality."""
    
    def test_basic_profiling(self, optimizer, sample_input):
        """Test basic device profiling."""
        profile = optimizer.profile_device()
        
        assert isinstance(profile, DeviceProfile)
        assert profile.cuda_available == torch.cuda.is_available()
        assert isinstance(profile.memory_available_mb, int)
        assert profile.memory_available_mb > 0
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_specific_profiling(self, optimizer):
        """Test CUDA-specific profiling."""
        profile = optimizer.profile_device()
        
        assert profile.cuda_compute_capability > 0
        assert profile.cuda_memory_bandwidth_gbps > 0
        
    def test_profiling_errors(self):
        """Test handling of profiling errors."""
        with patch("torch.cuda.is_available", side_effect=Exception("CUDA error")):
            optimizer = PerformanceOptimizer(
                model=torch.nn.Linear(10, 10),
                config=OptimizationConfig(
                    target_latency_ms=10,
                    target_memory_mb=1000,
                    enable_cuda_graphs=True,
                    enable_tensorrt=False
                )
            )
            
            with pytest.raises(OptimizationError):
                optimizer.profile_device()

class TestModelProfiling:
    """Test model profiling functionality."""
    
    def test_latency_profiling(self, optimizer, sample_input):
        """Test model latency profiling."""
        profile_data = optimizer.profile_model(sample_input)
        
        assert isinstance(profile_data, ProfilerData)
        assert profile_data.average_latency_ms > 0
        assert len(profile_data.layer_latencies) > 0
        
    def test_memory_profiling(self, optimizer, sample_input):
        """Test model memory usage profiling."""
        profile_data = optimizer.profile_model(sample_input)
        
        assert profile_data.peak_memory_mb > 0
        assert len(profile_data.layer_memory) > 0
        
    def test_profile_batched_input(self, optimizer):
        """Test profiling with different batch sizes."""
        batch_sizes = [1, 4, 8, 16]
        profiles = []
        
        for batch_size in batch_sizes:
            input_tensor = torch.randn(batch_size, 100)
            profile = optimizer.profile_model(input_tensor)
            profiles.append(profile)
            
        # Latency should generally increase with batch size
        latencies = [p.average_latency_ms for p in profiles]
        assert all(a <= b for a, b in zip(latencies, latencies[1:]))

class TestOptimizationStrategies:
    """Test various optimization strategies."""
    
    def test_cuda_graphs(self, optimizer, sample_input):
        """Test CUDA Graphs optimization."""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
            
        metrics_before = optimizer.profile_model(sample_input)
        optimizer.enable_cuda_graphs()
        metrics_after = optimizer.profile_model(sample_input)
        
        assert metrics_after.average_latency_ms <= metrics_before.average_latency_ms
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_tensorrt_optimization(self, optimizer, sample_input):
        """Test TensorRT optimization if available."""
        try:
            import tensorrt
        except ImportError:
            pytest.skip("TensorRT not available")
            
        optimizer.config.enable_tensorrt = True
        metrics_before = optimizer.profile_model(sample_input)
        optimizer.optimize()
        metrics_after = optimizer.profile_model(sample_input)
        
        assert metrics_after.average_latency_ms <= metrics_before.average_latency_ms
        
    def test_memory_optimization(self, optimizer, sample_input):
        """Test memory usage optimization."""
        metrics_before = optimizer.profile_model(sample_input)
        optimizer.optimize_memory_usage()
        metrics_after = optimizer.profile_model(sample_input)
        
        assert metrics_after.peak_memory_mb <= metrics_before.peak_memory_mb

class TestOptimizationResults:
    """Test optimization results and metrics."""
    
    def test_optimization_success(self, optimizer, sample_input):
        """Test successful optimization."""
        initial_metrics = optimizer.profile_model(sample_input)
        result = optimizer.optimize()
        final_metrics = optimizer.profile_model(sample_input)
        
        assert result.success
        assert final_metrics.average_latency_ms <= optimizer.config.target_latency_ms
        assert final_metrics.peak_memory_mb <= optimizer.config.target_memory_mb
        
    def test_optimization_failure(self):
        """Test handling of optimization failure."""
        # Create model with impossible targets
        optimizer = PerformanceOptimizer(
            model=torch.nn.Linear(1000, 1000),
            config=OptimizationConfig(
                target_latency_ms=0.001,  # Impossible target
                target_memory_mb=1,  # Impossible target
                enable_cuda_graphs=True,
                enable_tensorrt=False
            )
        )
        
        result = optimizer.optimize()
        assert not result.success
        assert len(result.failure_reasons) > 0
        
    def test_metrics_tracking(self, optimizer, sample_input):
        """Test optimization metrics tracking."""
        optimizer.optimize()
        metrics = optimizer.get_optimization_metrics()
        
        assert isinstance(metrics, OptimizationMetrics)
        assert len(metrics.latency_history) > 0
        assert len(metrics.memory_usage_history) > 0
        assert metrics.optimization_time_ms > 0

class TestStressTests:
    """Test optimizer under stress conditions."""
    
    @pytest.mark.slow
    def test_continuous_optimization(self, optimizer, sample_input):
        """Test continuous optimization under load."""
        for _ in range(10):
            metrics_before = optimizer.profile_model(sample_input)
            optimizer.optimize()
            metrics_after = optimizer.profile_model(sample_input)
            
            assert metrics_after.average_latency_ms <= metrics_before.average_latency_ms
            
            # Add some computational load
            torch.randn(1000, 1000).mm(torch.randn(1000, 1000))
            
    @pytest.mark.slow
    def test_memory_pressure(self, optimizer, sample_input):
        """Test optimization under memory pressure."""
        # Create memory pressure
        tensors = []
        try:
            while True:
                tensors.append(torch.randn(1000, 1000))
        except RuntimeError:  # Out of memory
            pass
            
        # Should still be able to optimize
        result = optimizer.optimize()
        assert result.success
        
        # Cleanup
        del tensors
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_multi_gpu_optimization(self, sample_model):
        """Test optimization across multiple GPUs if available."""
        if torch.cuda.device_count() < 2:
            pytest.skip("Multiple GPUs not available")
            
        optimizers = []
        inputs = []
        
        for gpu_id in range(2):
            with torch.cuda.device(gpu_id):
                model_copy = sample_model.to(f"cuda:{gpu_id}")
                optimizer = PerformanceOptimizer(
                    model=model_copy,
                    config=OptimizationConfig(
                        target_latency_ms=10,
                        target_memory_mb=1000,
                        enable_cuda_graphs=True,
                        enable_tensorrt=False
                    )
                )
                optimizers.append(optimizer)
                inputs.append(torch.randn(1, 100).to(f"cuda:{gpu_id}"))
                
        # Optimize on both GPUs
        results = []
        for opt, inp in zip(optimizers, inputs):
            results.append(opt.optimize())
            
        assert all(r.success for r in results)

class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_optimization_retry(self, optimizer, sample_input):
        """Test retry mechanism for failed optimizations."""
        # Simulate failures then success
        original_optimize = optimizer._optimize_impl
        failure_count = [0]
        
        def mock_optimize(*args, **kwargs):
            if failure_count[0] < 2:
                failure_count[0] += 1
                raise RuntimeError("Optimization failed")
            return original_optimize(*args, **kwargs)
            
        with patch.object(optimizer, '_optimize_impl', side_effect=mock_optimize):
            result = optimizer.optimize(max_retries=3)
            assert result.success
            assert failure_count[0] == 2
            
    def test_resource_cleanup(self, optimizer, sample_input):
        """Test resource cleanup after optimization."""
        initial_memory = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        
        try:
            optimizer.optimize()
        except Exception:
            pass
            
        # Force garbage collection
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        final_memory = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        assert abs(final_memory - initial_memory) < 1024  # Within 1KB
        
    def test_interrupt_handling(self, optimizer, sample_input):
        """Test handling of optimization interruption."""
        def interrupt_optimization():
            time.sleep(0.1)
            raise KeyboardInterrupt
            
        import threading
        thread = threading.Thread(target=interrupt_optimization)
        thread.start()
        
        with pytest.raises(KeyboardInterrupt):
            optimizer.optimize()
            
        # Check cleanup
        assert optimizer.is_cleanup_complete()