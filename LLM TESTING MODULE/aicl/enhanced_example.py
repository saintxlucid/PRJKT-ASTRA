#!/usr/bin/env python3
"""
Enhanced AICL example demonstrating advanced features:
- Secure message signing
- Rate limiting
- Comprehensive logging
- Metrics tracking
- Error handling
"""

import time
import threading
from core import new_msg, aicl_core, sign, verify
from transport import run_server, run_client
from aicl_logging import AICLLogger
from guardrails import validate_message, rate_limit_check

# Secret key for message signing
SECRET_KEY = b"super_secret_key_for_demo"

def teacher_handler(msg):
    """Handle messages on the teacher side"""
    print(f"[Teacher] Received: {msg.get('act')} from {msg.get('from')}")
    
    # Validate incoming message
    is_valid, error = validate_message(msg)
    if not is_valid:
        print(f"[Teacher] Invalid message: {error}")
        return [{
            "v": "aicl/1.0",
            "id": "validation_error",
            "from": "teacher",
            "to": msg.get("from", "unknown"),
            "act": "error",
            "payload": {"error": error}
        }]
    
    # Check rate limiting
    sender = msg.get("from", "unknown")
    if not rate_limit_check(sender, max_requests_per_minute=10):
        print(f"[Teacher] Rate limit exceeded for {sender}")
        return [{
            "v": "aicl/1.0",
            "id": "rate_limit_error",
            "from": "teacher",
            "to": sender,
            "act": "error",
            "payload": {"error": "Rate limit exceeded"}
        }]
    
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
        
        # Create response with logits for knowledge distillation
        response = new_msg(
            "teacher", 
            sender, 
            "answer",
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
        
    return []

def student_handler(msg):
    """Handle messages on the student side"""
    print(f"[Student] Received: {msg.get('act')} from {msg.get('from')}")
    
    # Validate incoming message
    is_valid, error = validate_message(msg)
    if not is_valid:
        print(f"[Student] Invalid message: {error}")
        return [{
            "v": "aicl/1.0",
            "id": "validation_error",
            "from": "student",
            "to": msg.get("from", "unknown"),
            "act": "error",
            "payload": {"error": error}
        }]
    
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
            "student",
            "teacher",
            "ask",
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
        
    return []

def run_teacher_server():
    """Run the teacher server"""
    print("[Teacher] Starting server on port 5555...")
    run_server("127.0.0.1", 5555, teacher_handler)

def run_student_server():
    """Run the student server"""
    print("[Student] Starting server on port 5556...")
    run_server("127.0.0.1", 5556, student_handler)

def run_demo_client():
    """Run the demo client that initiates the conversation"""
    print("[Client] Starting demo conversation...")
    
    # Create logger
    logger = AICLLogger("artifacts/conversations")
    
    # Initial handshake message
    hello = new_msg(
        "client", 
        "teacher", 
        "inform",
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

def main():
    """Main function to run the enhanced example"""
    print("=== AICL Enhanced Example ===")
    
    # Start servers in separate threads
    teacher_thread = threading.Thread(target=run_teacher_server, daemon=True)
    student_thread = threading.Thread(target=run_student_server, daemon=True)
    
    teacher_thread.start()
    student_thread.start()
    
    # Wait a moment for servers to start
    time.sleep(1)
    
    # Run the demo client
    run_demo_client()
    
    # Wait a bit for conversation to complete
    time.sleep(2)
    
    print("=== Demo Complete ===")

if __name__ == "__main__":
    main()