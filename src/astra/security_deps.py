"""
Admin authentication dependency for sensitive endpoints.

Requires x-astra-admin header with format: key_id.secret
Server verifies against ASTRA_ADMIN_KEY env var (format: key_id:sha256_hash)
"""

from fastapi import Header, HTTPException
import os
import hmac
import hashlib
from typing import Dict, Optional


ADMIN_HEADER = "x-astra-admin"
ADMIN_KEY = os.getenv("ASTRA_ADMIN_KEY", "")


def require_admin(x_astra_admin: Optional[str] = Header(None)) -> Dict[str, str]:
    """
    FastAPI dependency that enforces admin authentication.
    
    Usage:
        @app.post("/drain")
        def drain(_: dict = Depends(require_admin)):
            ...
    
    Args:
        x_astra_admin: Header value in format "key_id.secret"
    
    Returns:
        Dict with authenticated key_id
    
    Raises:
        HTTPException: 401 if header missing, 403 if invalid
    """
    if not x_astra_admin:
        raise HTTPException(
            status_code=401,
            detail="Missing admin header",
            headers={"WWW-Authenticate": "X-Astra-Admin"}
        )
    
    try:
        kid, secret = x_astra_admin.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Malformed admin token (expected format: key_id.secret)"
        )
    
    # Hash the provided secret
    digest = hashlib.sha256(secret.encode()).hexdigest()
    expected_format = f"{kid}:{digest}"
    
    # Compare against environment variable
    if not ADMIN_KEY or not hmac.compare_digest(ADMIN_KEY, expected_format):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid admin credentials"
        )
    
    return {"kid": kid, "authenticated": True}


def generate_admin_key(key_id: str, secret: str) -> str:
    """
    Helper to generate the ASTRA_ADMIN_KEY env var value.
    
    Usage:
        admin_key = generate_admin_key("ops", "your-secret-here")
        # Set as: ASTRA_ADMIN_KEY=ops:abc123...
    
    Args:
        key_id: Key identifier (e.g., "ops", "admin")
        secret: Secret passphrase
    
    Returns:
        Formatted string for ASTRA_ADMIN_KEY environment variable
    """
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return f"{key_id}:{digest}"


if __name__ == "__main__":
    # Example: Generate admin key
    import sys
    if len(sys.argv) == 3:
        kid, secret = sys.argv[1], sys.argv[2]
        print(f"ASTRA_ADMIN_KEY={generate_admin_key(kid, secret)}")
    else:
        print("Usage: python security_deps.py <key_id> <secret>")
        print("Example: python security_deps.py ops MyAdminSecret123")
