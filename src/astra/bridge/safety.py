"""
ASTRA Bridge Safety
Input redaction and sanitization for safe processing.
"""
from .patterns import REDACTIONS


def redact(text: str) -> str:
    """
    Apply redaction patterns to sensitive data.
    Also applies hard length cap to prevent oversized payloads.
    
    Returns sanitized text (max 10,000 chars).
    """
    masked = text
    for pat, repl in REDACTIONS:
        masked = pat.sub(repl, masked)
    
    # Hard cap to avoid oversized payloads
    return masked[:10000]


def validate_safety(text: str, max_len: int = 10000) -> tuple[bool, str]:
    """
    Validate input for safety before processing.
    
    Returns:
        (is_safe: bool, reason: str)
    """
    if len(text) == 0:
        return False, "Empty input"
    
    if len(text) > max_len:
        return False, f"Input exceeds max length ({max_len} chars)"
    
    # Could add more validation rules here
    # - Check for malicious patterns
    # - Validate encoding
    # - Check for injection attempts
    
    return True, "OK"
