#!/usr/bin/env python3
"""
Demonstration of AICL enhanced features
"""

import sys
import os

def demonstrate_core_features():
    """Demonstrate core AICL features"""
    print("=== Core AICL Features ===")
    
    # Add current directory to path
    sys.path.insert(0, '.')
    
    try:
        # Import core module
        from core import new_msg, new_stream_msg, new_error_msg, new_ping_msg, new_pong_msg
        from core import get_message_type, get_message_topic, is_request_message, is_response_message
        from core import sign, verify
        
        # Create different message types
        basic_msg = new_msg(
            frm="sender", 
            to="receiver", 
            act="inform", 
            payload={"text": {"content": "Hello World"}}
        )
        
        stream_msg = new_stream_msg("sender", "receiver", "test_topic", [])
        error_msg = new_error_msg("sender", "receiver", "Test error")
        ping_msg = new_ping_msg("sender", "receiver")
        pong_msg = new_pong_msg("sender", "receiver", "ping123")
        
        print("✓ Message creation functions work")
        
        # Test utility functions
        assert get_message_type(stream_msg) == "stream"
        assert get_message_topic(stream_msg) == "test_topic"
        assert is_request_message(ping_msg) == True
        assert is_response_message(pong_msg) == True
        
        print("✓ Message utility functions work")
        
        # Test signing
        secret_key = b"test_key"
        signed_msg = sign(basic_msg, secret_key)
        assert verify(signed_msg, secret_key) == True
        
        print("✓ Message signing and verification work")
        
        return True
    except Exception as e:
        print(f"✗ Core features demonstration failed: {e}")
        return False

def demonstrate_config():
    """Demonstrate configuration management"""
    print("\n=== Configuration Management ===")
    
    try:
        from config import config
        
        # Test configuration access
        host = config.get("host")
        port = config.get("port")
        assert host == "127.0.0.1"
        assert port == 5555
        
        print("✓ Configuration access works")
        
        # Test configuration modification
        config.set("demo_key", "demo_value")
        assert config.get("demo_key") == "demo_value"
        
        print("✓ Configuration modification works")
        
        return True
    except Exception as e:
        print(f"✗ Configuration demonstration failed: {e}")
        return False

def demonstrate_enhanced_features():
    """Demonstrate enhanced features"""
    print("\n=== Enhanced Features ===")
    
    try:
        # Test error handling
        from error_handling import AICLError, AICLErrorCode
        
        error = AICLError(
            code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
            message="Test error"
        )
        
        error_dict = error.to_dict()
        assert "error_code" in error_dict
        assert error_dict["error_code"] == "INVALID_MESSAGE_FORMAT"
        
        print("✓ Enhanced error handling works")
        
        # Test streaming
        from streaming import StreamChunk, split_large_content
        
        content = "A" * 1000
        chunks = split_large_content(content, chunk_size=250)
        assert len(chunks) == 4
        
        print("✓ Streaming functionality works")
        
        # Test routing
        from routing import MessageRouter
        
        router = MessageRouter()
        
        def test_handler(msg):
            return []
            
        router.add_route("test_topic", test_handler)
        
        print("✓ Routing functionality works")
        
        # Test benchmarking
        from benchmark import BenchmarkResult
        
        result = BenchmarkResult("test")
        result.add_latency(10.5)
        result.add_success()
        
        summary = result.summary()
        assert summary["name"] == "test"
        assert summary["successful_operations"] == 1
        
        print("✓ Benchmarking functionality works")
        
        return True
    except Exception as e:
        print(f"✗ Enhanced features demonstration failed: {e}")
        return False

def main():
    """Run demonstration"""
    print("AICL Enhanced Features Demonstration")
    print("=" * 50)
    
    tests = [
        demonstrate_core_features,
        demonstrate_config,
        demonstrate_enhanced_features
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"Demonstration Results: {passed}/{total} sections passed")
    
    if passed == total:
        print("🎉 All demonstrations completed successfully!")
        print("AICL is fully enhanced with production-ready features.")
        return 0
    else:
        print("❌ Some demonstrations failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())