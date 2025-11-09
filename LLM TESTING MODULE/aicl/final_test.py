#!/usr/bin/env python3
"""
Final test to verify all AICL enhancements work correctly
"""

import sys
import os

def test_core_enhancements():
    """Test core module enhancements"""
    print("=== Testing Core Enhancements ===")
    
    try:
        # Use relative imports
        from core import (
            new_msg, new_stream_msg, new_error_msg, new_ping_msg, new_pong_msg,
            get_message_type, get_message_topic, is_request_message, is_response_message
        )
        
        # Test new message types
        stream_msg = new_stream_msg("sender", "receiver", "test_topic", [])
        error_msg = new_error_msg("sender", "receiver", "test error")
        ping_msg = new_ping_msg("sender", "receiver")
        pong_msg = new_pong_msg("sender", "receiver", "ping123")
        
        print("✓ All new message types created successfully")
        
        # Test utility functions
        assert get_message_type(stream_msg) == "stream"
        assert get_message_topic(stream_msg) == "test_topic"
        assert is_request_message(ping_msg) == True
        assert is_response_message(pong_msg) == True
        
        print("✓ Message utility functions work correctly")
        
        return True
    except Exception as e:
        print(f"✗ Core enhancements test failed: {e}")
        return False

def test_config_management():
    """Test configuration management"""
    print("\n=== Testing Configuration Management ===")
    
    try:
        from config import config
        # Note: AICLConfig is the class, config is the instance
        
        # Test default configuration
        host = config.get("host")
        port = config.get("port")
        assert host == "127.0.0.1"
        assert port == 5555
        
        print("✓ Default configuration loaded correctly")
        
        # Test configuration modification
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"
        
        print("✓ Configuration modification works")
        
        return True
    except Exception as e:
        print(f"✗ Configuration management test failed: {e}")
        return False

def test_streaming():
    """Test streaming functionality"""
    print("\n=== Testing Streaming Functionality ===")
    
    try:
        # Use relative imports
        from streaming import StreamChunk, split_large_content, create_stream_message
        
        # Test StreamChunk
        chunk = StreamChunk(0, "test data", False)
        chunk_dict = chunk.to_dict()
        reconstructed = StreamChunk.from_dict(chunk_dict)
        
        assert reconstructed.sequence == 0
        assert reconstructed.data == "test data"
        assert reconstructed.final == False
        
        print("✓ StreamChunk works correctly")
        
        # Test content splitting
        large_content = "A" * 1000
        chunks = split_large_content(large_content, chunk_size=250)
        assert len(chunks) == 4
        
        print("✓ Content splitting works correctly")
        
        # Test stream message creation
        stream_msg = create_stream_message("sender", "receiver", "test", chunks)
        assert stream_msg["act"] == "stream"
        assert len(stream_msg["payload"]["chunks"]) == 4
        
        print("✓ Stream message creation works correctly")
        
        return True
    except Exception as e:
        print(f"✗ Streaming test failed: {e}")
        return False

def test_routing():
    """Test routing functionality"""
    print("\n=== Testing Routing Functionality ===")
    
    try:
        # Use relative imports
        from routing import router, broker, MessageRouter, MessageBroker
        
        # Test router creation
        test_router = MessageRouter()
        test_broker = MessageBroker()
        
        print("✓ Router and broker creation works")
        
        # Test route addition
        def test_handler(msg):
            return []
            
        test_router.add_route("test_topic", test_handler)
        test_router.add_pattern_route(r"test_.*", test_handler)
        
        print("✓ Route addition works")
        
        return True
    except Exception as e:
        print(f"✗ Routing test failed: {e}")
        return False

def test_benchmarking():
    """Test benchmarking functionality"""
    print("\n=== Testing Benchmarking Functionality ===")
    
    try:
        # Use relative imports
        from benchmark import AICLBenchmark, AsyncAICLBenchmark, BenchmarkResult
        
        # Test benchmark result creation
        result = BenchmarkResult("test")
        result.add_latency(10.5)
        result.add_throughput(100.0)
        result.add_success()
        
        summary = result.summary()
        assert summary["name"] == "test"
        assert summary["successful_operations"] == 1
        
        print("✓ Benchmark result handling works")
        
        # Test benchmark creation
        benchmark = AICLBenchmark()
        assert hasattr(benchmark, "results")
        
        async_benchmark = AsyncAICLBenchmark()
        assert hasattr(async_benchmark, "benchmark_async_operations")
        
        print("✓ Benchmark creation works")
        
        return True
    except Exception as e:
        print(f"✗ Benchmarking test failed: {e}")
        return False

