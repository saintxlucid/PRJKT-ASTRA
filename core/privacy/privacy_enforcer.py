"""
ASTRA Privacy Protection Protocol (A.P.P.P) Enforcer
Core module that enforces privacy protections across the system
"""

import os
import socket
import yaml
import functools
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("astra.privacy")

CONFIG_PATH = Path(__file__).parent / "privacy_config.yaml"

class PrivacyEnforcer:
    """Enforces ASTRA's privacy protection protocol"""
    
    def __init__(self):
        self._load_config()
        self._original_socket = socket.create_connection
        self._initialized = False
    
    def _load_config(self):
        """Load privacy configuration"""
        try:
            with open(CONFIG_PATH) as f:
                self.config = yaml.safe_load(f)
            logger.info("Privacy config loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load privacy config: {e}")
            self.config = {}
    
    def in_strict_mode(self) -> bool:
        """Check if running in strict privacy mode"""
        return self.config.get("PRIVACY_MODE", "STRICT").upper() == "STRICT"
    
    def allowed_hostname(self, hostname: str) -> bool:
        """Check if hostname is allowed for network access"""
        if not self.in_strict_mode():
            return True
        
        # Allow localhost always
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return True
            
        allowed = self.config.get("ALLOWED_ENDPOINTS", [])
        return hostname in allowed

    def _guard_socket(self, address, *args, **kwargs):
        """Guard socket connections to prevent unauthorized network access"""
        host = address[0] if isinstance(address, tuple) else address
        if not self.allowed_hostname(host):
            self.log_blocked_access("network", f"Blocked connection to {host}")
            raise ConnectionError(f"Network access blocked by privacy policy: {host}")
        return self._original_socket(address, *args, **kwargs)

    def enforce_startup(self):
        """Enforce privacy protections at startup"""
        if self._initialized:
            return
            
        logger.info("Activating ASTRA Privacy Protection Protocol")
        
        if self.in_strict_mode():
            # Replace socket connection with guarded version
            socket.create_connection = self._guard_socket
            
            # Disable telemetry and crash reporting via env vars
            os.environ["DISABLE_TELEMETRY"] = "1"
            os.environ["CRASH_REPORTS_ENABLED"] = "0"
            
            # Set training opt-out flags
            os.environ["NO_TRAIN"] = "1"
            os.environ["DISABLE_METRICS"] = "1"
            
            # Create encryption key if needed
            key_path = Path(self.config.get("ENCRYPTION_KEY_PATH", "core/privacy/.ast_key"))
            if not key_path.exists():
                from .storage import generate_and_store_key
                generate_and_store_key(key_path)
            
            logger.info("Privacy enforcement active - STRICT mode")
        else:
            logger.info("Privacy enforcement active - LENIENT mode")
        
        self._initialized = True
    
    def log_blocked_access(self, category: str, details: str):
        """Log blocked access attempts"""
        try:
            from .audit_logger import log_event
            log_event(
                action="blocked_access",
                actor="privacy_enforcer",
                payload={
                    "category": category,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to log blocked access: {e}")

# Global instance
_enforcer = None

def get_privacy_enforcer() -> PrivacyEnforcer:
    """Get the global privacy enforcer instance"""
    global _enforcer
    if _enforcer is None:
        _enforcer = PrivacyEnforcer()
    return _enforcer

# Decorator to prevent data exfiltration
def block_exfiltration(func):
    """Decorator that blocks data exfiltration attempts"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        enforcer = get_privacy_enforcer()
        if enforcer.in_strict_mode():
            # Check for potential data exfiltration
            endpoint = kwargs.get("endpoint") or (args[0] if args else None)
            if endpoint and isinstance(endpoint, str):
                if "://" in endpoint:
                    host = endpoint.split("/")[2]
                else:
                    host = endpoint
                if not enforcer.allowed_hostname(host):
                    enforcer.log_blocked_access(
                        "data_exfiltration",
                        f"Blocked data upload to {host}"
                    )
                    raise PermissionError(f"Data upload blocked by privacy policy: {host}")
        return func(*args, **kwargs)
    return wrapper