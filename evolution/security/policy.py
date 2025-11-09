"""Policy engine for privileged operation validation.

Provides:
- Allowlist-based operation validation
- HMAC token validation for privileged actions
- Policy rule evaluation and enforcement
- Audit logging for security events
"""

import hmac
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
import yaml


class SecurityLevel(Enum):
    """Security levels for operations."""
    LOW = 0      # Basic operations, no special privileges
    MEDIUM = 1   # Protected operations, requires basic auth
    HIGH = 2     # Privileged operations, requires HMAC
    CRITICAL = 3 # System-critical, requires multi-factor


@dataclass
class PolicyRule:
    """Rule definition for policy enforcement."""
    operation: str
    level: SecurityLevel
    allowlist: Set[str]
    requires_hmac: bool = False
    requires_audit: bool = False
    max_batch_size: Optional[int] = None
    cooldown_period: Optional[timedelta] = None


@dataclass
class SecurityToken:
    """Security token for operation validation."""
    operation: str
    timestamp: datetime
    nonce: str
    hmac: str


class PolicyViolation(Exception):
    """Raised when a policy rule is violated."""
    pass


class PolicyEngine:
    """Enforces security policies for privileged operations."""
    
    def __init__(
        self,
        config_path: Path,
        hmac_key: bytes,
        audit_path: Optional[Path] = None
    ):
        """Initialize policy engine.
        
        Args:
            config_path: Path to policy config YAML
            hmac_key: HMAC secret key
            audit_path: Optional path for audit logs
        """
        self.config_path = Path(config_path)
        self.hmac_key = hmac_key
        self.audit_path = Path(audit_path) if audit_path else None
        
        # Load policy configuration
        self.rules = self._load_policy_rules()
        
        # Setup audit logging
        self.logger = logging.getLogger("policy_engine")
        if self.audit_path:
            handler = logging.FileHandler(self.audit_path)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        # Track operation timestamps for cooldown
        self.last_operations: Dict[str, datetime] = {}
        
    def validate_operation(
        self,
        operation: str,
        token: Optional[SecurityToken] = None,
        context: Optional[Dict] = None
    ) -> bool:
        """Validate if an operation is allowed.
        
        Args:
            operation: Operation identifier
            token: Optional security token
            context: Optional operation context
            
        Returns:
            True if operation is allowed
            
        Raises:
            PolicyViolation: If operation violates policy
        """
        # Get policy rule
        try:
            rule = self.rules[operation]
        except KeyError:
            raise PolicyViolation(f"No policy defined for operation: {operation}")
            
        # Check security level requirements
        if rule.level != SecurityLevel.LOW and token is None:
            raise PolicyViolation(
                f"Security token required for {operation}"
            )
            
        # Validate HMAC token if required
        if rule.requires_hmac and token:
            if not self._validate_token(token):
                raise PolicyViolation("Invalid security token")
                
        # Check allowlist
        if context and "user" in context:
            if context["user"] not in rule.allowlist:
                raise PolicyViolation(
                    f"User {context['user']} not in allowlist for {operation}"
                )
                
        # Check cooldown period
        if rule.cooldown_period:
            last_time = self.last_operations.get(operation)
            if last_time:
                elapsed = datetime.now() - last_time
                if elapsed < rule.cooldown_period:
                    raise PolicyViolation(
                        f"Operation {operation} in cooldown for "
                        f"{(rule.cooldown_period - elapsed).seconds}s"
                    )
                    
        # Check batch size limits
        if rule.max_batch_size and context and "batch_size" in context:
            if context["batch_size"] > rule.max_batch_size:
                raise PolicyViolation(
                    f"Batch size {context['batch_size']} exceeds "
                    f"limit {rule.max_batch_size}"
                )
                
        # Update operation timestamp
        self.last_operations[operation] = datetime.now()
        
        # Audit if required
        if rule.requires_audit:
            self._audit_operation(operation, token, context)
            
        return True
        
    def create_token(
        self,
        operation: str,
        nonce: Optional[str] = None
    ) -> SecurityToken:
        """Create a security token for an operation.
        
        Args:
            operation: Operation identifier
            nonce: Optional nonce (generated if None)
            
        Returns:
            Security token
        """
        timestamp = datetime.now()
        if nonce is None:
            nonce = self._generate_nonce()
            
        # Create message
        msg = json.dumps({
            "operation": operation,
            "timestamp": timestamp.isoformat(),
            "nonce": nonce
        })
        
        # Generate HMAC
        h = hmac.new(self.hmac_key, msg.encode(), hashlib.sha256)
        
        return SecurityToken(
            operation=operation,
            timestamp=timestamp,
            nonce=nonce,
            hmac=h.hexdigest()
        )
        
    def _load_policy_rules(self) -> Dict[str, PolicyRule]:
        """Load policy rules from config file."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
            
        rules = {}
        for op_name, op_config in config["operations"].items():
            rules[op_name] = PolicyRule(
                operation=op_name,
                level=SecurityLevel[op_config["level"]],
                allowlist=set(op_config.get("allowlist", [])),
                requires_hmac=op_config.get("requires_hmac", False),
                requires_audit=op_config.get("requires_audit", False),
                max_batch_size=op_config.get("max_batch_size"),
                cooldown_period=timedelta(
                    seconds=op_config.get("cooldown_seconds", 0)
                ) if "cooldown_seconds" in op_config else None
            )
            
        return rules
        
    def _validate_token(self, token: SecurityToken) -> bool:
        """Validate a security token."""
        # Check timestamp (within 5 minutes)
        if datetime.now() - token.timestamp > timedelta(minutes=5):
            return False
            
        # Verify HMAC
        msg = json.dumps({
            "operation": token.operation,
            "timestamp": token.timestamp.isoformat(),
            "nonce": token.nonce
        })
        
        h = hmac.new(self.hmac_key, msg.encode(), hashlib.sha256)
        return hmac.compare_digest(h.hexdigest(), token.hmac)
        
    def _generate_nonce(self, length: int = 16) -> str:
        """Generate a random nonce."""
        import secrets
        return secrets.token_hex(length)
        
    def _audit_operation(
        self,
        operation: str,
        token: Optional[SecurityToken],
        context: Optional[Dict]
    ) -> None:
        """Log an audit entry for an operation."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "token_present": token is not None
        }
        
        if context:
            entry["context"] = context
            
        self.logger.info("Audit: %s", json.dumps(entry))