def test_error_handling():
    """Test enhanced error handling"""
    print("\n=== Testing Error Handling ===")
    
    try:
        from error_handling import AICLError, AICLErrorCode, AICLValidationError
        
        # Test error creation
        error = AICLError(
            code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
            message="Test error message",
            details={"field": "test_field"}
        )
        
        assert error.code == AICLErrorCode.INVALID_MESSAGE_FORMAT
        assert error.message == "Test error message"
        assert error.details["field"] == "test_field"
        
        print("✓ AICLError creation works")
        
        # Test error serialization
        error_dict = error.to_dict()
        reconstructed = AICLError.from_dict(error_dict)
        
        assert reconstructed.code == error.code
        assert reconstructed.message == error.message
        
        print("✓ Error serialization works")
        
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def test_persistence():
    """Test message persistence"""
    print("\n=== Testing Message Persistence ===")
    
    try:
        from persistence import MessageStore, MessageRecovery
        
        # Create message store
        store = MessageStore(":memory:")  # Use in-memory database for testing
        
        # Test message storage
        from core import new_msg
        msg = new_msg(
            frm="test_sender",
            to="test_receiver",
            act="inform",
            payload={"test": "data"}
        )
        
        assert store.store_message(msg) == True
        print("✓ Message storage works")
        
        # Test message retrieval
        retrieved = store.get_message_by_id(msg["id"])
        assert retrieved is not None
        assert retrieved["id"] == msg["id"]
        print("✓ Message retrieval works")
        
        # Test message status update
        assert store.update_message_status(msg["id"], "processed") == True
        print("✓ Message status update works")
        
        return True
    except Exception as e:
        print(f"✗ Persistence test failed: {e}")
        return False

def test_security():
    """Test security features"""
    print("\n=== Testing Security Features ===")
    
    try:
        from security import SecurityManager, MessageIntegrity
        
        # Create security manager
        secret_key = b"test_secret_key"
        security = SecurityManager(secret_key)
        
        # Test message signing
        from core import new_msg
        msg = new_msg(
            frm="sender",
            to="receiver",
            act="inform",
            payload={"test": "data"}
        )
        
        signed_msg = security.sign_message(msg)
        assert "sig" in signed_msg
        print("✓ Message signing works")
        
        # Test signature verification
        assert security.integrity.verify_signature(signed_msg, secret_key) == True
        print("✓ Message signature verification works")
        
        return True
    except Exception as e:
        print(f"✗ Security test failed: {e}")
        return False

def test_monitoring():
    """Test monitoring features"""
    print("\n=== Testing Monitoring Features ===")
    
    try:
        from monitoring import AICLObserver, MetricsCollector
        
        # Create observer
        observer = AICLObserver()
        
        # Test metric recording
        observer.metrics_collector.record_metric("test_metric", 42, {"tag": "value"})
        metrics = observer.metrics_collector.get_metrics("test_metric")
        assert len(metrics) == 1
        assert metrics[0].value == 42
        print("✓ Metric recording works")
        
        # Test event logging
        observer.event_logger.log_event("test_event", "Test message", "info")
        events = observer.event_logger.get_events("test_event")
        assert len(events) == 1
        assert events[0]["message"] == "Test message"
        print("✓ Event logging works")
        
        # Test performance monitoring
        observer.performance_monitor.record_operation_timing("test_op", 15.5, True)
        stats = observer.performance_monitor.get_performance_stats("test_op")
        assert stats["total_count"] == 1
        assert stats["success_count"] == 1
        print("✓ Performance monitoring works")
        
        return True
    except Exception as e:
        print(f"✗ Monitoring test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("AICL Final Enhancement Test Suite")
    print("=" * 50)
    
    tests = [
        test_core_enhancements,
        test_config_management,
        test_streaming,
        test_routing,
        test_benchmarking,
        test_error_handling,
        test_persistence,
        test_security,
        test_monitoring
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
        print("🎉 All enhancement tests passed! AICL is fully enhanced.")
        return 0
    else:
        print("❌ Some enhancement tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())