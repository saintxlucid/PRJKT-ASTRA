"""
Simple Vault abstraction for secrets management.

Supports:
- HashiCorp Vault via hvac (if installed + configured via VAULT_ADDR/VAULT_TOKEN)
- Fallback to environment variables
- Developer-friendly local file (encrypted with Fernet if cryptography is present)

Keep this minimal and pluggable for Phase 0.
"""
from typing import Optional
import os
import json
import structlog

logger = structlog.get_logger(__name__)

try:
    import hvac
    HAS_HVAC = True
except Exception:
    HAS_HVAC = False

try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except Exception:
    HAS_FERNET = False


class Vault:
    """Minimal vault facade.

    Usage:
        v = Vault()
        secret = v.get_secret('pg/password')
    """

    def __init__(self):
        self.backend = os.environ.get("VAULT_BACKEND", "env")

        if self.backend == "hvac" and HAS_HVAC:
            self.client = hvac.Client(
                url=os.getenv("VAULT_ADDR"),
                token=os.getenv("VAULT_TOKEN"),
            )
            logger.info("vault_hvac_initialized")
        else:
            self.client = None
            if self.backend == "hvac":
                logger.warning("vault_hvac_requested_but_hvac_missing")

        # local file fallback
        self.local_path = os.getenv("LOCAL_VAULT_PATH", "data/local_vault.json")
        if not os.path.exists(os.path.dirname(self.local_path)):
            try:
                os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
            except Exception:
                pass

    def get_secret(self, key: str) -> Optional[str]:
        """Get secret by key. Order: HashiCorp -> env -> local file."""
        # 1) HashiCorp
        if self.client:
            try:
                # assume key is 'secret/data/path' style or 'kv/path'
                path = key
                resp = self.client.secrets.kv.v2.read_secret_version(path=path)
                data = resp.get("data", {}).get("data", {})
                # if value is nested, return JSON string
                if isinstance(data, dict):
                    return json.dumps(data)
                return str(data)
            except Exception as e:
                logger.warning("vault_hvac_read_failed", key=key, error=str(e))

        # 2) Environment variables
        env_key = key.upper().replace("/", "_")
        if env_key in os.environ:
            return os.environ[env_key]

        # 3) Local file
        if os.path.exists(self.local_path):
            try:
                with open(self.local_path, "r") as f:
                    data = json.load(f)
                    if key in data:
                        return data[key]
            except Exception as e:
                logger.warning("vault_local_read_failed", error=str(e))

        return None

    def put_secret_local(self, key: str, value: str):
        """Write secret to local file (developer only)."""
        data = {}
        if os.path.exists(self.local_path):
            try:
                with open(self.local_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        data[key] = value
        with open(self.local_path, "w") as f:
            json.dump(data, f, indent=2)
