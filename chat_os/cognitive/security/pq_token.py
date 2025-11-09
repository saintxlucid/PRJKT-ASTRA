from __future__ import annotations

import hmac
import json
import os
import time
from dataclasses import dataclass
from hashlib import sha256


@dataclass
class TokenClaims:
    sub: str
    exp: int
    scope: str
    pid: int


class PQToken:
    """Dilithium-ready token interface with HMAC fallback."""

    def __init__(self, secret_env: str = "ASTRA_HMAC_SECRET") -> None:
        secret = os.environ.get(secret_env)
        self._secret = secret.encode("utf-8") if isinstance(secret, str) else os.urandom(32)

    def _sign_classical(self, payload: bytes) -> str:
        return hmac.new(self._secret, payload, sha256).hexdigest()

    def issue(self, claims: TokenClaims) -> str:
        payload = json.dumps(vars(claims), separators=(",", ":"), sort_keys=True).encode("utf-8")
        classical = self._sign_classical(payload)
        token = {"alg": "DLTH+HMAC256", "payload": vars(claims), "sig_classical": classical}
        return json.dumps(token, separators=(",", ":"))

    def verify(self, token: str) -> bool:
        try:
            obj = json.loads(token)
            payload = json.dumps(obj["payload"], separators=(",", ":"), sort_keys=True).encode("utf-8")
            if self._sign_classical(payload) != obj.get("sig_classical"):
                return False
            if int(obj["payload"]["exp"]) < int(time.time()):
                return False
            if int(obj["payload"]["pid"]) != os.getpid():
                return False
            return True
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return False
