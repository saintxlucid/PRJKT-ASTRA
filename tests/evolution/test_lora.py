"""Tests for LoRA adapter merging functionality."""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import json
from typing import Dict, Any, List, Tuple

from evolution.core.lora import (
    LoRAConfig,
    LoRAMerger,
    LoRAError,
    validate_lora_config
)
from evolution.core.tensor import Tensor
from evolution.core.validation import ValidationMetrics

def create_test_weights(
    shapes: List[Tuple[int, ...]], 
    dtype=np.dtype('float32')
) -> List[Tensor]:
    """Create test weight tensors."""
    return [
        Tensor(
            name=f"weight_{i}",
            data=np.random.normal(0, 1, shape).astype(dtype),
            dtype=dtype
        )
        for i, shape in enumerate(shapes)
    ]

@pytest.fixture
def mock_base_model(tmp_path) -> Path:
    """Create a mock base model file."""
    model_path = tmp_path / "base_model.bin"
    weights = create_test_weights([
        (768, 768),  # q_proj
        (768, 768),  # k_proj
        (768, 768),  # v_proj
        (768, 3072)  # mlp
    ])
    
    # Save weights in simple format
    with open(model_path, "wb") as f:
        for tensor in weights:
            f.write(tensor.data.tobytes())
    return model_path

@pytest.fixture
def mock_lora_adapter(tmp_path) -> Path:
    """Create a mock LoRA adapter file."""
    adapter_path = tmp_path / "adapter.bin"
    
    # Create LoRA weights (smaller rank)
    rank = 8
    lora_weights = {
        "q_proj": (
            np.random.normal(0, 1, (768, rank)).astype(np.float32),
            np.random.normal(0, 1, (rank, 768)).astype(np.float32)
        ),
        "v_proj": (
            np.random.normal(0, 1, (768, rank)).astype(np.float32),
            np.random.normal(0, 1, (rank, 768)).astype(np.float32)
        )
    }
    
    # Save adapter with metadata
    metadata = {
        "format": "lorav2",
        "rank": rank,
        "alpha": 0.7,
        "target_modules": ["q_proj", "v_proj"]
    }
    
    with open(adapter_path, "wb") as f:
        # Write metadata
        metadata_bytes = json.dumps(metadata).encode()
        f.write(len(metadata_bytes).to_bytes(4, 'little'))
        f.write(metadata_bytes)
        
        # Write weights
        for name, (up, down) in lora_weights.items():
            f.write(up.tobytes())
            f.write(down.tobytes())
            
    return adapter_path

@pytest.fixture
def merger(mock_base_model, mock_lora_adapter) -> LoRAMerger:
    """Create a LoRAMerger instance."""
    return LoRAMerger(
        base_model_path=mock_base_model,
        config=LoRAConfig(
            adapter_path=mock_lora_adapter,
            alpha=0.7,
            target_modules=["q_proj", "v_proj"]
        )
    )

class TestLoRAValidation:
    """Test LoRA configuration validation."""
    
    def test_valid_config(self):
        """Test validation with valid config."""
        config = {
            "adapter_path": "adapter.bin",
            "alpha": 0.7,
            "target_modules": ["q_proj", "v_proj"]
        }
        assert validate_lora_config(config) is None
        
    def test_invalid_alpha(self):
        """Test validation with invalid alpha."""
        config = {
            "adapter_path": "adapter.bin",
            "alpha": -1.0,  # Invalid
            "target_modules": ["q_proj", "v_proj"]
        }
        with pytest.raises(LoRAError, match="Invalid alpha"):
            validate_lora_config(config)
            
    def test_invalid_target_modules(self):
        """Test validation with invalid target modules."""
        config = {
            "adapter_path": "adapter.bin",
            "alpha": 0.7,
            "target_modules": []  # Invalid
        }
        with pytest.raises(LoRAError, match="No target modules"):
            validate_lora_config(config)
            
    def test_missing_adapter(self):
        """Test validation with missing adapter."""
        config = {
            "alpha": 0.7,
            "target_modules": ["q_proj", "v_proj"]
        }
        with pytest.raises(LoRAError, match="Missing adapter_path"):
            validate_lora_config(config)

