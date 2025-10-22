"""Tests for low-level tensor operations optimization."""

import os
import mmap
import pytest
import numpy as np
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Iterator

from astra.evolution.backend.tensor_ops import (
    StreamingTensorReader,
    MemoryMappedTensor,
    ParallelValidator,
    TensorCache,
    PerformanceMetrics
)

@pytest.fixture
def large_tensor_file() -> Path:
    """Create a large test tensor file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
        # Create 100MB test tensor
        shape = (1000, 1000)  # 1000x1000 float32 = ~4MB
        tensor_data = np.random.randn(*shape).astype(np.float32)
        
        # Save with metadata header
        header = {
            "dtype": "float32",
            "shape": shape,
            "version": 1
        }
        
        # Write header
        header_bytes = str(header).encode()
        f.write(len(header_bytes).to_bytes(4, "little"))
        f.write(header_bytes)
        
        # Write tensor data
        tensor_data.tofile(f)
        
    return Path(f.name)

@pytest.fixture
def validation_data() -> List[Dict]:
    """Create test validation data."""
    return [
        {"input": "test input 1", "expected": "test output 1"},
        {"input": "test input 2", "expected": "test output 2"},
        {"input": "test input 3", "expected": "test output 3"},
        {"input": "test input 4", "expected": "test output 4"}
    ]

class TestStreamingOperations:
    """Test streaming tensor operations."""
    
    def test_streaming_read(self, large_tensor_file):
        """Test streaming tensor reading."""
        reader = StreamingTensorReader(large_tensor_file)
        
        # Read tensor in chunks
        chunks = []
        total_size = 0
        
        for chunk in reader.stream_tensor(chunk_size=1024*1024):  # 1MB chunks
            chunks.append(chunk)
            total_size += chunk.nbytes
            
        # Verify complete read
        assert total_size == os.path.getsize(large_tensor_file) - reader.header_size
        
        # Verify data integrity
        reconstructed = np.concatenate([c.reshape(-1) for c in chunks])
        original = np.fromfile(large_tensor_file, offset=reader.header_size, dtype=np.float32)
        np.testing.assert_array_equal(reconstructed, original)
        
    def test_streaming_shapes(self, large_tensor_file):
        """Test shape handling in streaming operations."""
        reader = StreamingTensorReader(large_tensor_file)
        
        # Get tensor info
        info = reader.get_tensor_info()
        assert "shape" in info
        assert "dtype" in info
        
        # Verify chunks maintain shape compatibility
        chunk_size = 1024 * 1024  # 1MB
        for chunk in reader.stream_tensor(chunk_size=chunk_size):
            # Should be properly shaped for original dimensions
            assert chunk.size % np.prod(info["shape"][1:]) == 0
            
    def test_streaming_performance(self, large_tensor_file):
        """Test streaming performance metrics."""
        reader = StreamingTensorReader(large_tensor_file)
        metrics = PerformanceMetrics()
        
        with metrics.measure("streaming_read"):
            for chunk in reader.stream_tensor(chunk_size=1024*1024):
                # Simulate some processing
                _ = chunk.mean()
                
        assert metrics.get_metric("streaming_read").count == 1
        assert metrics.get_metric("streaming_read").duration > 0

class TestMemoryMapping:
    """Test memory-mapped tensor operations."""
    
    def test_mmap_tensor(self, large_tensor_file):
        """Test memory-mapped tensor access."""
        tensor = MemoryMappedTensor(large_tensor_file)
        
        # Access should not load full tensor
        assert not tensor.is_fully_loaded
        
        # Read small section
        subset = tensor[0:10, 0:10]
        assert subset.shape == (10, 10)
        
        # Verify lazy loading
        assert not tensor.is_fully_loaded
        
    def test_mmap_updates(self, large_tensor_file):
        """Test memory-mapped tensor updates."""
        tensor = MemoryMappedTensor(large_tensor_file)
        
        # Update small section
        new_data = np.ones((10, 10), dtype=np.float32)
        tensor[0:10, 0:10] = new_data
        
        # Read back
        read_back = tensor[0:10, 0:10]
        np.testing.assert_array_equal(read_back, new_data)
        
    def test_mmap_concurrent_access(self, large_tensor_file):
        """Test concurrent memory-mapped tensor access."""
        tensor = MemoryMappedTensor(large_tensor_file)
        
        def read_section(idx: int) -> np.ndarray:
            return tensor[idx:idx+10, 0:10].copy()
        
        # Concurrent reads
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(read_section, range(0, 40, 10)))
            
        assert len(results) == 4
        assert all(r.shape == (10, 10) for r in results)

class TestParallelValidation:
    """Test parallel validation functionality."""
    
    def test_parallel_validation(self, validation_data):
        """Test parallel validation execution."""
        validator = ParallelValidator(num_workers=4)
        
        def validate_item(item: Dict) -> bool:
            return item["input"].replace("input", "output") == item["expected"]
        
        # Run validation in parallel
        results = validator.validate_batch(validation_data, validate_item)
        
        assert len(results) == len(validation_data)
        assert all(results)  # All should pass
        
    def test_early_stopping(self, validation_data):
        """Test early stopping in parallel validation."""
        validator = ParallelValidator(num_workers=4)
        
        def validate_item(item: Dict) -> bool:
            if item["input"] == "test input 3":
                return False
            return True
            
        # Should stop after first failure
        results = validator.validate_batch(
            validation_data,
            validate_item,
            early_stop=True
        )
        
        assert len(results) < len(validation_data)
        assert not all(results)  # Should have failure
        
    def test_validation_metrics(self, validation_data):
        """Test validation performance metrics."""
        validator = ParallelValidator(num_workers=4)
        metrics = PerformanceMetrics()
        
        def validate_item(item: Dict) -> bool:
            return True
            
        with metrics.measure("parallel_validation"):
            results = validator.validate_batch(validation_data, validate_item)
            
        assert metrics.get_metric("parallel_validation").count == 1
        assert metrics.get_metric("parallel_validation").duration > 0
        
    def test_progress_tracking(self, validation_data):
        """Test validation progress tracking."""
        validator = ParallelValidator(num_workers=4)
        progress = []
        
        def progress_callback(completed: int, total: int) -> None:
            progress.append((completed, total))
            
        results = validator.validate_batch(
            validation_data,
            lambda x: True,
            progress_callback=progress_callback
        )
        
        assert len(progress) > 0
        assert progress[-1] == (len(validation_data), len(validation_data))

class TestCaching:
    """Test tensor caching functionality."""
    
    def test_cache_operations(self, large_tensor_file):
        """Test basic cache operations."""
        cache = TensorCache(max_size=1024*1024*10)  # 10MB cache
        
        # Read tensor in chunks
        reader = StreamingTensorReader(large_tensor_file)
        
        for i, chunk in enumerate(reader.stream_tensor(chunk_size=1024*1024)):
            key = f"chunk_{i}"
            cache.store(key, chunk)
            
            # Verify retrieval
            cached = cache.get(key)
            assert cached is not None
            np.testing.assert_array_equal(cached, chunk)
            
    def test_cache_eviction(self, large_tensor_file):
        """Test cache eviction policy."""
        # Small cache to force eviction
        cache = TensorCache(max_size=1024*1024)  # 1MB cache
        
        reader = StreamingTensorReader(large_tensor_file)
        stored_keys = []
        
        for i, chunk in enumerate(reader.stream_tensor(chunk_size=1024*512)):  # 512KB chunks
            key = f"chunk_{i}"
            cache.store(key, chunk)
            stored_keys.append(key)
            
            # Verify oldest chunks get evicted
            if i > 2:  # After storing >1MB
                assert not cache.contains(stored_keys[0])
                
    def test_cache_metrics(self, large_tensor_file):
        """Test cache performance metrics."""
        cache = TensorCache(max_size=1024*1024*10)
        metrics = PerformanceMetrics()
        
        # Monitor cache operations
        with metrics.measure("cache_ops"):
            # Store some data
            data = np.random.randn(1000, 1000).astype(np.float32)
            cache.store("test_key", data)
            
            # Access multiple times
            for _ in range(10):
                _ = cache.get("test_key")
                
        assert metrics.get_metric("cache_ops").count == 1
        assert metrics.get_metric("cache_ops").duration > 0
        assert cache.get_stats().hits > 0
        
    def test_cache_persistence(self, large_tensor_file, tmp_path):
        """Test cache persistence to disk."""
        cache_dir = tmp_path / "tensor_cache"
        cache = TensorCache(
            max_size=1024*1024*10,
            cache_dir=cache_dir
        )
        
        # Store some data
        data = np.random.randn(100, 100).astype(np.float32)
        cache.store("persistent_key", data)
        
        # Create new cache instance
        new_cache = TensorCache(
            max_size=1024*1024*10,
            cache_dir=cache_dir
        )
        
        # Should load from disk
        cached = new_cache.get("persistent_key")
        assert cached is not None
        np.testing.assert_array_equal(cached, data)