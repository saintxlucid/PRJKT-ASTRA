"""
DPAPI-backed secret store helpers for Windows.
Wraps Windows DPAPI via pywin32 when available, otherwise falls back to
an in-memory (non-production) store for testing.
"""
from typing import Optional
import os
import structlog

logger = structlog.get_logger(__name__)

try:
    import win32crypt
    HAS_DPAPI = True
except Exception:
    HAS_DPAPI = False

# Fallback in-memory store (for non-Windows or CI)
_in_memory_store = {}

def dpapi_protect(raw: bytes) -> bytes:
    """Protect bytes using Windows DPAPI or fallback store."""
    if HAS_DPAPI:
        try:
            protected = win32crypt.CryptProtectData(raw, None, None, None, None, 0)
            return protected
        except Exception as e:
            logger.error("dpapi_protect_failed", error=str(e))
            raise
    else:
        # Non-secure fallback: store in memory and return key reference
        key = os.urandom(16).hex()
        _in_memory_store[key] = raw
        return key.encode('utf-8')

def dpapi_unprotect(blob: bytes) -> bytes:
    """Unprotect bytes previously protected."""
    if HAS_DPAPI:
        try:
            unprotected = win32crypt.CryptUnprotectData(blob, None, None, None, None, 0)[1]
            return unprotected
        except Exception as e:
            logger.error("dpapi_unprotect_failed", error=str(e))
            raise
    else:
        key = blob.decode('utf-8')
        return _in_memory_store.get(key, b'')
