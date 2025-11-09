#!/usr/bin/env python3
"""
Comprehensive AICL example demonstrating all advanced features:
- Configuration management
- Streaming support
- Compression for large payloads
- Routing and broker system
- Async support
- Benchmarking
- Advanced error handling
"""

import time
import asyncio
import threading
from typing import List, Dict

# Import AICL modules
from .core import (
    new_msg, 
    new_stream_msg, 
    new_error_msg, 
    aicl_core, 
    sign, 
    verify
)
from .transport import run_server, run_client, AICLConnection
from .aicl_logging import AICLLogger, AICLReplayer
from .guardrails import validate_message, rate_limit_check
from .config import config
from .streaming import create_stream_message, split_large_content, StreamChunk
from .routing import router, broker
from .benchmark import AICLBenchmark, AsyncAICLBenchmark

# Configuration
SECRET_KEY = b"super_secret_key_for_demo"

def teacher_handler(msg: Dict) -> List[Dict]:
    """Handle messages on the teacher side"""
    print(f"[Teacher] Received: {msg.get('act')} from {msg.get('from')}")
    
    # Validate incoming message
    is_valid, error = validate_message(msg)
    if not is_valid:
        print(f"[Teacher] Invalid message: {error}")
        return [new_error_msg("teacher", msg.get("from", "unknown"), str(error) if error else "Validation failed")]
    
    # Check rate limiting
    sender = msg.get("from", "unknown")
    if not rate_limit_check(sender, max_requests_per_minute=10):
        print(f"[Teacher] Rate limit exceeded for {sender}")
        return [new_error_msg("teacher", sender, "Rate limit exceeded")]
    
    act = msg.get("act")
    
    if act == "inform":  # Capabilities exchange
        print("[Teacher] Sending ACK")
        return [new_msg("teacher", sender, "ack", payload={"ok": True})]
        
    elif act == "ask":
        # Process student request
        content = msg["payload"]["text"]["content"]
        print(f"[Teacher] Processing request: {content[:50]}...")
        
        # Simulate some processing time
        time.sleep(0.1)
        
        # For large content, use streaming
        if len(content) > 500:
            # Split content into chunks
            chunks = split_large_content(content, chunk_size=200)
            # Create stream message directly with StreamChunk objects
            stream_msg = create_stream_message(
                frm="teacher",
                to=sender,
                topic="large_response",
                chunks=chunks,
                ctx=msg.get("ctx", {})
            )
            # Sign the response
            stream_msg = sign(stream_msg, SECRET_KEY)
            return [stream_msg]
        else:
            # Create response with logits for knowledge distillation
            response = new_msg(
                frm="teacher", 
                to=sender, 
                act="answer",
                payload={
                    "text": {
                        "lang": "en",
                        "fmt": "md",
                        "content": f"Teacher response to: {content[:100]}..."
                    },
                    "logits": {
                        "temperature": 2.0,
                        "topk": [
                            {"tok": "distillation", "p": 0.35},
                            {"tok": "compression", "p": 0.25},
                            {"tok": "transfer", "p": 0.15},
                            {"tok": "learning", "p": 0.12},
                            {"tok": "model", "p": 0.10}
                        ]
                    }
                },
                ctx=msg.get("ctx", {}),
                limits={"tokens": 256}
            )
            
            # Sign the response
            response = sign(response, SECRET_KEY)
            return [response]
        
    elif act == "ping":
        # Respond to ping
        return [new_msg(
            frm="teacher",
            to=sender,
            act="pong",
            payload={},
            ctx={"ping_id": msg.get("id")}
        )]
        
    return []

