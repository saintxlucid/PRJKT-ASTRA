import hashlib
import hmac
import time
import json
from typing import Dict, Optional, Set, List
from collections import defaultdict, deque
from error_handling import AICLErrorCode, AICLSecurityError

class MessageIntegrity:
    """Message integrity verification utilities"""
    
    @staticmethod
    def create_signature(msg: Dict, secret_key: bytes) -> str:
        """
        Create HMAC signature for a message
        
        Args:
            msg (dict): The message to sign
            secret_key (bytes): Secret key for HMAC
            
        Returns:
            str: Hex digest of the signature
        """
        # Remove existing signature if present
        msg_copy = msg.copy()
        msg_copy.pop("sig", None)
        
        # Create canonical representation
        canonical = json.dumps(msg_copy, separators=(",", ":"), sort_keys=True).encode("utf-8")
        
        # Compute signature
        return hmac.new(secret_key, canonical, hashlib.sha256).hexdigest()
    
    @staticmethod
    def verify_signature(msg: Dict, secret_key: bytes) -> bool:
        """
        Verify message signature
        
        Args:
            msg (dict): The message to verify
            secret_key (bytes): Secret key for HMAC
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        if "sig" not in msg:
            return False
        
        # Extract signature
        signature = msg.pop("sig")
        
        try:
            # Compute expected signature
            expected = MessageIntegrity.create_signature(msg, secret_key)
            
            # Restore signature
            msg["sig"] = signature
            
            # Compare signatures securely
            return hmac.compare_digest(expected, signature)
        except Exception:
            # Restore signature even on error
            msg["sig"] = signature
            return False

class ReplayProtection:
    """Protection against message replay attacks"""
    
    def __init__(self, window_size: int = 10000):
        self.window_size = window_size
        self.seen_messages = deque(maxlen=window_size)
        self.seen_message_ids = set()
    
    def is_replay(self, msg: Dict) -> bool:
        """
        Check if a message is a replay
        
        Args:
            msg (dict): The message to check
            
        Returns:
            bool: True if this is a replay, False otherwise
        """
        msg_id = msg.get("id")
        if not msg_id:
            return False
        
        # Check if we've seen this message ID recently
        if msg_id in self.seen_message_ids:
            return True
        
        # Add to our tracking
        self.seen_messages.append(msg_id)
        self.seen_message_ids.add(msg_id)
        
        # If we're at capacity, remove the oldest ID
        if len(self.seen_messages) == self.window_size:
            oldest_id = self.seen_messages.popleft()
            self.seen_message_ids.discard(oldest_id)
        
        return False

class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self):
        # Store timestamps for each sender
        self.sender_timestamps = defaultdict(deque)
    
    def is_allowed(
        self,
        sender_id: str,
        max_requests_per_minute: int = 60,
        max_requests_per_hour: int = 1000,
        max_concurrent_connections: int = 8
    ) -> bool:
        """
        Check if a request is allowed based on rate limits
        
        Args:
            sender_id (str): ID of the sender
            max_requests_per_minute (int): Max requests per minute
            max_requests_per_hour (int): Max requests per hour
            max_concurrent_connections (int): Max concurrent connections
            
        Returns:
            bool: True if allowed, False if rate limited
        """
        now = time.time()
        
        # Clean old timestamps (older than 1 hour)
        cutoff = now - 3600
        queue = self.sender_timestamps[sender_id]
        while queue and queue[0] < cutoff:
            queue.popleft()
        
        # Add current timestamp
        queue.append(now)
        
        # Check hourly limit
        if len(queue) > max_requests_per_hour:
            return False
        
        # Check minute limit
        minute_ago = now - 60
        recent_requests = sum(1 for t in queue if t > minute_ago)
        if recent_requests > max_requests_per_minute:
            return False
        
        return True
    
    def get_current_usage(self, sender_id: str) -> Dict[str, int]:
        """
        Get current usage statistics for a sender
        
        Args:
            sender_id (str): ID of the sender
            
        Returns:
            dict: Usage statistics
        """
        now = time.time()
        queue = self.sender_timestamps.get(sender_id, deque())
        
        hour_ago = now - 3600
        minute_ago = now - 60
        
        hourly_count = sum(1 for t in queue if t > hour_ago)
        minute_count = sum(1 for t in queue if t > minute_ago)
        
        return {
            "requests_last_hour": hourly_count,
            "requests_last_minute": minute_count,
            "total_requests": len(queue)
        }

class AccessControl:
    """Access control and authorization"""
    
    def __init__(self):
        self.allowed_senders = set()
        self.allowed_receivers = set()
        self.sender_permissions = defaultdict(set)
    
    def add_allowed_sender(self, sender_id: str):
        """Add a sender to the allowed list"""
        self.allowed_senders.add(sender_id)
    
    def add_allowed_receiver(self, receiver_id: str):
        """Add a receiver to the allowed list"""
        self.allowed_receivers.add(receiver_id)
    
    def set_sender_permissions(self, sender_id: str, permissions: Set[str]):
        """Set permissions for a sender"""
        self.sender_permissions[sender_id] = set(permissions)
    
    def is_authorized(self, msg: Dict) -> bool:
        """
        Check if a message is authorized
        
        Args:
            msg (dict): The message to check
            
        Returns:
            bool: True if authorized, False otherwise
        """
        sender = msg.get("from")
        receiver = msg.get("to")
        act = msg.get("act")
        
        # Check if sender is allowed
        if self.allowed_senders and sender not in self.allowed_senders:
            return False
        
        # Check if receiver is allowed
        if self.allowed_receivers and receiver not in self.allowed_receivers:
            return False
        
        # Check permissions
        if sender in self.sender_permissions:
            permissions = self.sender_permissions[sender]
            if act and act not in permissions:
                return False
        
        return True

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self, secret_key: Optional[bytes] = None):
        self.secret_key = secret_key
        self.integrity = MessageIntegrity()
        self.replay_protection = ReplayProtection()
        self.rate_limiter = RateLimiter()
        self.access_control = AccessControl()
    
    def validate_message(self, msg: Dict, policy: Optional[Dict] = None) -> bool:
        """
        Comprehensive message validation
        
        Args:
            msg (dict): The message to validate
            policy (dict): Security policy constraints
            
        Returns:
            bool: True if valid, raises AICLSecurityError if not
        """
        # Check for replay attacks
        if self.replay_protection.is_replay(msg):
            raise AICLSecurityError(
                code=AICLErrorCode.REPLAY_ATTACK_DETECTED,
                message="Message replay detected",
                sender=msg.get("from")
            )
        
        # Check rate limits
        sender = msg.get("from")
        if sender and not self.rate_limiter.is_allowed(sender):
            raise AICLSecurityError(
                code=AICLErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded",
                sender=sender
            )
        
        # Check authorization
        if not self.access_control.is_authorized(msg):
            raise AICLSecurityError(
                code=AICLErrorCode.SIGNATURE_VERIFICATION_FAILED,
                message="Unauthorized message",
                sender=sender
            )
        
        # Verify signature if secret key is provided
        if self.secret_key and "sig" in msg:
            if not self.integrity.verify_signature(msg, self.secret_key):
                raise AICLSecurityError(
                    code=AICLErrorCode.SIGNATURE_VERIFICATION_FAILED,
                    message="Signature verification failed",
                    sender=sender
                )
        
        return True
    
    def sign_message(self, msg: Dict) -> Dict:
        """
        Sign a message with HMAC
        
        Args:
            msg (dict): The message to sign
            
        Returns:
            dict: The signed message
        """
        if not self.secret_key:
            raise AICLSecurityError(
                code=AICLErrorCode.SIGNATURE_VERIFICATION_FAILED,
                message="No secret key configured for signing"
            )
        
        msg_copy = msg.copy()
        msg_copy["sig"] = self.integrity.create_signature(msg, self.secret_key)
        return msg_copy