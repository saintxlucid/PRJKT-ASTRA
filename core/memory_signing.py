"""
ASTRA Memory Signing - Integrity Protection

HMAC-SHA256 signing for all memory records to detect tampering or corruption.
Requires ASTRA_MEMORY_SIGNING_KEY environment variable (256-bit key).

Usage (in MemoryEngine):
    # On write:
    from core.memory_signing import sign_record
    sig, ts = sign_record(memory)
    memory["signature"] = {"alg": "HMAC-SHA256", "ts": ts, "value": sig}
    
    # On read:
    from core.memory_signing import verify_record
    sig_obj = memory.get("signature", {})
    if not verify_record(memory, sig_obj.get("value", ""), sig_obj.get("ts", 0)):
        memory["quarantined"] = True  # Do not use for RAG

Security Model:
    - Key rotation: Change ASTRA_MEMORY_SIGNING_KEY and re-sign all memories
    - Quarantine: Unverified memories are flagged but not deleted (forensics)
    - Canonical fields: Only id, timestamp, type, content, meta are signed
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Tuple

ENV_KEY = "ASTRA_MEMORY_SIGNING_KEY"

# Canonical fields included in signature (adjust to your memory schema)
CANON_FIELDS = ("id", "timestamp", "type", "content", "meta")


def _key() -> bytes:
    """Get signing key from environment."""
    k = os.environ.get(ENV_KEY)
    if not k:
        raise RuntimeError(
            f"{ENV_KEY} not set. Generate via: (New-Guid).Guid or openssl rand -hex 32"
        )
    return k.encode("utf-8")


def _canonicalize(record: Dict[str, Any]) -> bytes:
    """Produce canonical JSON bytes for signing."""
    payload = {k: record.get(k) for k in CANON_FIELDS if k in record}
    return json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sign_record(record: Dict[str, Any]) -> Tuple[str, int]:
    """
    Sign a memory record with HMAC-SHA256.
    
    Args:
        record: Memory dict with canonical fields
        
    Returns:
        (signature_hex, timestamp)
    """
    ts = int(time.time())
    msg = _canonicalize(record) + f"|{ts}".encode()
    sig = hmac.new(_key(), msg, hashlib.sha256).hexdigest()
    return sig, ts


def verify_record(record: Dict[str, Any], sig: str, ts: int) -> bool:
    """
    Verify a signed memory record.
    
    Args:
        record: Memory dict
        sig: Signature hex string
        ts: Signature timestamp
        
    Returns:
        True if signature valid, False otherwise
    """
    if not sig:
        return False
    msg = _canonicalize(record) + f"|{ts}".encode()
    expected = hmac.new(_key(), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
