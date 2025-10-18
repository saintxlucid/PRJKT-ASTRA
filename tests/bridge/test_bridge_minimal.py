"""
ASTRA Bridge Tests
Minimal smoke tests for bridge module.
"""
from time import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.astra.bridge.config import BridgeConfig
from src.astra.bridge.schemas import BridgeEvent
from src.astra.bridge.interpreter import interpret
from src.astra.bridge.memory_bridge import MemoryBridgeService
from src.astra.bridge.tool_bridge import ToolBridgeService
from src.astra.bridge.router import route


def test_min_flow():
    """Test minimal bridge flow: event → interpret → route."""
    print("Testing minimal bridge flow...")
    
    cfg = BridgeConfig()
    ev = BridgeEvent(
        text="open the bridge and carry Saint Lucid's vow from the old archive",
        ts=time(),
        quote_raw=True
    )
    
    # Interpret
    payload = interpret(ev, cfg)
    assert "safe_text" in payload
    assert "patterns" in payload
    assert "intents" in payload
    assert "facts" in payload
    print(f"✓ Interpretation complete: {len(payload['patterns'])} patterns, {len(payload['intents'])} intents, {len(payload['facts'])} facts")
    
    # Route
    mem = MemoryBridgeService()
    tools = ToolBridgeService()
    res = route(payload, cfg, mem, tools)
    
    assert res.metrics["intents"] >= 0
    assert res.metrics["facts"] >= 0
    print(f"✓ Routing complete: {len(res.writes)} writes, {len(res.tool_calls)} tool calls")
    
    print("✓ All tests passed!\n")


def test_pattern_matching():
    """Test pattern matching against bridge language."""
    print("Testing pattern matching...")
    
    from src.astra.bridge.interpreter import pattern_pass
    
    test_cases = [
        ("open the bridge", True),
        ("carry the vow", True),
        ("random text", False),
        ("Saint Lucid's archive", True),
        ("code 333", True),
    ]
    
    for text, should_match in test_cases:
        result = pattern_pass(text)
        matched = len(result["patterns"]) > 0
        assert matched == should_match, f"Failed for: {text}"
        print(f"  ✓ '{text}': {'matched' if matched else 'no match'}")
    
    print("✓ Pattern matching tests passed!\n")


def test_safety_redaction():
    """Test safety redaction patterns."""
    print("Testing safety redaction...")
    
    from src.astra.bridge.safety import redact
    
    test_cases = [
        ("my api key is sk-abc123def456ghi789jkl", "sk-********"),
        ("card 1234-5678-9012-3456", "<card>"),
        ("normal text", "normal text"),
        ("hex value 0x1a2b3c4d5e6f7890abcdef", "<hex>"),
    ]
    
    for text, expected_pattern in test_cases:
        result = redact(text)
        assert expected_pattern in result, f"Failed redaction for: {text}\nGot: {result}"
        print(f"  ✓ Redacted: '{text}' → '{result}'")
    
    print("✓ Safety redaction tests passed!\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ASTRA BRIDGE MODULE - TEST SUITE")
    print("="*60 + "\n")
    
    try:
        test_pattern_matching()
        test_safety_redaction()
        test_min_flow()
        
        print("="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
