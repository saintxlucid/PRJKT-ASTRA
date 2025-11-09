#!/usr/bin/env python3
"""
Final demonstration of all AICL enhanced features working together
"""

import sys
import time
from core import new_msg, sign, verify
from config import config
from error_handling import AICLError, AICLErrorCode
from persistence import MessageStore
from security import SecurityManager
from monitoring import AICLObserver
from streaming import split_large_content, create_stream_message

def demonstrate_integrated_features():
    """Demonstrate all enhanced features working together"""
    print("=== AICL Enhanced Features Integration Demo ===")
    
    # Initialize components
    secret_key = b"integration_demo_key"
    security_manager = SecurityManager(secret_key)
    message_store = MessageStore(":memory:")  # In-memory for demo
    observer = AICLObserver()
    
    try:
        # 1. Create and sign a message
        print("1. Creating and signing message...")
        msg = new_msg(
            frm="demo_sender",
            to="demo_receiver",
            act="inform",
            payload={
                "text": {
                    "content": "This is a demonstration of AICL enhanced features"
                }
            }
        )
        
        signed_msg = security_manager.sign_message(msg)
        print(f"   ✓ Message created and signed (sig: {signed_msg.get('sig', '')[:10]}...)")
        
        # Record metric
        observer.metrics_collector.record_metric("message_created", 1)
        
        # 2. Verify message signature
        print("2. Verifying message signature...")
        is_valid = security_manager.integrity.verify_signature(signed_msg, secret_key)
        assert is_valid, "Signature verification failed"
        print("   ✓ Message signature verified")
        
        # Record event
        observer.event_logger.log_event("signature_verified", "Message signature verified successfully")
        
        # 3. Store message
        print("3. Storing message...")
        store_result = message_store.store_message(signed_msg)
        assert store_result, "Message storage failed"
        print(f"   ✓ Message stored (ID: {signed_msg['id']})")
        
        # Record metric
        observer.metrics_collector.record_metric("message_stored", 1)
        
        # 4. Retrieve message
        print("4. Retrieving message...")
        retrieved_msg = message_store.get_message_by_id(signed_msg["id"])
        assert retrieved_msg is not None, "Message retrieval failed"
        print("   ✓ Message retrieved from storage")
        
        # Record event
        observer.event_logger.log_event("message_retrieved", "Message retrieved from storage")
        
        # 5. Update message status
        print("5. Updating message status...")
        update_result = message_store.update_message_status(signed_msg["id"], "processed")
        assert update_result, "Status update failed"
        print("   ✓ Message status updated to 'processed'")
        
        # Record metric
        observer.metrics_collector.record_metric("message_processed", 1)
        
        # 6. Demonstrate streaming for large content
        print("6. Demonstrating streaming for large content...")
        large_content = "A" * 2000  # 2KB of content
        chunks = split_large_content(large_content, chunk_size=500)
        stream_msg = create_stream_message("streamer", "receiver", "large_content", chunks)
        signed_stream_msg = security_manager.sign_message(stream_msg)
        print(f"   ✓ Streaming message created with {len(chunks)} chunks")
        
        # Record performance
        observer.performance_monitor.record_operation_timing("stream_message_create", 5.2, True)
        
        # 7. Configuration access
        print("7. Accessing configuration...")
        host = config.get("host")
        port = config.get("port")
        enable_streaming = config.get("enable_streaming")
        print(f"   ✓ Config - Host: {host}, Port: {port}, Streaming: {enable_streaming}")
        
        # Record metric
        observer.metrics_collector.record_metric("config_accessed", 1)
        
        # 8. Error handling demonstration
        print("8. Demonstrating error handling...")
        try:
            # Simulate an error condition
            raise AICLError(
                code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
                message="Demo error for testing",
                details={"test_field": "test_value"}
            )
        except AICLError as e:
            error_dict = e.to_dict()
            print(f"   ✓ Error handled - Code: {error_dict['error_code']}, Message: {error_dict['message']}")
            
            # Record event
            observer.event_logger.log_event("error_handled", "Demo error handled successfully", "info", error_dict)
        
        # 9. Monitoring and metrics
        print("9. Collecting monitoring data...")
        # Record some metrics
        observer.metrics_collector.record_metric("demo_operation", 42, {"type": "test"})
        observer.metrics_collector.record_metric("demo_duration", 15.7, {"unit": "ms"})
        
        # Record performance
        observer.performance_monitor.record_operation_timing("demo_operation", 15.7, True)
        
        # Log events
        observer.event_logger.log_event("demo_started", "Demo started successfully")
        observer.event_logger.log_event("demo_completed", "Demo completed successfully")
        
        # Get system status
        status = observer.get_system_status()
        print(f"   ✓ System status collected - Health: {status['health']['overall_status']}")
        print(f"   ✓ Metrics collected: {len(status['metrics_summary'])} metrics")
        print(f"   ✓ Events logged: {len(status['recent_events'])} recent events")
        
        # 10. Summary statistics
        print("10. Generating summary...")
        metrics_summary = observer.metrics_collector.get_metrics_summary()
        performance_stats = observer.performance_monitor.get_all_performance_stats()
        
        print(f"    Metrics Summary:")
        for name, data in list(metrics_summary.items())[:3]:  # Show first 3 metrics
            print(f"      {name}: {data['latest_value']}")
            
        print(f"    Performance Stats:")
        for name, stats in list(performance_stats.items())[:2]:  # Show first 2 operations
            print(f"      {name}: {stats['success_count']}/{stats['total_count']} success")
        
        print("\n🎉 All AICL enhanced features demonstrated successfully!")
        print("✅ Integration test passed - all components working together")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        return False

def main():
    """Main function"""
    print("AICL Enhanced Features Integration Demonstration")
    print("=" * 60)
    
    start_time = time.time()
    success = demonstrate_integrated_features()
    end_time = time.time()
    
    duration = end_time - start_time
    print("=" * 60)
    print(f"Demo completed in {duration:.2f} seconds")
    
    if success:
        print("🎉 Integration demonstration completed successfully!")
        print("\nAICL is now fully enhanced with:")
        print("  • Enhanced error handling")
        print("  • Message persistence and recovery")
        print("  • Advanced security features")
        print("  • Comprehensive monitoring")
        print("  • Configuration management")
        print("  • Streaming support")
        print("  • And much more...")
        return 0
    else:
        print("❌ Integration demonstration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())