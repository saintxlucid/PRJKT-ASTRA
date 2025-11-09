import json
import traceback
from typing import Dict, Optional, Any
from enum import Enum

class AICLErrorCode(Enum):
    """Standardized error codes for AICL"""
    # Message validation errors
    INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    INVALID_MESSAGE_ID = "INVALID_MESSAGE_ID"
    INVALID_SENDER_RECEIVER = "INVALID_SENDER_RECEIVER"
    INVALID_ACT = "INVALID_ACT"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    
    # Security errors
    SIGNATURE_VERIFICATION_FAILED = "SIGNATURE_VERIFICATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    REPLAY_ATTACK_DETECTED = "REPLAY_ATTACK_DETECTED"
    
    # Network errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    SEND_FAILED = "SEND_FAILED"
    RECEIVE_FAILED = "RECEIVE_FAILED"
    TIMEOUT = "TIMEOUT"
    
    # Resource errors
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    OUT_OF_MEMORY = "OUT_OF_MEMORY"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

class AICLError(Exception):
    """Base exception class for AICL errors"""
    
    def __init__(
        self, 
        code: AICLErrorCode, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation"""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }
    
    def to_json(self) -> str:
        """Convert error to JSON string"""
        return json.dumps(self.to_dict(), separators=(",", ":"))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AICLError':
        """Create AICLError from dictionary representation"""
        return cls(
            code=AICLErrorCode(data["error_code"]),
            message=data["message"],
            details=data.get("details", {}),
            cause=None  # We can't reconstruct the original exception
        )

class AICLValidationError(AICLError):
    """Exception for validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
            message=message,
            details=details
        )

class AICLSecurityError(AICLError):
    """Exception for security-related errors"""
    def __init__(self, code: AICLErrorCode, message: str, sender: Optional[str] = None):
        details = {}
        if sender:
            details["sender"] = sender
        
        super().__init__(
            code=code,
            message=message,
            details=details
        )

class AICLNetworkError(AICLError):
    """Exception for network-related errors"""
    def __init__(
        self, 
        code: AICLErrorCode, 
        message: str, 
        host: Optional[str] = None, 
        port: Optional[int] = None
    ):
        details = {}
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        
        super().__init__(
            code=code,
            message=message,
            details=details
        )

def handle_exception(e: Exception) -> AICLError:
    """Convert standard exceptions to AICLError"""
    if isinstance(e, AICLError):
        return e
    
    # Handle common standard exceptions
    if isinstance(e, ValueError):
        return AICLError(
            code=AICLErrorCode.INVALID_MESSAGE_FORMAT,
            message=str(e),
            cause=e
        )
    elif isinstance(e, TimeoutError):
        return AICLError(
            code=AICLErrorCode.TIMEOUT,
            message=str(e),
            cause=e
        )
    elif isinstance(e, MemoryError):
        return AICLError(
            code=AICLErrorCode.OUT_OF_MEMORY,
            message=str(e),
            cause=e
        )
    else:
        # Generic internal error
        return AICLError(
            code=AICLErrorCode.INTERNAL_ERROR,
            message=f"Unexpected error: {str(e)}",
            details={"exception_type": type(e).__name__},
            cause=e
        )

def format_exception_trace(e: Exception) -> str:
    """Format exception with full traceback for debugging"""
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))

def create_error_message(
    frm: str,
    to: str,
    error: AICLError,
    original_msg_id: Optional[str] = None
) -> Dict:
    """Create a standardized error message"""
    from .core import new_error_msg
    return new_error_msg(
        frm=frm,
        to=to,
        error=error.to_json(),
        original_msg_id=original_msg_id
    )