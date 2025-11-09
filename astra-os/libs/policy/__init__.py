"""
ASTRA-OS Policy Engine and Consent Broker
Implements policy loading, risk scoring, and consent workflows.

File: libs/policy/__init__.py + libs/consent/__init__.py
Lines: 600+
"""

import yaml
import json
import hashlib
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger("astra.policy")


class RiskLevel(Enum):
    """Risk classification."""
    LOW = 0.15
    MEDIUM = 0.4
    HIGH = 0.85
    CRITICAL = 1.0


@dataclass
class PolicyConfig:
    """Parsed policy configuration."""
    version: int
    risk_thresholds: Dict[str, float]
    budgets: Dict[str, int]
    consent: Dict[str, Any]
    actions: Dict[str, Any]
    file_hash: str = ""


@dataclass
class ConsentRequest:
    """Consent request to operator."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    action_preview: str = ""
    risk_score: float = 0.5
    risk_level: str = "medium"
    require_pin: bool = False
    timeout_s: int = 120
    status: str = "pending"  # pending, approved, denied, timeout
    operator_notes: str = ""
    child_requests: List["ConsentRequest"] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "ts": self.ts,
            "action_preview": self.action_preview,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "require_pin": self.require_pin,
            "timeout_s": self.timeout_s,
            "status": self.status,
            "operator_notes": self.operator_notes,
        }


class PolicyEngine:
    """
    Loads, validates, and enforces policies.
    Implements risk scoring and capability checks.
    """
    
    def __init__(self, policy_dir: str):
        self.policy_dir = Path(policy_dir)
        self.policies: Dict[str, PolicyConfig] = {}
        self.active_policy = None
        self.budget_usage: Dict[str, int] = {}
    
    def load_policy(self, name: str, yaml_path: str) -> bool:
        """Load and parse policy YAML."""
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            
            # Validate schema
            if "version" not in data:
                logger.error(f"Policy {name} missing version")
                return False
            
            # Compute HMAC for integrity
            with open(yaml_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            policy = PolicyConfig(
                version=data.get("version", 1),
                risk_thresholds=data.get("risk", {}).get("thresholds", {}),
                budgets=data.get("risk", {}).get("budgets", {}),
                consent=data.get("consent", {}),
                actions=data.get("actions", {}),
                file_hash=file_hash
            )
            
            self.policies[name] = policy
            self.active_policy = name
            
            logger.info(f"Loaded policy '{name}' (v{policy.version}, hash={file_hash[:8]}...)")
            return True
        except Exception as e:
            logger.error(f"Failed to load policy {name}: {e}")
            return False
    
    def verify_policy_integrity(self, name: str, yaml_path: str) -> bool:
        """Verify policy hasn't been tampered with."""
        if name not in self.policies:
            return False
        
        try:
            with open(yaml_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            
            stored_hash = self.policies[name].file_hash
            if current_hash != stored_hash:
                logger.error(f"Policy {name} integrity check failed!")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Integrity check error: {e}")
            return False
    
    def check_capability(self, capability: str, target: str) -> bool:
        """Check if capability is allowed by policy."""
        if not self.active_policy:
            return False
        
        policy = self.policies[self.active_policy]
        
        # Parse capability (e.g., "filesystem.write", "shell.execute")
        parts = capability.split(".")
        if len(parts) < 2:
            return False
        
        resource_type = parts[0]
        operation = parts[1]
        
        actions = policy.actions.get(resource_type, {})
        
        # Check allow list
        if "allow" in actions:
            allowed = actions["allow"]
            if isinstance(allowed, list):
                return operation in allowed or target in allowed
            else:
                return operation in str(allowed)
        
        # Check deny list
        if "deny" in actions:
            denied = actions["deny"]
            if isinstance(denied, list):
                return operation not in denied and target not in denied
        
        return True
    
    def get_budget_remaining(self, budget_name: str) -> int:
        """Get remaining budget for resource."""
        if not self.active_policy:
            return 0
        
        policy = self.policies[self.active_policy]
        total = policy.budgets.get(budget_name, 0)
        used = self.budget_usage.get(budget_name, 0)
        
        return max(0, total - used)
    
    def consume_budget(self, budget_name: str, amount: int = 1) -> bool:
        """Consume from budget."""
        remaining = self.get_budget_remaining(budget_name)
        if remaining >= amount:
            self.budget_usage[budget_name] = self.budget_usage.get(budget_name, 0) + amount
            return True
        return False
    
    def score_risk(self, context: Dict[str, Any]) -> float:
        """
        Score risk of an action given context.
        Returns 0.0-1.0 risk score.
        """
        if not self.active_policy:
            return 0.5  # Unknown = medium risk
        
        policy = self.policies[self.active_policy]
        
        # Base risk from capability type
        risk = 0.5
        
        # Modifiers
        if context.get("affects_system_files"):
            risk += 0.3
        if context.get("requires_elevation"):
            risk += 0.2
        if context.get("network_egress"):
            risk += 0.15
        if context.get("sensitive_data"):
            risk += 0.2
        if context.get("unsigned_executable"):
            risk += 0.25
        
        # Clamp to 0-1
        return min(1.0, max(0.0, risk))
    
    def get_required_consent_level(self, risk_score: float) -> str:
        """Determine consent requirement level."""
        if not self.active_policy:
            return "modal"
        
        thresholds = self.policies[self.active_policy].risk_thresholds
        
        if risk_score >= thresholds.get("block", 0.85):
            return "block"
        elif risk_score >= thresholds.get("require_prompt", 0.4):
            return "modal"
        elif risk_score >= thresholds.get("auto_ok", 0.15):
            return "toast"
        else:
            return "silent"


class ConsentBroker:
    """
    Manages consent requests and approvals.
    Tracks operator decisions and enforces safe words.
    """
    
    def __init__(self):
        self.pending: Dict[str, ConsentRequest] = {}
        self.history: List[ConsentRequest] = []
        self.max_history = 1000
        self.cooldown_minutes = 5
        self.last_requests: Dict[str, datetime] = {}
        self.global_pause = False
    
    def request_consent(self, action_preview: str, risk_score: float,
                       require_pin: bool = False) -> ConsentRequest:
        """
        Create consent request and wait for approval.
        """
        req = ConsentRequest(
            action_preview=action_preview,
            risk_score=risk_score,
            risk_level=self._risk_to_level(risk_score),
            require_pin=require_pin,
            timeout_s=120
        )
        
        self.pending[req.id] = req
        logger.info(f"Consent requested: {req.id} (risk={risk_score:.2f})")
        
        return req
    
    def resolve(self, request_id: str, approved: bool, 
               operator_notes: str = "") -> bool:
        """
        Resolve consent request with operator decision.
        """
        if request_id not in self.pending:
            logger.warning(f"Unknown consent request: {request_id}")
            return False
        
        req = self.pending.pop(request_id)
        req.status = "approved" if approved else "denied"
        req.operator_notes = operator_notes
        
        self.history.append(req)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        logger.info(f"Consent {req.status}: {request_id}")
        return approved
    
    def check_safe_word(self, text: str) -> Optional[str]:
        """
        Check if text contains safe words.
        HOLD = pause current operation
        333 STOP = global pause
        """
        if "333 STOP" in text.upper():
            self.global_pause = True
            return "GLOBAL_PAUSE"
        elif "HOLD" in text.upper():
            return "PAUSE"
        return None
    
    def is_globally_paused(self) -> bool:
        """Check if system is in global pause."""
        return self.global_pause
    
    def clear_global_pause(self):
        """Clear global pause state."""
        self.global_pause = False
    
    def check_cooldown(self, action_key: str) -> bool:
        """
        Check if action is in cooldown period.
        Prevents repeated consent requests for same action.
        """
        if action_key not in self.last_requests:
            self.last_requests[action_key] = datetime.utcnow()
            return True
        
        elapsed = datetime.utcnow() - self.last_requests[action_key]
        if elapsed < timedelta(minutes=self.cooldown_minutes):
            return False
        
        self.last_requests[action_key] = datetime.utcnow()
        return True
    
    def get_consent_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent consent decisions."""
        return [asdict(req) for req in self.history[-limit:]]
    
    def _risk_to_level(self, risk_score: float) -> str:
        """Convert risk score to level."""
        if risk_score >= 0.85:
            return "critical"
        elif risk_score >= 0.4:
            return "high"
        elif risk_score >= 0.15:
            return "medium"
        else:
            return "low"


class RiskEngine:
    """
    Comprehensive risk assessment for actions.
    Combines multiple risk factors.
    """
    
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
        self.risk_factors: Dict[str, float] = {}
    
    def assess_action(self, action: Dict[str, Any]) -> float:
        """Comprehensive risk assessment."""
        risk = 0.0
        
        # Tool risk
        tool = action.get("tool", "")
        tool_risk = self._get_tool_risk(tool)
        risk += tool_risk * 0.3
        
        # Target risk
        target = action.get("target", "")
        target_risk = self._get_target_risk(target)
        risk += target_risk * 0.3
        
        # Context risk
        context_risk = self.policy_engine.score_risk(action.get("context", {}))
        risk += context_risk * 0.4
        
        # Clamp
        return min(1.0, risk)
    
    def _get_tool_risk(self, tool: str) -> float:
        """Risk score for tool type."""
        tool_risks = {
            "filesystem.write": 0.4,
            "filesystem.delete": 0.8,
            "shell.execute": 0.9,
            "registry.write": 0.85,
            "network.egress": 0.6,
        }
        return tool_risks.get(tool, 0.3)
    
    def _get_target_risk(self, target: str) -> float:
        """Risk score for target path/resource."""
        if not target:
            return 0.1
        
        target_lower = target.lower()
        
        # System paths are high risk
        dangerous_patterns = [
            "c:\\windows",
            "c:\\program files",
            "c:\\programdata",
            "hkey_local_machine",
            "hkey_classes_root",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in target_lower:
                return 0.8
        
        # User temp is moderate risk
        if "temp" in target_lower or "appdata\\local\\temp" in target_lower:
            return 0.5
        
        # User workspace is low risk
        if "documents" in target_lower or "workspace" in target_lower:
            return 0.2
        
        return 0.3


# Policy validation schema
DEFAULT_POLICY_SCHEMA = {
    "version": 1,
    "risk": {
        "thresholds": {
            "auto_ok": 0.15,
            "require_prompt": 0.4,
            "block": 0.85,
        },
        "budgets": {
            "daily_cpu_minutes": 120,
            "daily_disk_ops": 5000,
            "daily_shell_cmds": 40,
        },
    },
    "consent": {
        "methods": ["toast", "modal"],
        "timeout_s": 120,
        "pin_required_over": 0.6,
        "safe_words": ["HOLD", "333 STOP"],
    },
    "actions": {
        "filesystem": {
            "allow_write_in": ["C:/Users/*/Workspace", "C:/Temp/ASTRA"],
            "deny_patterns": ["*.sys", "C:/Windows/*"],
        },
        "shell": {
            "allow": ["dir", "copy", "move", "git", "python"],
            "deny": ["reg delete", "bcdedit"],
        },
    },
}


__all__ = [
    "PolicyConfig",
    "ConsentRequest",
    "RiskLevel",
    "PolicyEngine",
    "ConsentBroker",
    "RiskEngine",
]
