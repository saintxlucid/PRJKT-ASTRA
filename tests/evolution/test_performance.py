"""Performance optimization tests for the evolution system."""

import pytest
import numpy as np
from pathlib import Path
import mmap
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from evolution.core.tensor_ops import StreamingTensorOps
from evolution.core.cache import TensorCache
from evolution.core.validator import ParallelValidator
from evolution.utils.memory import estimate_memory_usage

def test_streaming_tensor_operations(tensor_cache: Path, performance_monitor):
    """Test performance of streaming tensor operations."""
    ops = StreamingTensorOps()
    
    with performance_monitor.measure("streaming_tensor_load"):
        # Test streaming tensor loading
        tensors = []
        for tensor_path in (tensor_cache / "mapped").glob("*.bin"):
            with open(tensor_path, "rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                tensors.append(mm)
                
    # Verify memory efficiency
    stats = performance_monitor.get_stats("streaming_tensor_load")
    assert stats["max_memory"] < 1024 * 1024 * 1024  # Should use less than 1GB
    
    # Test streaming operations
    with performance_monitor.measure("streaming_tensor_ops"):
        for tensor in tensors:
            # Perform streaming operation (e.g., quantization)
            ops.stream_quantize(tensor, dtype=np.float16)
            
    stats = performance_monitor.get_stats("streaming_tensor_ops")
    assert stats["avg_duration"] < 2.0  # Operations should complete within 2 seconds on average

def test_memory_mapped_access(tensor_cache: Path, performance_monitor):
    """Test performance of memory-mapped file access."""
    cache = TensorCache(tensor_cache)
    
    with performance_monitor.measure("mmap_random_access"):
        # Test random access performance
        for _ in range(100):
            tensor_name = f"tensor_{np.random.randint(0, 3)}"
            data = cache.get_tensor(tensor_name)
            assert data is not None
            
    stats = performance_monitor.get_stats("mmap_random_access")
    assert stats["avg_duration"] < 0.01  # Each access should be very fast
    
    # Test memory efficiency during bulk operations
    with performance_monitor.measure("mmap_bulk_ops"):
        tensors = []
        for i in range(3):
            tensors.append(cache.get_tensor(f"tensor_{i}"))
            
    stats = performance_monitor.get_stats("mmap_bulk_ops")
    peak_mem = stats["max_memory"]
    assert peak_mem < sum(t.nbytes for t in tensors)  # Should use less memory than full tensors

def test_parallel_validation(parallel_validator, tensor_cache: Path, performance_monitor):
    """Test performance of parallel validation operations."""
    def validation_task(tensor_path: Path) -> bool:
        """Sample validation task."""
        with open(tensor_path, "rb") as f:
            data = np.fromfile(f, dtype=np.float32)
            return np.all(np.isfinite(data))
    
    tensor_paths = list((tensor_cache / "mapped").glob("*.bin"))
    
    with performance_monitor.measure("parallel_validation"):
        # Run validations in parallel
        results = parallel_validator.validate_batch(tensor_paths, validation_task)
        
    stats = performance_monitor.get_stats("parallel_validation")
    assert all(results)  # All validations should pass
    assert stats["avg_duration"] < len(tensor_paths) * 0.5  # Should be faster than sequential

def test_cache_performance(tensor_cache: Path, performance_monitor):
    """Test performance of tensor caching system."""
    cache = TensorCache(tensor_cache)
    
    # Test cache hit performance
    with performance_monitor.measure("cache_hits"):
        for _ in range(50):
            tensor = cache.get_tensor("tensor_0")
            assert tensor is not None
            
    stats = performance_monitor.get_stats("cache_hits")
    assert stats["avg_duration"] < 0.001  # Cache hits should be very fast
    
    # Test cache eviction and reloading
    with performance_monitor.measure("cache_eviction"):
        cache.clear()
        for i in range(3):
            tensor = cache.get_tensor(f"tensor_{i}")
            assert tensor is not None
            
    stats = performance_monitor.get_stats("cache_eviction")
    assert stats["max_memory"] < 2 * 1024 * 1024 * 1024  # Should maintain memory bounds

def test_concurrent_operations(tensor_cache: Path, parallel_validator, performance_monitor):
    """Test performance of concurrent operations."""
    cache = TensorCache(tensor_cache)
    
    def concurrent_task(tensor_name: str) -> Dict[str, Any]:
        """Sample concurrent operation."""
        tensor = cache.get_tensor(tensor_name)
        stats = {
            "mean": float(np.mean(tensor)),
            "std": float(np.std(tensor)),
            "shape": tensor.shape
        }
        return stats
    
    tensor_names = [f"tensor_{i}" for i in range(3)]
    
    with performance_monitor.measure("concurrent_ops"):
        results = parallel_validator.validate_batch(tensor_names, concurrent_task)
        
    stats = performance_monitor.get_stats("concurrent_ops")
    assert len(results) == len(tensor_names)
    assert stats["avg_duration"] < len(tensor_names)  # Should process faster than sequential

def test_memory_efficiency(tensor_cache: Path, performance_monitor):
    """Test overall memory efficiency of operations."""
    cache = TensorCache(tensor_cache)
    
    def memory_intensive_task():
        """Perform memory-intensive operations."""
        tensors = []
        for i in range(3):
            tensor = cache.get_tensor(f"tensor_{i}")
            # Process tensor in streaming fashion
            processed = StreamingTensorOps().stream_quantize(tensor, dtype=np.float16)
            tensors.append(processed)
        return tensors
    
    with performance_monitor.measure("memory_efficiency"):
        results = memory_intensive_task()
        
    stats = performance_monitor.get_stats("memory_efficiency")
    total_tensor_size = sum(t.nbytes for t in results)
    assert stats["max_memory"] < total_tensor_size * 1.5  # Should use less than 1.5x tensor size
    
    # Verify we're not leaking memory
    del results
    final_stats = performance_monitor.get_stats("memory_efficiency")
    assert final_stats["memory_end"] < stats["memory_start"] * 1.1  # Allow for small overhead