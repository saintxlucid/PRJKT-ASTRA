"""
Test Harmony Format Utilities

This script tests the Harmony chat format utilities for GPT-OSS models,
including prompt building, message parsing, and format conversion.

Usage:
    python scripts/test_harmony.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from src.astra.infrastructure.llm.harmony import (
    HarmonyPromptBuilder,
    HarmonyMessage,
    HarmonyRole,
    HarmonyChannel,
    strip_cot_from_history,
    parse_harmony_response,
    extract_final_response,
    extract_cot,
    convert_to_openai_format
)
from src.astra.models.model_info import ReasoningMode

def test_harmony_format():
    """Test Harmony format utilities."""
    
    print("=" * 80)
    print("   Harmony Format Utilities Test")
    print("=" * 80)
    print()
    
    # Test 1: Build a basic prompt
    print("[1/5] Building Basic Prompt:")
    builder = HarmonyPromptBuilder()
    builder.add_system_message(
        "You are a helpful AI assistant.",
        reasoning_mode=ReasoningMode.MEDIUM,
        enable_browsing=False,
        enable_python=True
    )
    builder.add_user_message("What is the capital of France?")
    
    prompt = builder.build()
    print(prompt)
    print()
    
    # Test 2: Build a multi-turn conversation
    print("[2/5] Building Multi-Turn Conversation:")
    builder = HarmonyPromptBuilder()
    builder.add_system_message(
        "You are a coding assistant.",
        reasoning_mode=ReasoningMode.HIGH,
        enable_python=True,
        enable_developer_functions=True
    )
    builder.add_user_message("Write a Python function to calculate fibonacci numbers.")
    builder.add_assistant_message(
        "Let me think about the most efficient approach...",
        channel=HarmonyChannel.ANALYSIS
    )
    builder.add_assistant_message(
        "I'll use dynamic programming for O(n) time complexity.",
        channel=HarmonyChannel.COMMENTARY
    )
    builder.add_assistant_message(
        "Here's the function:\n```python\ndef fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)\n```",
        channel=HarmonyChannel.FINAL
    )
    builder.add_user_message("Can you optimize it?")
    
    prompt = builder.build()
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    print()
    
    # Test 3: Parse harmony response
    print("[3/5] Parsing Harmony Response:")
    response_text = """<|start_header_id|>assistant|analysis<|end_header_id|>

Let me analyze this problem step by step.

<|start_header_id|>assistant|commentary<|end_header_id|>

I'll use memoization for better performance.

<|start_header_id|>assistant|final<|end_header_id|>

Here's the optimized version:
```python
def fib(n, memo={}):
    if n in memo: return memo[n]
    if n <= 1: return n
    memo[n] = fib(n-1, memo) + fib(n-2, memo)
    return memo[n]
```"""
    
    messages = parse_harmony_response(response_text)
    print(f"   Parsed {len(messages)} messages:")
    for msg in messages:
        content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        print(f"   • {msg.role.value}|{msg.channel.value if msg.channel else 'none'}: {content_preview}")
    print()
    
    # Test 4: Extract final response
    print("[4/5] Extracting Final Response:")
    final = extract_final_response(messages)
    if final:
        print(f"   Final response length: {len(final)} characters")
        print(f"   Preview: {final[:100]}...")
    print()
    
    # Test 5: Convert to OpenAI format
    print("[5/5] Converting to OpenAI Format:")
    
    # Create a conversation with CoT
    conversation = [
        HarmonyMessage(
            role=HarmonyRole.SYSTEM,
            content="You are a helpful assistant.",
            channel=None
        ),
        HarmonyMessage(
            role=HarmonyRole.USER,
            content="What is 2+2?",
            channel=None
        ),
        HarmonyMessage(
            role=HarmonyRole.ASSISTANT,
            content="Let me think...",
            channel=HarmonyChannel.ANALYSIS
        ),
        HarmonyMessage(
            role=HarmonyRole.ASSISTANT,
            content="This is basic arithmetic.",
            channel=HarmonyChannel.COMMENTARY
        ),
        HarmonyMessage(
            role=HarmonyRole.ASSISTANT,
            content="2 + 2 = 4",
            channel=HarmonyChannel.FINAL
        )
    ]
    
    # Convert with CoT
    openai_with_cot = convert_to_openai_format(conversation, include_cot=True)
    print(f"   With CoT: {len(openai_with_cot)} messages")
    for msg in openai_with_cot:
        print(f"      • {msg['role']}: {msg['content'][:50]}...")
    print()
    
    # Convert without CoT
    openai_without_cot = convert_to_openai_format(conversation, include_cot=False)
    print(f"   Without CoT: {len(openai_without_cot)} messages")
    for msg in openai_without_cot:
        print(f"      • {msg['role']}: {msg['content'][:50]}...")
    print()
    
    # Test strip_cot_from_history
    print("Strip CoT from History:")
    stripped = strip_cot_from_history(conversation)
    print(f"   Original: {len(conversation)} messages")
    print(f"   Stripped: {len(stripped)} messages")
    print()
    
    print("=" * 80)
    print("   ✓ Harmony Format Test Complete!")
    print("=" * 80)
    print()

if __name__ == "__main__":
    try:
        test_harmony_format()
        sys.exit(0)
    except Exception as e:
        print(f"   ✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
