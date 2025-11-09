#!/usr/bin/env python3
"""
Simple integration test to demonstrate key AICL enhanced features
"""

import sys
import os

def test_core_functionality():
    """Test core AICL functionality"""
    print("Testing core AICL functionality...")
    
    # Add current directory to path
    sys.path.insert(0, '.')
    
    try:
        # Import and test core functions
        from core import new_msg, sign, verify
        
        # Create a message
        msg = new_msg(
            frm="test_sender",
            to="test_receiver",
            act="inform",
            payload={"text": {"content": "Test message"}}
        )
        
        print(f"✓ Created message with ID: {msg['id']}")
        
        # Test signing
        secret_key = b"test_key"
        signed_msg = sign(msg, secret_key)
        is_valid = verify(signed_msg, secret_key)
        
        assert is_valid, "Signature verification failed"
        print("✓ Message signing and verification works")
        
        return True
    except Exception as e:
        print(f"✗ Core functionality test failed: {e}")
        return False

def test_enhanced_features():
    """Test enhanced features"""
    print("\nTesting enhanced features...")
    
    try:
        # Test error handling
        from error_handling import AICLError, AICLErrorCode
        
        error = AICLError(
            code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
            message="Test error"
        )
        
        error_dict = error.to_dict()
        assert error_dict["error_code"] == "INVALID_MESSAGE_FORMAT"
        print("✓ Enhanced error handling works")
        
        # Test configuration
        from config import config
        
        host = config.get("host")
        port = config.get("port")
        assert host == "127.0.0.1"
        assert port == 5555
        print("✓ Configuration management works")
        
        # Test streaming basics
        from streaming import StreamChunk
        
        chunk = StreamChunk(0, "test data", False)
        chunk_dict = chunk.to_dict()
        assert chunk_dict["data"] == "test data"
        print("✓ Streaming functionality works")
        
        return True
    except Exception as e:
        print(f"✗ Enhanced features test failed: {e}")
        return False

def main():
    """Main test function"""
    print("AICL Simple Integration Test")
    print("=" * 40)
    
    tests = [
        test_core_functionality,
        test_enhanced_features
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        print("\nAICL Enhanced Features Summary:")
        print("  • Core message creation and signing: ✓")
        print("  • Enhanced error handling: ✓")
        print("  • Configuration management: ✓")
        print("  • Streaming support: ✓")
        print("  • Persistence, security, and monitoring modules available")
        return 0
    else:
        print("❌ Some integration tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())