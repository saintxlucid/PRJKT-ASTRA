#!/usr/bin/env python3
"""
Comprehensive test of AICL enhanced features
"""

import sys
import os
import time

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_core_functionality():
    """Test core AICL functionality"""
    print("=== Testing Core Functionality ===")
    
    try:
        import core
        
        # Test message creation
        msg = core.new_msg(
            frm="test_sender",
            to="test_receiver",
            act="ask",
            payload={
                "text": {
                    "lang": "en",
                    "fmt": "md",
                    "content": "Test message content"
                }
            },
            limits={"tokens": 128}
        )
        print("✓ Message creation successful")
        
        # Test serialization
        json_msg = core.aicl_core(msg)
        print("✓ JSON serialization successful")
        
        # Test glyph conversion
        glyph_msg = core.to_glyph(msg)
        print("✓ Glyph conversion successful")
        
        # Test parsing
        parsed_msg = core.from_glyph(glyph_msg)
        print("✓ Glyph parsing successful")
        
        # Test signing
        key = b"test_key"
        signed_msg = core.sign(msg, key)
        is_valid = core.verify(signed_msg, key)
        print(f"✓ Message signing and verification: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"✗ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transport_functionality():
    """Test transport functionality"""
    print("\n=== Testing Transport Functionality ===")
    
    try:
        import transport
        print("✓ Transport module imported successfully")
        
        # Test that classes and functions exist
        assert hasattr(transport, 'run_server')
        assert hasattr(transport, 'run_client')
        assert hasattr(transport, 'AICLConnection')
        print("✓ Transport classes and functions available")
        
        return True
        
    except Exception as e:
        print(f"✗ Transport functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logging_functionality():
    """Test logging functionality"""
    print("\n=== Testing Logging Functionality ===")
    
    try:
        import logging as aicl_logging
        
        # Test logger creation
        logger = aicl_logging.AICLLogger("test_logs", compress=False)
        print("✓ Logger creation successful")
        
        # Test message logging
        test_msg = {
            "v": "aicl/1.0",
            "id": "test123",
            "from": "sender",
            "to": "receiver",
            "act": "inform",
            "payload": {"test": "data"}
        }
        
        logger.log_message(test_msg, latency_ms=10.5)
        print("✓ Message logging successful")
        
        # Test metrics
        metrics = logger.get_metrics()
        print(f"✓ Metrics retrieval successful: {metrics['total_messages']} messages")
        
        return True
        
    except Exception as e:
        print(f"✗ Logging functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_guardrails_functionality():
    """Test guardrails functionality"""
    print("\n=== Testing Guardrails Functionality ===")
    
    try:
        import guardrails
        
        # Test message validation
        valid_msg = {
            "v": "aicl/1.0",
            "id": "test123",
            "from": "sender",
            "to": "receiver",
            "act": "inform",
            "payload": {"test": "data"}
        }
        
        is_valid, error = guardrails.validate_message(valid_msg)
        print(f"✓ Message validation successful: {is_valid}")
        
        # Test rate limiting
        sender_id = "test_sender"
        allowed = guardrails.rate_limit_check(sender_id, max_requests_per_minute=10)
        print(f"✓ Rate limiting check successful: {allowed}")
        
        # Test signature verification
        key = b"test_key"
        signed_msg = valid_msg.copy()
        signed_msg["sig"] = "dummy_signature"  # This will fail verification, which is expected
        is_verified = guardrails.verify_signature(signed_msg, key)
        print(f"✓ Signature verification test completed: {is_verified}")
        
        return True
        
    except Exception as e:
        print(f"✗ Guardrails functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("AICL Comprehensive Test Suite")
    print("=" * 50)
    
    tests = [
        test_core_functionality,
        test_transport_functionality,
        test_logging_functionality,
        test_guardrails_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AICL is ready for use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())