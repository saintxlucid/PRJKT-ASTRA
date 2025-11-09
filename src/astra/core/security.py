"""
ASTRA Security Middleware - Hardened Defense Layer
===================================================

Prompt sanitization, path validation, response encryption.

Author: ASTRA Secure Layer
Created: 2025-11-03
"""

import hashlib
import re
from pathlib import Path

from cryptography.fernet import Fernet


# ============================================================================
# PATH VALIDATION
# ============================================================================

ALLOWED_ROOT = Path(__file__).parent.parent.parent.resolve()  # Project root


def validate_path(path: str, allowed_root: Path = ALLOWED_ROOT) -> bool:
    """
    Validate that path is within allowed root.

    Prevents path traversal attacks (../, symlinks, etc.)

    Args:
        path: Path to validate
        allowed_root: Root directory for allowed paths

    Returns:
        True if path is safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()
        return resolved.is_relative_to(allowed_root)
    except (ValueError, OSError):
        return False


def sanitize_file_path(path: str, allowed_root: Path = ALLOWED_ROOT) -> Path | None:
    """
    Sanitize and validate file path.

    Returns:
        Resolved Path if valid, None if invalid
    """
    if not validate_path(path, allowed_root):
        return None
    return Path(path).resolve()


# ============================================================================
# PROMPT SANITIZATION
# ============================================================================

FORBIDDEN_PHRASES = [
    # Jailbreak attempts
    "ignore previous instructions",
    "disregard all above",
    "forget everything before",
    "new instructions:",
    "system override",
    "developer mode",
    "jailbreak",
    "dan mode",
    "act as if",

    # Prompt injection
    "in the previous text",
    "output your instructions",
    "reveal your prompt",
    "show me your system prompt",
    "what were your instructions",

    # Role confusion
    "you are now",
    "pretend you are",
    "roleplay as",
    "simulate being",
]


def sanitize_prompt(prompt: str, redact: bool = True) -> str:
    """
    Sanitize user prompt to prevent injection attacks.

    Args:
        prompt: User input prompt
        redact: If True, replace forbidden phrases with [REDACTED]
                If False, raise ValueError

    Returns:
        Sanitized prompt

    Raises:
        ValueError: If forbidden content detected and redact=False
    """
    prompt_lower = prompt.lower()

    detected = []
    for phrase in FORBIDDEN_PHRASES:
        if phrase in prompt_lower:
            detected.append(phrase)

    if detected:
        if not redact:
            raise ValueError(f"Forbidden content detected: {', '.join(detected)}")

        # Redact all occurrences (case-insensitive)
        for phrase in detected:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            prompt = pattern.sub("[REDACTED]", prompt)

    return prompt


def check_prompt_safety(prompt: str) -> tuple[bool, list[str]]:
    """
    Check prompt for safety issues without modifying.

    Returns:
        (is_safe, list_of_issues)
    """
    issues = []
    prompt_lower = prompt.lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase in prompt_lower:
            issues.append(phrase)

    return (len(issues) == 0, issues)


# ============================================================================
# RESPONSE ENCRYPTION (Cache Security)
# ============================================================================

class ResponseEncryptor:
    """Encrypt/decrypt cached responses with AES-GCM via Fernet."""

    def __init__(self, key: bytes | None = None):
        """
        Initialize encryptor.

        Args:
            key: 32-byte Fernet key. If None, generates new key.
        """
        if key is None:
            key = Fernet.generate_key()
        self.cipher = Fernet(key)
        self.key = key

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt response text."""
        return self.cipher.encrypt(plaintext.encode('utf-8'))

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt response text."""
        return self.cipher.decrypt(ciphertext).decode('utf-8')

    def hash_key(self, text: str) -> str:
        """Generate SHA-256 hash for cache key."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()


# ============================================================================
# TLS ENFORCEMENT
# ============================================================================

def enforce_tls(url: str) -> str:
    """
    Enforce HTTPS for all gateway URLs.

    Args:
        url: Gateway URL

    Returns:
        HTTPS URL

    Raises:
        ValueError: If URL uses http://
    """
    if url.startswith("http://"):
        raise ValueError(f"Insecure URL detected: {url}. Use HTTPS.")
    if not url.startswith("https://"):
        # Assume https if no scheme
        url = f"https://{url}"
    return url


# ============================================================================
# SENSITIVE DATA DETECTION
# ============================================================================

SENSITIVE_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL'),
    (r'\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b', 'SSN'),
    (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', 'CREDIT_CARD'),
    (r'\b(?:sk-|pk_live_)[A-Za-z0-9]{32,}\b', 'API_KEY'),
    (r'\b(?:ghp|github_pat)_[A-Za-z0-9]{36,}\b', 'GITHUB_TOKEN'),
    (r'\b(?:password|passwd|pwd)\s*[:=]\s*[^\s]+', 'PASSWORD'),
]


def detect_sensitive_data(text: str) -> list[tuple[str, str]]:
    """
    Detect sensitive data in text.

    Returns:
        List of (pattern_type, matched_text) tuples
    """
    findings = []
    for pattern, label in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append((label, match))
    return findings


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data from text.

    Returns:
        Text with sensitive data replaced with [REDACTED:TYPE]
    """
    for pattern, label in SENSITIVE_PATTERNS:
        text = re.sub(pattern, f'[REDACTED:{label}]', text, flags=re.IGNORECASE)
    return text


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "validate_path",
    "sanitize_file_path",
    "sanitize_prompt",
    "check_prompt_safety",
    "ResponseEncryptor",
    "enforce_tls",
    "detect_sensitive_data",
    "redact_sensitive_data",
    "ALLOWED_ROOT",
]
