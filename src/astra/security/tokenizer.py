"""
HMAC Execution Tokenizer (v1)
Generates and verifies single-use HMAC tokens for privileged tool execution.
Token format: v1.<b64url(payload)>.<hex(hmac)>
Payload: { sub, scopes, nonce, exp, trace_id }
"""
import os
import json
import time
import hmac
import hashlib
import base64
import uuid
from typing import Tuple, Set, Dict, Any

from astra.security.dpapi_store import dpapi_unprotect
import structlog

logger = structlog.get_logger(__name__)

USED_NONCES = set()

def b64u_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b'=')

def b64u_decode(data: bytes) -> bytes:
    padding = b'=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)

class Tokenizer:
    def __init__(self, secret_blob: bytes):
        # secret_blob may be DPAPI-protected; caller should unprotect
        self.secret = secret_blob

    @classmethod
    def from_dpapi(cls, protected_blob: bytes):
        secret = dpapi_unprotect(protected_blob)
        return cls(secret)

    def create(self, sub: str, scopes: Set[str], ttl: int = 120, trace_id: str = None) -> str:
        payload = {
            'sub': sub,
            'scopes': list(scopes),
            'nonce': str(uuid.uuid4()),
            'exp': int(time.time()) + ttl,
            'trace_id': trace_id or f"trc_{uuid.uuid4().hex[:8]}"
        }
        payload_b = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        payload_b64 = b64u_encode(payload_b)
        mac = hmac.new(self.secret, payload_b64, hashlib.sha256).hexdigest()
        token = f"v1.{payload_b64.decode('utf-8')}.{mac}"
        return token

    def verify(self, token: str, want_scopes: Set[str]) -> Tuple[bool, str, Dict[str, Any]]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, 'format', {}
            ver, payload_b64_s, mac_hex = parts
            if ver != 'v1':
                return False, 'ver', {}
            payload_b64 = payload_b64_s.encode('utf-8')
            expected_mac = hmac.new(self.secret, payload_b64, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_mac, mac_hex):
                return False, 'sig', {}
            payload = json.loads(b64u_decode(payload_b64))
            if time.time() > payload['exp']:
                return False, 'exp', payload
            if payload['nonce'] in USED_NONCES:
                return False, 'replay', payload
            if not set(payload.get('scopes', [])).issuperset(want_scopes):
                return False, 'scope', payload
            # mark nonce as used (single-use)
            USED_NONCES.add(payload['nonce'])
            return True, 'ok', payload
        except Exception as e:
            logger.error('token_verify_exception', error=str(e))
            return False, 'error', {}
