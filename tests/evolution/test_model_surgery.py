"""
Tests for model surgery operations.
"""

import pytest
import torch
import numpy as np
from pathlib import Path
from astra.evolution.backend.model_surgery import (
    ModelSurgeon,
    QuantizationConfig,
    LoRAConfig,
    RoPEConfig,
    ModelSurgeryError,
    QuantizationError,
    LoRAError,
    RoPEError,
    GGUFTensorType
)

@pytest.fixture
def test_model_path(tmp_path, sample_gguf_path):
    """Copy sample GGUF model for testing."""
    test_path = tmp_path / "test_model.gguf"
    test_path.write_bytes(sample_gguf_path.read_bytes())
    return test_path

@pytest.fixture
def test_lora_path(tmp_path, sample_gguf_path):
    """Create a test LoRA file."""
    lora_path = tmp_path / "test_lora.gguf"
    # Create minimal LoRA file with matching architecture
    lora_path.write_bytes(sample_gguf_path.read_bytes())
    return lora_path

@pytest.fixture
def surgeon(test_model_path):
    """Create ModelSurgeon instance."""
    return ModelSurgeon(str(test_model_path))

class TestModelSurgeon:
    def test_quantization_validation(self, surgeon, tmp_path):
        """Test quantization validation."""
        output_path = tmp_path / "quantized.gguf"
        
        # Test valid quantization
        config = QuantizationConfig(target_type=GGUFTensorType.Q4_K_M)
        surgeon.validate_quantization(config)  # Should not raise
        
        # Test invalid base model
        with surgeon:
            # Modify metadata to simulate quantized model
            metadata = surgeon.reader.read_metadata()
            metadata['quantization_type'] = 'Q4_0'
            
        with pytest.raises(QuantizationError, match="Cannot quantize from Q4_0"):
            surgeon.validate_quantization(config)

    def test_lora_validation(self, surgeon, test_lora_path, tmp_path):
        """Test LoRA validation."""
        output_path = tmp_path / "merged.gguf"
        
        # Test valid LoRA merge
        config = LoRAConfig(
            lora_paths=[str(test_lora_path)],
            alpha=0.8
        )
        surgeon.validate_lora(config)  # Should not raise
        
        # Test invalid architecture
        invalid_lora = tmp_path / "invalid_arch.gguf"
        with open(invalid_lora, "w") as f:
            f.write("invalid")  # Not a GGUF file
            
        config = LoRAConfig(lora_paths=[str(invalid_lora)])
        with pytest.raises(LoRAError, match="Architecture mismatch"):
            surgeon.validate_lora(config)

    def test_rope_validation(self, surgeon, tmp_path):
        """Test RoPE validation."""
        output_path = tmp_path / "rope_adjusted.gguf"
        
        # Test valid RoPE adjustment
        config = RoPEConfig(scale=1.2)
        surgeon.validate_rope(config)  # Should not raise
        
        # Test invalid scale
        config = RoPEConfig(scale=2.0)  # Above ROPE_SCALE_MAX
        with pytest.raises(RoPEError, match="RoPE scale must be between"):
            surgeon.validate_rope(config)

    def test_quantization(self, surgeon, tmp_path):
        """Test model quantization operation."""
        output_path = tmp_path / "quantized.gguf"
        config = QuantizationConfig(target_type=GGUFTensorType.Q4_K_M)
        
        result = surgeon.quantize(str(output_path), config)
        assert isinstance(result, dict)
        assert "changed_tensors" in result
        assert "bytes_delta_mb" in result
        assert "heatmap_vec" in result
        assert result["changed_tensors"] > 0
        assert result["bytes_delta_mb"] < 0  # Should reduce size
        assert len(result["heatmap_vec"]) == 64 * 24

    def test_lora_merge(self, surgeon, test_lora_path, tmp_path):
        """Test LoRA adapter merging."""
        output_path = tmp_path / "merged.gguf"
        config = LoRAConfig(
            lora_paths=[str(test_lora_path)],
            alpha=0.8,
            target_modules=["attention", "mlp"]
        )
        
        result = surgeon.merge_lora(str(output_path), config)
        assert isinstance(result, dict)
        assert "changed_tensors" in result
        assert "bytes_delta_mb" in result
        assert "heatmap_vec" in result
        assert result["changed_tensors"] > 0
        assert len(result["heatmap_vec"]) == 64 * 24

    def test_rope_adjustment(self, surgeon, tmp_path):
        """Test RoPE parameter adjustment."""
        output_path = tmp_path / "rope_adjusted.gguf"
        config = RoPEConfig(base=10000.0, scale=1.2)
        
        result = surgeon.adjust_rope(str(output_path), config)
        assert isinstance(result, dict)
        assert "changed_tensors" in result
        assert "bytes_delta_mb" in result
        assert "heatmap_vec" in result
        assert result["changed_tensors"] > 0
        assert result["bytes_delta_mb"] == 0.0  # Should not change size
        assert len(result["heatmap_vec"]) == 64 * 24

    def test_tensor_repacking(self, surgeon, tmp_path):
        """Test tensor repacking."""
        output_path = tmp_path / "repacked.gguf"
        result = surgeon.repack_tensors(str(output_path), alignment=64)
        
        assert isinstance(result, dict)
        assert "changed_tensors" in result
        assert "bytes_delta_mb" in result
        assert "heatmap_vec" in result
        assert result["changed_tensors"] > 0
        assert result["bytes_delta_mb"] <= 0  # Should not increase size
        assert len(result["heatmap_vec"]) == 64 * 24

    def test_delta_heatmap(self, surgeon, test_model_path, tmp_path):
        """Test delta heatmap computation."""
        modified_path = tmp_path / "modified.gguf"
        modified_path.write_bytes(test_model_path.read_bytes())
        
        heatmap = surgeon.compute_delta_heatmap(
            str(test_model_path),
            str(modified_path),
            sample_rate=0.5
        )
        
        assert isinstance(heatmap, list)
        assert len(heatmap) == 64 * 24
        assert all(-1.0 <= x <= 1.0 for x in heatmap)

    def test_context_manager(self, surgeon):
        """Test context manager behavior."""
        with surgeon as s:
            assert s.reader.file is not None
            assert s.reader.mmap is not None
        assert surgeon.reader.file is None or surgeon.reader.file.closed
        assert surgeon.reader.mmap is None or surgeon.reader.mmap.closed()