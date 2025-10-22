"""Tests for RoPE tuning and grammar validation."""

import pytest
import numpy as np
from pathlib import Path
import json

from evolution.gguf.rope import RoPETuner, RoPEConfig
from evolution.gguf.grammar import GrammarValidator, ValidationResult

# RoPE Tuning Tests

def test_rope_arch_support():
    """Test architecture support checking."""
    tuner = RoPETuner()
    
    # Supported architecture
    kv_supported = {
        "arch.name": "llama",
        "rope.freq_base": 10000.0,
        "rope.scale": 1.0
    }
    supported, _ = tuner.check_arch_support(kv_supported)
    assert supported
    
    # Unsupported architecture
    kv_unsupported = {
        "arch.name": "gpt2",
        "rope.freq_base": 10000.0
    }
    supported, reason = tuner.check_arch_support(kv_unsupported)
    assert not supported
    assert "Unsupported architecture" in reason

def test_rope_parameter_tuning():
    """Test RoPE parameter tuning."""
    tuner = RoPETuner()
    
    kv = {
        "arch.name": "llama",
        "arch.max_seq_len": 2048,
        "rope.freq_base": 10000.0,
        "rope.scale": 1.0
    }
    
    # Test default tuning
    config = tuner.tune_parameters(kv)
    assert isinstance(config, RoPEConfig)
    assert config.scale == 1.15  # Default scale
    
    # Test target length tuning
    config = tuner.tune_parameters(kv, target_len=4096)
    assert config.max_seq_len == 4096
    assert config.scale >= 1.0

def test_rope_drift_measurement():
    """Test embedding drift measurement."""
    tuner = RoPETuner(drift_threshold=0.07)
    
    # Create mock embeddings
    base = {
        "test": np.array([1.0, 0.0, 0.0])
    }
    
    # No drift
    tuned_nodrift = {
        "test": np.array([1.0, 0.0, 0.0])
    }
    drift = tuner.measure_drift(base, tuned_nodrift)
    assert drift < tuner.drift_threshold
    
    # High drift
    tuned_drift = {
        "test": np.array([0.0, 1.0, 0.0])
    }
    drift = tuner.measure_drift(base, tuned_drift)
    assert drift > tuner.drift_threshold

def test_rope_validation():
    """Test RoPE tuning validation."""
    tuner = RoPETuner()
    
    kv = {
        "rope.scale": 1.15,
        "rope.freq_base": 1e6
    }
    
    config = RoPEConfig()
    embeddings = {
        "test": np.array([1.0, 0.0, 0.0])
    }
    
    # Valid configuration
    valid, _ = tuner.validate_tuning(kv, config, embeddings)
    assert valid
    
    # Invalid configuration
    bad_config = RoPEConfig(scale=10.0)  # Invalid scale
    valid, reason = tuner.validate_tuning(kv, bad_config, embeddings)
    assert not valid
    assert "Invalid configuration" in reason

# Grammar Validation Tests

def test_plan_grammar_validation():
    """Test plan grammar validation."""
    validator = GrammarValidator(
        plan_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "goal": {"type": "STRING"},
                "steps": {
                    "type": "JSON_ARRAY",
                    "items": {
                        "type": "JSON_OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "action": {"type": "STRING"}
                        }
                    }
                }
            },
            "required": ["goal", "steps"]
        },
        tool_grammar={}
    )
    
    # Valid plan
    valid_plan = {
        "goal": "Test goal",
        "steps": [
            {"id": "1", "action": "test"}
        ]
    }
    result = validator.validate_plan(json.dumps(valid_plan))
    assert result.valid
    assert not result.errors
    
    # Invalid plan
    invalid_plan = {
        "steps": "not an array"
    }
    result = validator.validate_plan(json.dumps(invalid_plan))
    assert not result.valid
    assert result.errors
    assert "Missing required field: goal" in result.errors

def test_tool_grammar_validation():
    """Test tool call grammar validation."""
    validator = GrammarValidator(
        plan_grammar={},
        tool_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "tool": {"type": "STRING"},
                "arguments": {"type": "JSON_OBJECT"}
            },
            "required": ["tool", "arguments"]
        }
    )
    
    # Valid tool call
    valid_tool = {
        "tool": "test_tool",
        "arguments": {"arg1": "val1"}
    }
    result = validator.validate_tool_call(json.dumps(valid_tool))
    assert result.valid
    assert not result.errors
    
    # Invalid tool call
    invalid_tool = {
        "tool": "test_tool"
        # Missing arguments
    }
    result = validator.validate_tool_call(json.dumps(invalid_tool))
    assert not result.valid
    assert result.errors
    assert "Missing required field: arguments" in result.errors

def test_grammar_fix_attempts():
    """Test grammar fix attempts."""
    validator = GrammarValidator(
        plan_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "goal": {"type": "STRING"},
                "steps": {"type": "JSON_ARRAY"}
            },
            "required": ["goal", "steps"]
        },
        tool_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "tool": {"type": "STRING"},
                "arguments": {"type": "JSON_OBJECT"}
            },
            "required": ["tool", "arguments"]
        }
    )
    
    # Test plan fixing
    invalid_plan = {
        "steps": "invalid"
    }
    result = validator.validate_plan(
        json.dumps(invalid_plan),
        fix=True
    )
    assert result.fixed_output
    fixed_plan = json.loads(result.fixed_output)
    assert "goal" in fixed_plan
    assert isinstance(fixed_plan["steps"], list)
    
    # Test tool call fixing
    invalid_tool = {
        "tool": "test",
        "arguments": "invalid"
    }
    result = validator.validate_tool_call(
        json.dumps(invalid_tool),
        fix=True
    )
    assert result.fixed_output
    fixed_tool = json.loads(result.fixed_output)
    assert isinstance(fixed_tool["arguments"], dict)

def test_regex_generation():
    """Test regex pattern generation."""
    validator = GrammarValidator(
        plan_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "goal": {"type": "STRING"},
                "steps": {"type": "JSON_ARRAY"}
            }
        },
        tool_grammar={
            "type": "JSON_OBJECT",
            "properties": {
                "tool": {"type": "STRING"}
            }
        }
    )
    
    patterns = validator.generate_regex()
    assert "plan" in patterns
    assert "tool" in patterns
    
    # Test plan pattern
    plan_json = '{"goal":"test","steps":[]}'
    assert re.match(patterns["plan"], plan_json)
    
    # Test tool pattern
    tool_json = '{"tool":"test"}'
    assert re.match(patterns["tool"], tool_json)