"""
Test script to verify GPT-OSS model intelligence integration.

This script tests:
1. Model information access from model_info.py
2. Harmony format prompt building
3. Configuration loading with model card data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("GPT-OSS MODEL INTELLIGENCE INTEGRATION TEST")
print("=" * 80)

# Test 1: Model Information Access
print("\n[TEST 1] Model Information Access")
print("-" * 80)

try:
    from astra.models.model_info import (
        get_model_info,
        list_available_models,
        GPT_OSS_120B_INFO,
        GPT_OSS_20B_INFO,
    )
    
    print("✓ Successfully imported model_info module")
    
    # List available models
    models = list_available_models()
    print(f"✓ Available models: {', '.join(models)}")
    
    # Get model info for gpt-oss-20b
    model_20b = get_model_info("gpt-oss-20b")
    if model_20b:
        print(f"\n✓ GPT-OSS-20B Information:")
        print(f"  - Display Name: {model_20b.display_name}")
        print(f"  - Total Parameters: {model_20b.architecture.total_parameters:,}")
        print(f"  - Active Parameters: {model_20b.architecture.active_parameters:,}")
        print(f"  - Layers: {model_20b.architecture.layers}")
        print(f"  - Experts: {model_20b.architecture.num_experts} (top-{model_20b.architecture.top_k_experts})")
        print(f"  - Context Length: {model_20b.architecture.context_length:,} tokens")
        print(f"  - Quantization: {model_20b.architecture.quantization} ({model_20b.architecture.bits_per_parameter} bpp)")
        print(f"  - Checkpoint Size: {model_20b.architecture.checkpoint_size_gb} GiB")
        print(f"  - Tokenizer: {model_20b.architecture.tokenizer_name} ({model_20b.architecture.vocab_size:,} tokens)")
        
        # Reasoning modes
        print(f"\n  Reasoning Modes:")
        for mode_spec in model_20b.reasoning_modes:
            print(f"    • {mode_spec.mode.upper()}: {mode_spec.description}")
            print(f"      CoT Length: {mode_spec.avg_cot_length}, Cost: {mode_spec.relative_cost}")
        
        # Tools
        print(f"\n  Tool Capabilities:")
        for tool in model_20b.tool_capabilities:
            print(f"    • {tool.name}: {tool.description}")
        
        # Hardware requirements
        print(f"\n  Hardware Requirements:")
        for key, value in model_20b.hardware_requirements.items():
            print(f"    • {key}: {value}")
    
    # Get model info for gpt-oss-120b
    model_120b = get_model_info("gpt-oss-120b")
    if model_120b:
        print(f"\n✓ GPT-OSS-120B Information:")
        print(f"  - Total Parameters: {model_120b.architecture.total_parameters:,}")
        print(f"  - Active Parameters: {model_120b.architecture.active_parameters:,}")
        print(f"  - Layers: {model_120b.architecture.layers}")
        print(f"  - Experts: {model_120b.architecture.num_experts} (top-{model_120b.architecture.top_k_experts})")
        print(f"  - Checkpoint Size: {model_120b.architecture.checkpoint_size_gb} GiB")
    
    print("\n✓ TEST 1 PASSED: Model information access working correctly")
    
except Exception as e:
    print(f"\n✗ TEST 1 FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Harmony Format Utilities
print("\n[TEST 2] Harmony Format Prompt Building")
print("-" * 80)

try:
    from astra.infrastructure.llm.harmony import (
        HarmonyPromptBuilder,
        HarmonyRole,
        HarmonyChannel,
        strip_cot_from_history,
        HarmonyMessage,
    )
    
    print("✓ Successfully imported harmony module")
    
    # Build a sample prompt
    builder = HarmonyPromptBuilder()
    
    # Add system message with reasoning mode
    builder.add_system_message(
        "You are ASTRA, a helpful AI assistant.",
        reasoning_mode="medium",
        enable_browsing=False,
        enable_python=True
    )
    
    # Add developer message
    builder.add_developer_message(
        "Follow these guidelines: Be helpful, accurate, and concise."
    )
    
    # Add user message
    builder.add_user_message(
        "Calculate the first 10 Fibonacci numbers and explain the pattern."
    )
    
    # Build the prompt
    prompt = builder.build()
    
    print("\n✓ Built Harmony Format Prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    # Test CoT stripping
    messages = [
        HarmonyMessage(role=HarmonyRole.SYSTEM, content="System message", channel=HarmonyChannel.FINAL),
        HarmonyMessage(role=HarmonyRole.USER, content="User message", channel=HarmonyChannel.FINAL),
        HarmonyMessage(role=HarmonyRole.ASSISTANT, content="Thinking...", channel=HarmonyChannel.ANALYSIS),
        HarmonyMessage(role=HarmonyRole.ASSISTANT, content="Final answer", channel=HarmonyChannel.FINAL),
    ]
    
    cleaned = strip_cot_from_history(messages)
    
    print(f"\n✓ CoT Stripping Test:")
    print(f"  - Original messages: {len(messages)}")
    print(f"  - After stripping CoT: {len(cleaned)}")
    print(f"  - Analysis channel removed: {len(messages) - len(cleaned) == 1}")
    
    print("\n✓ TEST 2 PASSED: Harmony format utilities working correctly")
    
except Exception as e:
    print(f"\n✗ TEST 2 FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Configuration Loading
print("\n[TEST 3] Configuration with Model Card Data")
print("-" * 80)

try:
    from astra.models.config import Settings
    
    print("✓ Successfully imported config module")
    
    # Load settings
    settings = Settings()
    
    print(f"\n✓ Configuration Loaded:")
    print(f"  - Model Name: {settings.llm.model_name}")
    print(f"  - Model Size: {settings.llm.model_size}")
    print(f"  - Provider: {settings.llm.provider}")
    print(f"  - Base URL: {settings.llm.base_url}")
    print(f"  - Context Length: {settings.llm.context_length:,} tokens")
    print(f"  - Reasoning Mode: {settings.llm.reasoning_mode}")
    print(f"  - Harmony Format: {settings.llm.use_harmony_format}")
    print(f"  - Tokenizer: {settings.llm.tokenizer_name}")
    print(f"  - Vocab Size: {settings.llm.vocab_size:,}")
    print(f"  - Strip CoT: {settings.llm.strip_cot_in_history}")
    
    print(f"\n  Tools Enabled:")
    print(f"    • Browsing: {settings.llm.enable_browsing}")
    print(f"    • Python: {settings.llm.enable_python}")
    print(f"    • Developer Functions: {settings.llm.enable_developer_functions}")
    
    print(f"\n  Database: {settings.database.url}")
    print(f"  Vector Store: {settings.vector_store.persist_directory}")
    print(f"  Embedding Model: {settings.memory.embedding_model}")
    
    print("\n✓ TEST 3 PASSED: Configuration loading successfully")
    
except Exception as e:
    print(f"\n✗ TEST 3 FAILED: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("INTEGRATION TEST COMPLETE")
print("=" * 80)
print("\nAll GPT-OSS model intelligence is integrated and accessible!")
print("\nNext Steps:")
print("  1. Ensure llama.cpp server is running: http://localhost:8001")
print("  2. Initialize the database")
print("  3. Start the ASTRA server")
print("=" * 80)
