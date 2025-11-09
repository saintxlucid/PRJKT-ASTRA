"""
API key authentication for Q&A endpoints.

Requires x-astra-key header with format: key_id.secret
Server verifies against ASTRA_API_KEYS env var (CSV of "key_id:sha256_hash")
"""

from fastapi import Header, HTTPException
import os
import hmac
import hashlib
from typing import Dict, Optional


API_HEADER = "x-astra-key"
API_KEYS = os.getenv("ASTRA_API_KEYS", "")

# Parse API_KEYS into registry: {key_id: sha256_hash}
REGISTRY: Dict[str, str] = {}
if API_KEYS:
    for entry in API_KEYS.split(","):
        entry = entry.strip()
        if ":" in entry:
            kid, hash_val = entry.split(":", 1)
            REGISTRY[kid] = hash_val


def require_api_key(x_astra_key: Optional[str] = Header(None)) -> Dict[str, str]:
    """
    FastAPI dependency that enforces API key authentication.
    
    Usage:
        @app.post("/answer")
        def answer(req: AnswerRequest, _: dict = Depends(require_api_key)):
            ...
    
    Args:
        x_astra_key: Header value in format "key_id.secret"
    
    Returns:
        Dict with authenticated key_id
    
    Raises:
        HTTPException: 401 if header missing, 403 if invalid
    """
    if not x_astra_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "X-Astra-Key"}
        )
    
    try:
        kid, secret = x_astra_key.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Malformed API key (expected format: key_id.secret)"
        )
    
    # Look up expected hash for this key_id
    expected_hash = REGISTRY.get(kid)
    if not expected_hash:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key: unknown key_id"
        )
    
    # Hash the provided secret and compare
    actual_hash = hashlib.sha256(secret.encode()).hexdigest()
    if not hmac.compare_digest(expected_hash, actual_hash):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key: authentication failed"
        )
    
    return {"kid": kid, "authenticated": True}


def generate_api_key(key_id: str, secret: str) -> str:
    """
    Helper to generate an entry for ASTRA_API_KEYS env var.
    
    Usage:
        key_entry = generate_api_key("client1", "secret123")
        # Add to ASTRA_API_KEYS: client1:abc123...
        # Multiple keys: export ASTRA_API_KEYS="client1:hash1,client2:hash2"
    
    Args:
        key_id: Key identifier (e.g., "client1", "mobile_app")
        secret: Secret passphrase
    
    Returns:
        Formatted string entry for ASTRA_API_KEYS environment variable
    """
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return f"{key_id}:{digest}"


def reload_registry():
    """Reload API keys from environment (useful for runtime updates)."""
    global REGISTRY
    REGISTRY.clear()
    api_keys = os.getenv("ASTRA_API_KEYS", "")
    if api_keys:
        for entry in api_keys.split(","):
            entry = entry.strip()
            if ":" in entry:
                kid, hash_val = entry.split(":", 1)
                REGISTRY[kid] = hash_val


if __name__ == "__main__":
    # Example: Generate API key
    import sys
    if len(sys.argv) == 3:
        kid, secret = sys.argv[1], sys.argv[2]
        print(f"API Key Entry: {generate_api_key(kid, secret)}")
        print(f"\nAdd to ASTRA_API_KEYS environment variable")
        print(f"Example: ASTRA_API_KEYS=\"{generate_api_key(kid, secret)}\"")
    else:
        print("Usage: python security_api_key.py <key_id> <secret>")
        print("Example: python security_api_key.py client1 MyClientSecret456")