def student_handler(msg: Dict) -> List[Dict]:
    """Handle messages on the student side"""
    print(f"[Student] Received: {msg.get('act')} from {msg.get('from')}")
    
    # Validate incoming message
    is_valid, error = validate_message(msg)
    if not is_valid:
        print(f"[Student] Invalid message: {error}")
        return [new_error_msg("student", msg.get("from", "unknown"), str(error) if error else "Validation failed")]
    
    # Verify signature if present
    if "sig" in msg:
        if verify(msg, SECRET_KEY):
            print("[Student] Message signature verified")
        else:
            print("[Student] WARNING: Message signature invalid!")
    
    act = msg.get("act")
    
    if act == "inform":  # Capabilities exchange
        print("[Student] Sending ACK")
        return [new_msg("student", msg["from"], "ack", payload={"ok": True})]
        
    elif act == "answer":
        # Process teacher response
        content = msg["payload"]["text"]["content"]
        print(f"[Student] Received response: {content[:50]}...")
        
        # If logits are present, this could be used for knowledge distillation
        if "logits" in msg["payload"]:
            logits = msg["payload"]["logits"]
            print(f"[Student] Received logits (temperature={logits['temperature']})")
        
        # Create follow-up question
        followup = new_msg(
            frm="student",
            to="teacher",
            act="ask",
            payload={
                "text": {
                    "lang": "en",
                    "fmt": "md",
                    "content": "Can you explain more about knowledge distillation?"
                }
            },
            ctx={"turn": msg.get("ctx", {}).get("turn", 0) + 1},
            limits={"tokens": 128}
        )
        
        return [followup]
        
    elif act == "stream":
        # Handle streaming message
        chunks = msg["payload"]["chunks"]
        print(f"[Student] Received stream with {len(chunks)} chunks")
        # In a real implementation, you would reconstruct the content
        return []
        
    elif act == "pong":
        # Handle pong response
        print(f"[Student] Received pong for ping {msg.get('ctx', {}).get('ping_id')}")
        return []
        
    return []

def run_teacher_server():
    """Run the teacher server"""
    print("[Teacher] Starting server on port 5555...")
    run_server(
        config.get("host"),
        5555,
        teacher_handler,
        use_tls=config.get("use_tls"),
        max_connections=config.get("max_connections")
    )

def run_student_server():
    """Run the student server"""
    print("[Student] Starting server on port 5556...")
    run_server(
        config.get("host"),
        5556,
        student_handler,
        use_tls=config.get("use_tls"),
        max_connections=config.get("max_connections")
    )

def run_demo_client():
    """Run the demo client that initiates the conversation"""
    print("[Client] Starting demo conversation...")
    
    # Create logger
    logger = AICLLogger(config.get("log_dir"), compress=config.get("compress_logs"))
    
    # Initial handshake message
    hello = new_msg(
        frm="client", 
        to="teacher", 
        act="inform",
        payload={
            "caps": ["text", "logits:topk"],
            "max_ctx": 4096
        }
    )
    
    # Log the message
    logger.log_message(hello)
    
    # Send message
    try:
        responses = list(run_client("127.0.0.1", 5555, [hello]))
        for response in responses:
            print(f"[Client] Received: {response}")
            logger.log_message(response)
    except Exception as e:
        print(f"[Client] Error: {e}")

async def run_async_demo():
    """Run async demo"""
    print("[Async] Starting async demo...")
    
    # This would require implementing the async transport
    # For now, we'll just simulate async operations
    benchmark = AsyncAICLBenchmark()
    result = await benchmark.benchmark_async_operations(100)
    print(f"[Async] Benchmark result: {result.summary()}")

def run_benchmarks():
    """Run performance benchmarks"""
    print("Running benchmarks...")
    
    benchmark = AICLBenchmark()
    
    # Benchmark message processing
    result1 = benchmark.benchmark_message_processing(1000, 512)
    print(f"Message processing benchmark: {result1.summary()}")
    
    # Benchmark concurrent connections
    result2 = benchmark.benchmark_concurrent_connections(5, 50)
    print(f"Concurrent connections benchmark: {result2.summary()}")

def main():
    """Main function to run the comprehensive example"""
    print("=== AICL Comprehensive Example ===")
    
    # Show configuration
    print(f"Configuration: host={config.get('host')}, port={config.get('port')}")
    
    # Start servers in separate threads
    teacher_thread = threading.Thread(target=run_teacher_server, daemon=True)
    student_thread = threading.Thread(target=run_student_server, daemon=True)
    
    teacher_thread.start()
    student_thread.start()
    
    # Wait a moment for servers to start
    time.sleep(1)
    
    # Run the demo client
    run_demo_client()
    
    # Run benchmarks
    run_benchmarks()
    
    # Run async demo
    asyncio.run(run_async_demo())
    
    # Wait a bit for conversation to complete
    time.sleep(2)
    
    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()