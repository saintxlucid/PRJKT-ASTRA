#!/usr/bin/env python3
"""
Advanced AICL example demonstrating all enhanced features:
- Enhanced error handling
- Message persistence and recovery
- Advanced security features
- Monitoring and observability
"""

import time
import threading
import json
from typing import List, Dict, Optional

# Import AICL modules
from .core import new_msg, aicl_core, sign, verify
from .transport import run_server, run_client, AICLConnection
from .aicl_logging import AICLLogger, AICLReplayer
from .config import config
from .error_handling import AICLError, AICLErrorCode, handle_exception
from .persistence import MessageStore, MessageRecovery
from .security import SecurityManager
from .monitoring import AICLObserver

# Configuration
SECRET_KEY = b"advanced_secret_key_for_demo"

class AdvancedTeacherHandler:
    """Advanced teacher handler with all features"""
    
    def __init__(self):
        self.security_manager = SecurityManager(SECRET_KEY)
        self.message_store = MessageStore("teacher_messages.db")
        self.message_recovery = MessageRecovery(self.message_store)
        self.observer = AICLObserver()
    
    def handle_message(self, msg: Dict) -> List[Dict]:
        """Handle incoming messages with full feature set"""
        start_time = time.time()
        message_type = msg.get("act", "unknown")
        
        try:
            # Record message receipt
            self.observer.record_message_processed(message_type, 0, True)
            
            # Security validation
            self.security_manager.validate_message(msg)
            
            # Store message
            self.message_store.store_message(msg)
            
            # Process based on message type
            responses = self._process_message(msg)
            
            # Update message status
            self.message_store.update_message_status(msg["id"], "processed")
            
            # Record successful processing
            duration_ms = (time.time() - start_time) * 1000
            self.observer.record_message_processed(message_type, duration_ms, True)
            
            return responses
            
        except AICLError as e:
            # Handle AICL-specific errors
            self.observer.record_message_processed(message_type, 
                                                 (time.time() - start_time) * 1000, 
                                                 False)
            
            # Create error response
            error_response = {
                "v": "aicl/1.0",
                "id": f"error_{msg.get('id', 'unknown')}",
                "from": "teacher",
                "to": msg.get("from", "unknown"),
                "act": "error",
                "payload": {
                    "error_code": e.code.value,
                    "message": e.message,
                    "details": e.details
                },
                "timestamp": time.time()
            }
            
            # Sign error response
            error_response = self.security_manager.sign_message(error_response)
            
            # Store error response
            self.message_store.store_message(error_response)
            
            return [error_response]
            
        except Exception as e:
            # Handle unexpected errors
            self.observer.record_message_processed(message_type, 
                                                 (time.time() - start_time) * 1000, 
                                                 False)
            
            # Convert to AICLError
            aicl_error = handle_exception(e)
            
            # Create error response
            error_response = {
                "v": "aicl/1.0",
                "id": f"error_{msg.get('id', 'unknown')}",
                "from": "teacher",
                "to": msg.get("from", "unknown"),
                "act": "error",
                "payload": {
                    "error_code": aicl_error.code.value,
                    "message": aicl_error.message,
                    "details": aicl_error.details
                },
                "timestamp": time.time()
            }
            
            # Sign error response
            error_response = self.security_manager.sign_message(error_response)
            
            # Store error response
            self.message_store.store_message(error_response)
            
            return [error_response]
    
    def _process_message(self, msg: Dict) -> List[Dict]:
        """Process message based on type"""
        act = msg.get("act")
        
        if act == "inform":  # Capabilities exchange
            response = new_msg(
                frm="teacher", 
                to=msg["from"], 
                act="ack", 
                payload={"ok": True, "capabilities": ["text", "logits:topk"]}
            )
            return [self.security_manager.sign_message(response)]
            
        elif act == "ask":
            # Process student request
            content = msg["payload"]["text"]["content"]
            
            # Create response with logits for knowledge distillation
            response = new_msg(
                frm="teacher", 
                to=msg["from"], 
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
            return [self.security_manager.sign_message(response)]
            
        elif act == "ping":
            # Respond to ping
            response = new_msg(
                frm="teacher",
                to=msg["from"],
                act="pong",
                payload={},
                ctx={"ping_id": msg.get("id")}
            )
            return [self.security_manager.sign_message(response)]
            
        return []

def run_advanced_teacher_server():
    """Run the advanced teacher server"""
    handler = AdvancedTeacherHandler()
    
    print("[Advanced Teacher] Starting server on port 5557...")
    run_server(
        config.get("host"),
        5557,
        handler.handle_message,
        use_tls=config.get("use_tls"),
        max_connections=config.get("max_connections")
    )

class AdvancedStudentClient:
    """Advanced student client with full feature set"""
    
    def __init__(self):
        self.security_manager = SecurityManager(SECRET_KEY)
        self.message_store = MessageStore("student_messages.db")
        self.observer = AICLObserver()
        self.connection: Optional[AICLConnection] = None
    
    def connect(self, host: str, port: int) -> bool:
        """Establish connection to teacher"""
        self.connection = AICLConnection(host, port, use_tls=config.get("use_tls"))
        return self.connection.connect()
    
    def send_message(self, msg: Dict) -> Optional[Dict]:
        """Send message with full error handling"""
        if not self.connection:
            return None
            
        try:
            # Sign message
            signed_msg = self.security_manager.sign_message(msg)
            
            # Store message
            self.message_store.store_message(signed_msg)
            
            # Send message
            if self.connection.send(signed_msg):
                # Record successful send
                self.observer.record_message_processed(msg["act"], 0, True)
                
                # Receive response
                response = self.connection.recv()
                if response:
                    # Store response
                    self.message_store.store_message(response)
                    
                    # Verify signature if present
                    if "sig" in response:
                        if self.security_manager.integrity.verify_signature(response, SECRET_KEY):
                            print("[Student] Response signature verified")
                        else:
                            print("[Student] WARNING: Response signature invalid!")
                    
                    return response
                else:
                    # Record failed receive
                    self.observer.record_message_processed(msg["act"], 0, False)
                    return None
            else:
                # Record failed send
                self.observer.record_message_processed(msg["act"], 0, False)
                return None
                
        except Exception as e:
            # Handle errors
            aicl_error = handle_exception(e)
            print(f"[Student] Error sending message: {aicl_error.message}")
            return None

def run_advanced_student_client():
    """Run the advanced student client"""
    client = AdvancedStudentClient()
    
    print("[Advanced Student] Connecting to teacher...")
    if not client.connect("127.0.0.1", 5557):
        print("[Advanced Student] Failed to connect to teacher")
        return
    
    print("[Advanced Student] Sending capabilities exchange...")
    
    # Initial handshake message
    hello = new_msg(
        frm="student", 
        to="teacher", 
        act="inform",
        payload={
            "caps": ["text", "logits:topk"],
            "max_ctx": 4096
        }
    )
    
    response = client.send_message(hello)
    if response:
        print(f"[Advanced Student] Received: {response.get('act')} from {response.get('from')}")
    
    print("[Advanced Student] Sending question...")
    
    # Ask message
    question = new_msg(
        frm="student",
        to="teacher",
        act="ask",
        payload={
            "text": {
                "lang": "en",
                "fmt": "md",
                "content": "Can you explain knowledge distillation?"
            }
        },
        ctx={"turn": 1},
        limits={"tokens": 128}
    )
    
    response = client.send_message(question)
    if response:
        print(f"[Advanced Student] Received: {response.get('act')} from {response.get('from')}")
        if "payload" in response and "text" in response["payload"]:
            content = response["payload"]["text"]["content"]
            print(f"[Advanced Student] Response content: {content[:50]}...")
    
    # Send ping
    ping = new_msg(
        frm="student",
        to="teacher",
        act="ping",
        payload={}
    )
    
    response = client.send_message(ping)
    if response:
        print(f"[Advanced Student] Received: {response.get('act')} from {response.get('from')}")
    
    if client.connection:
        client.connection.disconnect()

def demonstrate_monitoring():
    """Demonstrate monitoring features"""
    print("\n=== Monitoring Demonstration ===")
    
    observer = AICLObserver()
    
    # Simulate some operations
    observer.record_message_processed("ask", 15.2, True)
    observer.record_message_processed("answer", 22.7, True)
    observer.record_message_processed("error", 5.1, False)
    
    # Log some events
    observer.event_logger.log_event("system_start", "System initialized", "info")
    observer.event_logger.log_event("message_processed", "Processed ask message", "info")
    observer.event_logger.log_event("warning", "High latency detected", "warning", {"latency_ms": 150})
    
    # Get system status
    status = observer.get_system_status()
    print("System Status:")
    print(json.dumps(status, indent=2))

def main():
    """Main function to run the advanced example"""
    print("=== AICL Advanced Features Example ===")
    
    # Demonstrate monitoring
    demonstrate_monitoring()
    
    # Start server in separate thread
    server_thread = threading.Thread(target=run_advanced_teacher_server, daemon=True)
    server_thread.start()
    
    # Wait a moment for server to start
    time.sleep(1)
    
    # Run client
    run_advanced_student_client()
    
    # Wait a bit for conversation to complete
    time.sleep(2)
    
    print("=== Advanced Example Complete ===")

if __name__ == "__main__":
    main()