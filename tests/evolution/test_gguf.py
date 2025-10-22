"""Tests for GGUF LoRA merging and schema enforcement."""

import pytest
import numpy as np
from pathlib import Path
import json

from evolution.gguf.lora_merge import (
    GGUFModel,
    AdapterSpec,
    load_lora_gguf,
    merge_loras,
    l2_to_heatmap
)
from evolution.gguf.schema import (
    SchemaEnforcer,
    Plan,
    ToolCall
)

def test_load_lora_mismatched_dims():
    """Test handling of mismatched dimensions."""
    with pytest.raises(ValueError, match=r".*dimension mismatch.*"):
        adapter = load_lora_gguf("test_data/bad_dims.gguf")

def test_merge_deterministic():
    """Test merge operation is deterministic."""
    base = GGUFModel("test_data/base.gguf")
    adapter1 = load_lora_gguf("test_data/adapter1.gguf")
    adapter2 = load_lora_gguf("test_data/adapter2.gguf")
    
    # First merge
    changed1, l2_1 = merge_loras(base, [adapter1, adapter2])
    checksum1 = base.kv_get("astra.signature")["astra.checksum"]
    
    # Reset and merge again
    base = GGUFModel("test_data/base.gguf") 
    changed2, l2_2 = merge_loras(base, [adapter1, adapter2])
    checksum2 = base.kv_get("astra.signature")["astra.checksum"]
    
    assert checksum1 == checksum2
    assert changed1 == changed2
    assert l2_1 == l2_2

def test_heatmap_generation():
    """Test heatmap vector generation."""
    l2_norms = {
        f"layer.{i}": float(i) 
        for i in range(100)
    }
    
    heatmap = l2_to_heatmap(l2_norms, buckets=10)
    
    assert len(heatmap) == 10
    assert all(-1 <= x <= 1 for x in heatmap)
    assert heatmap[0] == -1  # First bucket
    assert abs(heatmap[-1] - 1) < 1e-6  # Last bucket

def test_provenance_roundtrip():
    """Test provenance data survives save/load."""
    base = GGUFModel("test_data/base.gguf")
    adapter = load_lora_gguf("test_data/adapter.gguf")
    
    # Merge and save
    merge_loras(base, [adapter])
    base.save("test_data/merged.gguf")
    
    # Load and check provenance
    loaded = GGUFModel("test_data/merged.gguf")
    provenance = loaded.kv_get("astra.signature")
    
    assert "astra.ops" in provenance
    assert "astra.timestamp" in provenance
    assert "astra.adapters" in provenance
    assert len(provenance["astra.adapters"]) == 1

def test_quantized_base_handling():
    """Test handling of quantized base model."""
    base = GGUFModel("test_data/quantized.gguf")
    adapter = load_lora_gguf("test_data/adapter.gguf")
    
    with pytest.raises(ValueError, match=r".*requires fp16 base.*"):
        merge_loras(base, [adapter])

def test_plan_schema_enforcement():
    """Test plan schema enforcement."""
    enforcer = SchemaEnforcer()
    
    # Valid plan
    valid_json = {
        "goal": "Test goal",
        "steps": [
            {
                "id": "1",
                "action": "test",
                "args": {"foo": "bar"}
            }
        ]
    }
    
    plan = enforcer.enforce_plan(json.dumps(valid_json))
    assert isinstance(plan, Plan)
    assert plan.goal == "Test goal"
    assert len(plan.steps) == 1
    
    # Invalid plan
    invalid_json = {"not_a_plan": True}
    with pytest.raises(ValueError):
        enforcer.enforce_plan(json.dumps(invalid_json))

def test_tool_call_schema_enforcement():
    """Test tool call schema enforcement."""
    enforcer = SchemaEnforcer()
    
    # Valid tool call
    valid_json = {
        "tool": "test_tool",
        "arguments": {"arg1": "val1"}
    }
    
    tool_call = enforcer.enforce_tool_call(json.dumps(valid_json))
    assert isinstance(tool_call, ToolCall)
    assert tool_call.tool == "test_tool"
    
    # Invalid tool call
    invalid_json = {"not_a_tool": True}
    with pytest.raises(ValueError):
        enforcer.enforce_tool_call(json.dumps(invalid_json))

def test_schema_retry_behavior():
    """Test schema enforcement retry behavior."""
    enforcer = SchemaEnforcer(retry_temp=0.2, max_retries=1)
    
    # Test retry with invalid JSON
    with pytest.raises(ValueError):
        enforcer.enforce_plan("invalid json")