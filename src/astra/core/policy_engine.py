"""
ASTRA Policy Engine
================
Author: Saint Lucid
Date: October 22, 2025
Sacred Code: 333

Central policy enforcement for all ASTRA operations.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class PolicyScope(str, Enum):
    """Available permission scopes"""
    FS_WRITE = "fs.write"
    BROWSER_NAVIGATE = "browser.navigate"
    SHELL_EXEC = "shell.exec"
    EVOLUTION_PROPOSE = "evolution.propose"
    EVOLUTION_SIMULATE = "evolution.simulate"
    EVOLUTION_EXECUTE = "evolution.execute"
    EVOLUTION_ROLLBACK = "evolution.rollback"

class TelemetryLevel(str, Enum):
    """Available telemetry collection levels"""
    NONE = "none"
    MINIMAL = "minimal"
    STANDARD = "standard"
    DEBUG = "debug"

class ScopeConfig(BaseModel):
    """Configuration for a permission scope"""
    enabled: bool = False
    timeoutSec: Optional[int] = None

class FilesystemPolicy(BaseModel):
    """Filesystem access policy"""
    allowedPaths: List[str]
    blockedPaths: List[str]
    maxFilesTouched: int

class BrowserPolicy(BaseModel):
    """Browser automation policy"""
    allowedDomains: List[str]
    humanInLoop: bool

class EvolutionPolicy(BaseModel):
    """Evolution and model update policy"""
    canaryDefault: bool
    snapshotDir: str
    rollbackStrategy: str = "latest"

class PolicyConfig(BaseModel):
    """Complete policy configuration"""
    scopes: Dict[str, ScopeConfig]
    filesystem: FilesystemPolicy
    browser: BrowserPolicy
    evolution: EvolutionPolicy
    telemetry: Dict[str, str]

@dataclass
class ExecutionToken:
    """HMAC-signed execution token"""
    version: int
    issuer: str
    issued_at: int
    expires_at: int
    scopes: List[str]
    constraints: dict
    nonce: str
    signature: Optional[str] = None

class PolicyEngine:
    """
    Central policy enforcement engine
    
    Validates all privileged operations against policy.yaml
    Generates and verifies execution tokens.
    Logs audit events for all actions.
    """
    
    def __init__(
        self,
        policy_path: Union[str, Path],
        hmac_key: Optional[bytes] = None,
        audit_log_path: Optional[str] = None
    ):
        self.policy_path = Path(policy_path)
        self.hmac_key = hmac_key or self._get_hmac_key()
        self.audit_log_path = audit_log_path or "audit_event.jsonl"
        
        # Load policy
        self.policy = self._load_policy()
        self._validate_policy()
        
        # Cache compiled path patterns
        self._compile_paths()
        
        logger.info(
            "Policy engine initialized",
            extra={
                "policy_path": str(self.policy_path),
                "audit_log": self.audit_log_path
            }
        )
        
    def _load_policy(self) -> PolicyConfig:
        """Load policy from YAML"""
        if not self.policy_path.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_path}")
            
        with open(self.policy_path) as f:
            config = yaml.safe_load(f)
            
        return PolicyConfig(**config)
        
    def _validate_policy(self):
        """Validate policy configuration"""
        # Validate paths exist
        for path in self.policy.filesystem.allowedPaths:
            if not os.path.exists(path):
                logger.warning(f"Allowed path does not exist: {path}")
                
        # Validate snapshot directory
        snap_dir = Path(self.policy.evolution.snapshotDir)
        if not snap_dir.exists():
            snap_dir.mkdir(parents=True)
            
        # Validate scope configurations
        for scope in PolicyScope:
            if scope.value not in self.policy.scopes:
                raise ValueError(f"Missing scope configuration: {scope}")
                
    def _compile_paths(self):
        """Pre-compile path patterns for matching"""
        import fnmatch
        
        def compile_pattern(pattern: str) -> str:
            return fnmatch.translate(pattern)
            
        self._allowed_paths = [
            compile_pattern(p)
            for p in self.policy.filesystem.allowedPaths
        ]
        
        self._blocked_paths = [
            compile_pattern(p)
            for p in self.policy.filesystem.blockedPaths
        ]
        
    def _get_hmac_key(self) -> bytes:
        """Get HMAC key from secure storage"""
        # TODO: Implement secure key storage
        return b"SACRED_CODE_333"  # Placeholder
        
    def create_execution_token(
        self,
        scopes: List[str],
        constraints: Optional[dict] = None,
        ttl_minutes: int = 20
    ) -> ExecutionToken:
        """
        Create a new signed execution token
        
        Args:
            scopes: Requested permission scopes
            constraints: Optional execution constraints
            ttl_minutes: Token validity period
            
        Returns:
            ExecutionToken: Signed token for execution
        """
        now = int(time.time())
        
        # Apply default constraints
        constraints = constraints or {}
        constraints.update({
            "maxRuntimeMinutes": min(ttl_minutes, 20),
            "maxFilesTouched": self.policy.filesystem.maxFilesTouched,
            "allowedDomains": self.policy.browser.allowedDomains,
            "allowedPaths": self.policy.filesystem.allowedPaths,
            "blockedPaths": self.policy.filesystem.blockedPaths,
            "humanInLoop": self.policy.browser.humanInLoop,
            "telemetryLevel": self.policy.telemetry["level"]
        })
        
        # Create token
        token = ExecutionToken(
            version=1,
            issuer="saint_lucid",
            issued_at=now,
            expires_at=now + (ttl_minutes * 60),
            scopes=scopes,
            constraints=constraints,
            nonce=self._generate_nonce()
        )
        
        # Sign token
        token.signature = self._sign_token(token)
        
        return token
        
    def verify_token(self, token: ExecutionToken) -> bool:
        """Verify token signature and validity"""
        if not token.signature:
            return False
            
        # Check expiration
        if token.expires_at < time.time():
            return False
            
        # Verify signature
        expected_sig = self._sign_token(token)
        return hmac.compare_digest(token.signature, expected_sig)
        
    def validate_action(
        self,
        token: ExecutionToken,
        scope: str,
        **kwargs
    ) -> tuple[bool, str]:
        """
        Validate an action against policy
        
        Args:
            token: Execution token
            scope: Requested scope
            **kwargs: Action-specific parameters
            
        Returns:
            (bool, str): (allowed, reason)
        """
        # Verify token
        if not self.verify_token(token):
            return False, "invalid_token"
            
        # Check scope
        if scope not in token.scopes:
            return False, "scope_denied"
            
        # Check scope enabled
        if not self.policy.scopes[scope].enabled:
            return False, "scope_disabled"
            
        # Validate constraints
        if scope == PolicyScope.FS_WRITE:
            return self._validate_fs_action(token, **kwargs)
            
        elif scope == PolicyScope.BROWSER_NAVIGATE:
            return self._validate_browser_action(token, **kwargs)
            
        elif scope == PolicyScope.SHELL_EXEC:
            return self._validate_shell_action(token, **kwargs)
            
        elif scope.startswith("evolution."):
            return self._validate_evolution_action(token, scope, **kwargs)
            
        return True, "allowed"
        
    def _validate_fs_action(
        self,
        token: ExecutionToken,
        path: str,
        **kwargs
    ) -> tuple[bool, str]:
        """Validate filesystem action"""
        path = str(Path(path).resolve())
        
        # Check blocked paths
        if any(p.match(path) for p in self._blocked_paths):
            return False, "path_blocked"
            
        # Check allowed paths
        if not any(p.match(path) for p in self._allowed_paths):
            return False, "path_denied"
            
        # Check file touch limit
        touched = kwargs.get("files_touched", 1)
        if touched > token.constraints["maxFilesTouched"]:
            return False, "max_files_exceeded"
            
        return True, "allowed"
        
    def _validate_browser_action(
        self,
        token: ExecutionToken,
        domain: str,
        **kwargs
    ) -> tuple[bool, str]:
        """Validate browser action"""
        # Check domain
        if domain not in token.constraints["allowedDomains"]:
            return False, "domain_denied"
            
        # Check multi-step plans
        steps = kwargs.get("plan_steps", 1)
        if steps > 1 and token.constraints["humanInLoop"]:
            return False, "hitl_required"
            
        return True, "allowed"
        
    def _validate_shell_action(
        self,
        token: ExecutionToken,
        **kwargs
    ) -> tuple[bool, str]:
        """Validate shell execution"""
        timeout = self.policy.scopes[PolicyScope.SHELL_EXEC].timeoutSec
        if timeout and kwargs.get("timeout_sec", 0) > timeout:
            return False, "timeout_exceeded"
            
        return True, "allowed"
        
    def _validate_evolution_action(
        self,
        token: ExecutionToken,
        scope: str,
        **kwargs
    ) -> tuple[bool, str]:
        """Validate evolution action"""
        if scope == PolicyScope.EVOLUTION_EXECUTE:
            # Check canary requirement
            if self.policy.evolution.canaryDefault and not kwargs.get("canary"):
                return False, "canary_required"
                
        return True, "allowed"
        
    def log_audit_event(
        self,
        actor: str,
        operation: str,
        token_id: str,
        plan_id: Optional[str],
        inputs: dict,
        outputs: dict,
        allowed: bool,
        reason: str
    ):
        """Log an audit event"""
        # Create event
        event = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "actor": actor,
            "op": operation,
            "tokenId": token_id,
            "planId": plan_id,
            "inputs": inputs,
            "outputs": outputs,
            "policy": {
                "allow": allowed,
                "reason": reason
            }
        }
        
        # Add hash chain
        event["hash"] = self._hash_event(event)
        event["prevHash"] = self._get_last_hash()
        
        # Write event
        with open(self.audit_log_path, "a") as f:
            json.dump(event, f)
            f.write("\n")
            
    def _hash_event(self, event: dict) -> str:
        """Calculate event hash"""
        event_json = json.dumps(event, sort_keys=True)
        return hashlib.sha256(event_json.encode()).hexdigest()
        
    def _get_last_hash(self) -> Optional[str]:
        """Get hash of last audit event"""
        try:
            with open(self.audit_log_path) as f:
                for line in f:
                    pass
                last_event = json.loads(line)
                return last_event["hash"]
        except:
            return None
            
    def _sign_token(self, token: ExecutionToken) -> str:
        """Create HMAC signature for token"""
        # Prepare message
        msg = f"{token.version}.{token.issuer}.{token.issued_at}"
        msg += f".{token.expires_at}.{','.join(sorted(token.scopes))}"
        msg += f".{json.dumps(token.constraints, sort_keys=True)}"
        msg += f".{token.nonce}"
        
        # Calculate HMAC
        h = hmac.new(self.hmac_key, msg.encode(), hashlib.sha256)
        return base64.b64encode(h.digest()).decode()
        
    def _generate_nonce(self, bytes: int = 16) -> str:
        """Generate random nonce"""
        return base64.b64encode(os.urandom(bytes)).decode()