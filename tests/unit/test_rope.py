"""Unit tests for RoPE parameter configuration and tuning."""
import pytest
from evolution.gguf.rope import RoPEConfig

def test_rope_config_validation():
    """Test RoPE config validation."""
    # Valid config
    config = RoPEConfig(
        freq_base=10000,
        freq_scale=1.0,
        dimensions=128
    )
    assert config.is_valid()
    
    # Invalid freq_base
    with pytest.raises(ValueError):
        RoPEConfig(
            freq_base=-1,
            freq_scale=1.0,
            dimensions=128
        )
    
    # Invalid freq_scale
    with pytest.raises(ValueError):
        RoPEConfig(
            freq_base=10000,
            freq_scale=0,
            dimensions=128
        )
    
    # Invalid dimensions
    with pytest.raises(ValueError):
        RoPEConfig(
            freq_base=10000,
            freq_scale=1.0,
            dimensions=0
        )

def test_rope_config_interpolation():
    """Test RoPE parameter interpolation."""
    config = RoPEConfig(
        freq_base=10000,
        freq_scale=1.0,
        dimensions=128
    )
    
    # Test position encoding
    pos = 1000
    encoding = config.get_position_encoding(pos)
    assert encoding.shape == (config.dimensions,)
    assert encoding.dtype == "float32"
    
    # Test interpolation
    pos2 = 2000
    encoding2 = config.get_position_encoding(pos2)
    assert (encoding2 != encoding).any()

def test_rope_config_serialization():
    """Test RoPE config serialization."""
    config = RoPEConfig(
        freq_base=10000,
        freq_scale=1.0,
        dimensions=128
    )
    
    # Test to dict
    config_dict = config.dict()
    assert config_dict["freq_base"] == 10000
    assert config_dict["freq_scale"] == 1.0
    assert config_dict["dimensions"] == 128
    
    # Test from dict
    new_config = RoPEConfig(**config_dict)
    assert new_config == config

def test_rope_config_compatibility():
    """Test RoPE config compatibility checking."""
    config1 = RoPEConfig(
        freq_base=10000,
        freq_scale=1.0,
        dimensions=128
    )
    
    config2 = RoPEConfig(
        freq_base=10000,
        freq_scale=2.0,  # Different scale
        dimensions=128
    )
    
    config3 = RoPEConfig(
        freq_base=10000,
        freq_scale=1.0,
        dimensions=256  # Different dimensions
    )
    
    assert config1.is_compatible_with(config1)
    assert not config1.is_compatible_with(config2)
    assert not config1.is_compatible_with(config3)