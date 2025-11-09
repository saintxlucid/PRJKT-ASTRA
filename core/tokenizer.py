# core/tokenizer.py
"""
ASTRA Execution Tokenizer - HMAC-signed capability tokens
Provides short-lived, scope-limited, immutable tokens for consent-gated actions.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

# Import credential store for secure secret management
try:
    from core.credential_store import load_hmac_secret
    _SECRET = load_hmac_secret(is_previous=False)
    _PREV_SECRET = load_hmac_secret(is_previous=True)
except ImportError:
    # Fallback to environment variables if credential_store not available
    _SECRET = os.environ.get("ASTRA_POLICY_HMAC", "dev-secret-change-me").encode()
    _PREV_SECRET = os.environ.get("ASTRA_POLICY_HMAC_PREV", "").encode() or None


def _b64u(x: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(x).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    """Base64url decode with automatic padding."""
    s2 = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s2.encode())


def issue(
    action: str,
    scope: str,
    res: str,
    args: dict,
    ttl_s: int = 30,
    budget_ms: int = 2000,
    policy: str = "action",
) -> str:
    """
    Issue a new execution token.
    
    Args:
        action: Tool/action name (e.g., 'fs.copy', 'shell.run', 'browser.navigate')
        scope: Permission scope ('read|write|network|ui|process|fs|admin')
        res: Resource hint (path/host/window-title)
        args: Action arguments (will be hashed for immutability)
        ttl_s: Time-to-live in seconds (default 30s, max 300s for safety)
        budget_ms: Maximum execution time in milliseconds
        policy: Consent level ('info|action|admin')
    
    Returns:
        HMAC-signed token string (payload.signature)
    """
    now = int(time.time())
    args_hash = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
    
    claims = {
        "sub": action,
        "scope": scope,
        "res": res,
        "args_hash": args_hash,
        "nbf": now,
        "exp": now + min(int(ttl_s), 300),  # Cap at 5 minutes
        "jti": secrets.token_hex(8),
        "budget": {
            "ms": int(budget_ms),
            "stdout_kb": 256
        },
        "policy": policy,
        "iat": now
    }
    
    payload = _b64u(json.dumps(claims, separators=(",", ":")).encode())
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest()
    token = payload + "." + _b64u(sig)
    
    return token


from typing import Any


def verify(token: str, args: dict) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Verify an execution token.
    
    Args:
        token: The token string to verify
        args: Action arguments to check against args_hash
    
    Returns:
        Tuple of (ok, reason, claims-or-none)
        Reasons: "ok", "bad_sig", "expired", "nbf", "args_mismatch", or exception string
    """
    try:
        if "." not in token:
            return False, "malformed", None
            
        payload, sig = token.split(".", 1)
        
        # Verify HMAC signature (try current secret first, then previous)
        expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest()
        sig_bytes = _b64d(sig)
        
        valid = hmac.compare_digest(expected, sig_bytes)
        if not valid and _PREV_SECRET:
            # Try previous secret for dual-key rotation window
            expected_prev = hmac.new(_PREV_SECRET, payload.encode(), hashlib.sha256).digest()
            valid = hmac.compare_digest(expected_prev, sig_bytes)
        
        if not valid:
            return False, "bad_sig", None
        
        # Decode claims
        claims = json.loads(_b64d(payload))
        now = int(time.time())
        
        # Check not-before
        if now < claims.get("nbf", 0):
            return False, "nbf", claims
        
        # Check expiry
        if now > claims.get("exp", 0):
            return False, "expired", claims
        
        # Verify args haven't changed
        h = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()
        if h != claims.get("args_hash"):
            return False, "args_mismatch", claims
        
        return True, "ok", claims
        
    except json.JSONDecodeError as e:
        return False, f"json_decode_error:{str(e)}", None
    except Exception as e:
        return False, f"exception:{type(e).__name__}", None


def rotate_secret(new_secret: str, grace_period_s: int = 300) -> None:
    """
    Rotate the HMAC secret with a grace period for dual-key window.
    
    Args:
        new_secret: The new secret to use
        grace_period_s: How long to accept old tokens (default 5 minutes)
    """
    global _SECRET, _PREV_SECRET
    
    # Use credential store if available
    try:
        from core.credential_store import rotate_hmac_secret
        rotate_hmac_secret(new_secret.encode())
        _PREV_SECRET = _SECRET
        _SECRET = new_secret.encode()
    except ImportError:
        # Fallback: manual rotation
        _PREV_SECRET = _SECRET
        _SECRET = new_secret.encode()


def get_claims(token: str) -> dict[str, Any] | None:
    """
    Extract claims from a token without full verification.
    Useful for logging/debugging. DO NOT use for authorization.

    Args:
        token: The token string

    Returns:
        Claims dict or None if malformed
    """
    try:
        payload = token.split(".", 1)[0]
        return json.loads(_b64d(payload))
    except Exception:
        return None


# Token scope constants for type safety
SCOPE_READ = "read"
SCOPE_WRITE = "write"
SCOPE_NETWORK = "network"
SCOPE_UI = "ui"
SCOPE_PROCESS = "process"
SCOPE_FS = "fs"
SCOPE_ADMIN = "admin"

# Policy level constants
POLICY_INFO = "info"
POLICY_ACTION = "action"
POLICY_ADMIN = "admin"
