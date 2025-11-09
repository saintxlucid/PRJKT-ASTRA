"""
Test Model Information Access

This script tests the model intelligence integration by accessing
GPT-OSS model specifications through the structured Pydantic models.

Usage:
    python scripts/test_model_info.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from src.astra.models.model_info import (
    get_model_info,
    list_available_models,
    GPT_OSS_120B_INFO,
    GPT_OSS_20B_INFO,
    ReasoningMode
)

def test_model_info():
    """Test model information access."""
    
    print("=" * 80)
    print("   GPT-OSS Model Information Test")
    print("=" * 80)
    print()
    
    # List available models
    print("[1/5] Available Models:")
    models = list_available_models()
    for model_id in models:
        print(f"   • {model_id}")
    print()
    
    # Test direct access to GPT-OSS-20B
    print("[2/5] GPT-OSS-20B Direct Access:")
    model = GPT_OSS_20B_INFO
    print(f"   Display Name: {model.display_name}")
    print(f"   Size: {model.model_size}")
    print(f"   Total Parameters: {model.architecture.total_parameters / 1e9:.1f}B")
    print(f"   Active Parameters: {model.architecture.active_parameters / 1e9:.1f}B")
    print(f"   Context Length: {model.architecture.context_length:,} tokens")
    print(f"   Quantization: {model.architecture.quantization}")
    print(f"   Checkpoint Size: {model.architecture.checkpoint_size_gb} GiB")
    print(f"   License: {model.license}")
    print(f"   Developer: {model.developer}")
    print()
    
    # Test get_model_info function
    print("[3/5] GPT-OSS-20B via get_model_info():")
    model = get_model_info("gpt-oss-20b")
    if model:
        print(f"   ✓ Retrieved model: {model.display_name}")
        print(f"   Architecture:")
        print(f"      • Layers: {model.architecture.layers}")
        print(f"      • Experts: {model.architecture.num_experts}")
        print(f"      • Top-K Experts: {model.architecture.top_k_experts}")
        print(f"      • Residual Dim: {model.architecture.residual_dim}")
        print(f"      • Query Heads: {model.architecture.num_query_heads}")
        print(f"      • KV Heads: {model.architecture.num_kv_heads}")
        print()
    
    # Test reasoning modes
    print("[4/5] Reasoning Modes:")
    for mode_spec in model.reasoning_modes:
        print(f"   • {mode_spec.mode.upper()}:")
        print(f"      Description: {mode_spec.description}")
        print(f"      Use Case: {mode_spec.use_case}")
        print(f"      Avg CoT Length: {mode_spec.avg_cot_length} tokens")
        print(f"      Relative Cost: {mode_spec.relative_cost}x")
    print()
    
    # Test performance benchmarks
    print("[5/5] Performance Benchmarks (Medium Reasoning):")
    for benchmark in model.benchmarks[:5]:  # Show first 5
        if benchmark.score_medium is not None:
            print(f"   • {benchmark.name}: {benchmark.score_medium:.1f}% ({benchmark.category})")
    print()
    
    # Test harmony format
    print("Harmony Format Configuration:")
    harmony = model.harmony_format
    print(f"   Roles: {', '.join(r for r in harmony.role_hierarchy)}")
    print(f"   Channels: {', '.join(c for c in harmony.channels)}")
    print()
    
    # Test tool capabilities
    print("Tool Capabilities:")
    for tool in model.tool_capabilities:
        print(f"   • {tool.tool_type.upper()}")
        funcs = ', '.join(tool.functions[:3])
        if len(tool.functions) > 3:
            funcs += f"... (+{len(tool.functions)-3} more)"
        print(f"      Functions: {funcs}")
    print()
    
    print("=" * 80)
    print("   ✓ Model Information Test Complete!")
    print("=" * 80)
    print()

if __name__ == "__main__":
    try:
        test_model_info()
        sys.exit(0)
    except Exception as e:
        print(f"   ✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