class TestLoRACompat:
    """Test LoRA compatibility checks."""
    
    def test_rank_compatibility(self, merger):
        """Test rank compatibility check."""
        # Modify rank in adapter
        with open(merger.config.adapter_path, "r+b") as f:
            metadata_len = int.from_bytes(f.read(4), 'little')
            metadata = json.loads(f.read(metadata_len))
            metadata["rank"] = 1024  # Too large
            f.seek(0)
            metadata_bytes = json.dumps(metadata).encode()
            f.write(len(metadata_bytes).to_bytes(4, 'little'))
            f.write(metadata_bytes)
            
        with pytest.raises(LoRAError, match="Incompatible rank"):
            merger.validate_compatibility()
            
    def test_shape_compatibility(self, merger, tmp_path):
        """Test shape compatibility check."""
        # Create adapter with wrong shapes
        bad_adapter = tmp_path / "bad_adapter.bin"
        rank = 8
        bad_weights = {
            "q_proj": (
                np.random.normal(0, 1, (1024, rank)),  # Wrong shape
                np.random.normal(0, 1, (rank, 768))
            )
        }
        
        metadata = {
            "format": "lorav2",
            "rank": rank,
            "alpha": 0.7,
            "target_modules": ["q_proj"]
        }
        
        with open(bad_adapter, "wb") as f:
            metadata_bytes = json.dumps(metadata).encode()
            f.write(len(metadata_bytes).to_bytes(4, 'little'))
            f.write(metadata_bytes)
            
            for up, down in bad_weights.values():
                f.write(up.tobytes())
                f.write(down.tobytes())
                
        merger.config.adapter_path = bad_adapter
        with pytest.raises(LoRAError, match="Shape mismatch"):
            merger.validate_compatibility()
            
    def test_dtype_compatibility(self, merger):
        """Test dtype compatibility check."""
        # Create adapter with wrong dtype
        weights = create_test_weights([
            (768, 8),
            (8, 768)
        ], dtype=np.float64)  # Wrong dtype
        
        with pytest.raises(LoRAError, match="Incompatible dtype"):
            merger.validate_weights_dtype(weights)

class TestLoRAMerging:
    """Test LoRA merging operations."""
    
    def test_merge_single_module(self, merger):
        """Test merging single module."""
        original = np.random.normal(0, 1, (768, 768))
        up = np.random.normal(0, 1, (768, 8))
        down = np.random.normal(0, 1, (8, 768))
        
        merged = merger.merge_module(
            original=original,
            up=up,
            down=down,
            alpha=0.7
        )
        
        assert merged.shape == original.shape
        assert not np.allclose(merged, original)  # Should be different
        
    def test_merge_all_modules(self, merger):
        """Test merging all modules."""
        result = merger.merge()
        
        # Check all target modules were merged
        for module in merger.config.target_modules:
            assert module in result
            assert isinstance(result[module], np.ndarray)
            
    def test_merge_scaling(self, merger):
        """Test LoRA scaling behavior."""
        alpha_values = [0.0, 0.5, 1.0]
        base = np.random.normal(0, 1, (768, 768))
        up = np.random.normal(0, 1, (768, 8))
        down = np.random.normal(0, 1, (8, 768))
        
        results = []
        for alpha in alpha_values:
            merged = merger.merge_module(base, up, down, alpha)
            results.append(merged)
            
        # Alpha 0 should equal base
        np.testing.assert_allclose(results[0], base)
        
        # Higher alpha should mean bigger difference from base
        diff1 = np.abs(results[1] - base).mean()
        diff2 = np.abs(results[2] - base).mean()
        assert diff2 > diff1
        
    def test_merge_stability(self, merger):
        """Test numerical stability of merging."""
        # Test with extreme values
        original = np.random.normal(0, 1e3, (768, 768))  # Large values
        up = np.random.normal(0, 1e-3, (768, 8))  # Small values
        down = np.random.normal(0, 1, (8, 768))
        
        merged = merger.merge_module(original, up, down, 0.7)
        
        assert not np.any(np.isnan(merged))
        assert not np.any(np.isinf(merged))

class TestLoRAPerformance:
    """Test LoRA merging performance."""
    
    @pytest.mark.benchmark
    def test_merge_speed(self, merger, benchmark):
        """Benchmark merging speed."""
        def merge():
            return merger.merge()
            
        result = benchmark(merge)
        assert result.stats.mean < 1.0  # Should take less than 1 second
        
    def test_memory_efficiency(self, merger):
        """Test memory usage during merging."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        merger.merge()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Should not use more than 3x the model size
        model_size = os.path.getsize(merger.base_model_path) / (1024 * 1024)
        assert memory_increase < model_size * 3
        
    def test_parallel_merging(self, merger):
        """Test parallel merging of modules."""
        import time
        start_time = time.time()
        
        result = merger.merge_parallel()
        
        duration = time.time() - start_time
        assert len(result) == len(merger.config.target_modules)
        assert duration < 2.0  # Should complete in under 2 seconds