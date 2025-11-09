import time
import hashlib
import hmac
import json
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque

# Import our new error handling
from .error_handling import AICLErrorCode, AICLValidationError, AICLSecurityError

# Rate limiting storage
_rate_limits = defaultdict(deque)  # sender_id -> deque of timestamps

def validate_message(msg: Dict, policy: Optional[Dict] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate an AICL message against security and policy rules
    
    Args:
        msg (dict): The AICL message to validate
        policy (dict): Policy constraints (optional)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(msg, dict):
        return False, "Message must be a dictionary"
    
    # Check required fields
    required_fields = ["v", "id", "from", "to", "act", "payload"]
    for field in required_fields:
        if field not in msg:
            return False, f"Missing required field: {field}"
    
    # Check version
    if msg["v"] != "aicl/1.0":
        return False, f"Unsupported AICL version: {msg['v']}"
    
    # Validate message ID format (should be UUID-like)
    if not isinstance(msg["id"], str) or len(msg["id"]) < 8:
        return False, "Invalid message ID format"
    
    # Validate sender/receiver format
    if not isinstance(msg["from"], str) or not isinstance(msg["to"], str):
        return False, "Invalid sender/receiver format"
    
    # Validate act field
    valid_acts = {
        "ask", "answer", "inform", "plan", "tool_call", "tool_result", 
        "ping", "pong", "error", "ack", "stream"
    }
    if msg["act"] not in valid_acts:
        return False, f"Invalid act: {msg['act']}"
    
    # Check limits if policy is provided
    if policy:
        limits = msg.get("limits", {})
        
        # Token limit check
        if "max_tokens" in policy and limits.get("tokens", 0) > policy["max_tokens"]:
            return False, f"Token limit exceeded: {limits.get('tokens')} > {policy['max_tokens']}"
            
        # Latency limit check
        if "max_latency_ms" in policy and limits.get("latency_ms", 0) > policy["max_latency_ms"]:
            return False, f"Latency limit exceeded: {limits.get('latency_ms')} > {policy['max_latency_ms']}"
    
    # Basic payload size check
    payload_str = str(msg.get("payload", ""))
    max_payload_size = policy.get("max_payload_size", 100000) if policy else 100000  # 100KB default
    if len(payload_str) > max_payload_size:
        return False, f"Payload too large: {len(payload_str)} > {max_payload_size}"
    
    # Validate payload structure based on act type
    payload = msg.get("payload", {})
    act = msg["act"]
    
    if act in ["ask", "answer", "inform"] and "text" in payload:
        text = payload["text"]
        if not isinstance(text, dict) or "content" not in text:
            return False, "Invalid text payload structure"
            
    elif act == "tool_call" and "tool" in payload:
        tool = payload["tool"]
        if not isinstance(tool, dict) or "name" not in tool or "args" not in tool:
            return False, "Invalid tool_call payload structure"
            
    elif act == "tool_result" and "tool" in payload:
        tool = payload["tool"]
        if not isinstance(tool, dict) or "name" not in tool or "ok" not in tool:
            return False, "Invalid tool_result payload structure"
    
    return True, None

def rate_limit_check(
    sender_id: str, 
    max_requests_per_minute: int = 60,
    max_requests_per_hour: int = 1000,
    window_minutes: int = 60
) -> bool:
    """
    Rate limiting check with sliding window
    
    Args:
        sender_id (str): ID of the message sender
        max_requests_per_minute (int): Maximum requests allowed per minute
        max_requests_per_hour (int): Maximum requests allowed per hour
        window_minutes (int): Size of the sliding window in minutes
        
    Returns:
        bool: True if request is allowed, False if rate limited
    """
    now = time.time()
    window_start = now - (window_minutes * 60)
    
    # Clean old entries outside the window
    queue = _rate_limits[sender_id]
    while queue and queue[0] < window_start:
        queue.popleft()
    
    # Check hourly limit
    hour_ago = now - 3600
    hourly_count = sum(1 for t in queue if t > hour_ago)
    if hourly_count >= max_requests_per_hour:
        return False
    
    # Check minute limit
    minute_ago = now - 60
    minute_count = sum(1 for t in queue if t > minute_ago)
    if minute_count >= max_requests_per_minute:
        return False
    
    # Add current request
    queue.append(now)
    return True

def verify_signature(msg: Dict, secret_key: bytes) -> bool:
    """
    Verify message signature using HMAC
    
    Args:
        msg (dict): The AICL message to verify
        secret_key (bytes): Secret key for HMAC verification
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not secret_key or "sig" not in msg:
        return False
        
    # Extract signature and create canonical message
    signature = msg.pop("sig", None)
    if not signature:
        return False
        
    try:
        # Create canonical representation
        canonical = json.dumps(msg, separators=(",", ":"), sort_keys=True).encode("utf-8")
        
        # Compute expected signature
        expected = hmac.new(secret_key, canonical, hashlib.sha256).hexdigest()
        
        # Restore signature in message
        msg["sig"] = signature
        
        # Compare signatures securely
        return hmac.compare_digest(expected, signature)
    except Exception:
        # Restore signature in message even on error
        msg["sig"] = signature
        return False

def sanitize_message(msg: Dict) -> Dict:
    """
    Sanitize message by removing potentially sensitive fields
    
    Args:
        msg (dict): The message to sanitize
        
    Returns:
        dict: Sanitized message
    """
    # Create a copy to avoid modifying original
    sanitized = msg.copy()
    
    # Remove sensitive fields if they exist
    sensitive_fields = ["sig", "secret", "password", "token", "key"]
    for field in sensitive_fields:
        sanitized.pop(field, None)
        
    # Sanitize payload if it exists
    if "payload" in sanitized and isinstance(sanitized["payload"], dict):
        sanitized_payload = sanitized["payload"].copy()
        for field in sensitive_fields:
            sanitized_payload.pop(field, None)
        sanitized["payload"] = sanitized_payload
        
    return sanitized

def detect_replay(msg: Dict, replay_window_seconds: int = 300) -> bool:
    """
    Detect message replay attacks using a cache of recent message IDs
    
    Args:
        msg (dict): The message to check
        replay_window_seconds (int): Time window to remember message IDs
        
    Returns:
        bool: True if this appears to be a replay attack, False otherwise
    """
    # This would require a more sophisticated implementation with persistent storage
    # For now, we'll just return False as a placeholder
    return False