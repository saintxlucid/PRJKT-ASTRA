"""Unit tests for the ModelSurgeon class."""
import pytest
from evolution.gguf.surgeon import ModelSurgeon
from evolution.gguf.manifest import AdapterManifest

def test_merge_loras():
    """Test LoRA adapter merging."""
    surgeon = ModelSurgeon()
    manifest = AdapterManifest("tests/fixtures/manifest.json")
    
    result = surgeon.merge_loras(
        "tests/fixtures/base.gguf",
        manifest.get_merge_order().values()
    )
    
    assert result.success
    assert result.metrics.acc >= 0.8
    assert result.metrics.ppl <= 10.0
    assert result.metrics.drift <= 0.15

def test_tune_rope():
    """Test RoPE parameter tuning."""
    surgeon = ModelSurgeon()
    config = {
        "freq_base": 10000,
        "freq_scale": 1.0,
        "dimensions": 128
    }
    
    result = surgeon.tune_rope(
        "tests/fixtures/model.gguf",
        config,
        "tests/fixtures/model.rope.gguf"
    )
    
    assert result.success
    assert result.metrics.attention >= 0.85
    assert result.metrics.context >= 0.90
    assert result.metrics.drift <= 0.15

def test_validate():
    """Test model validation."""
    surgeon = ModelSurgeon()
    metrics = surgeon.validate(
        "tests/fixtures/model.gguf",
        "tests/fixtures/eval/"
    )
    
    assert metrics.passes_gates()
    assert metrics.acc >= 0.8
    assert metrics.guardrail >= 0.95

def test_embed_provenance():
    """Test provenance embedding."""
    surgeon = ModelSurgeon()
    metadata = {
        "type": "merge",
        "adapters": ["adapter1", "adapter2"]
    }
    
    checksum, signature = surgeon.embed_provenance(
        "tests/fixtures/model.gguf",
        metadata
    )
    
    assert len(checksum) == 64  # SHA-256
    assert len(signature) > 0