"""
ASTRA Safety Policies
Core safety policies and configuration.
Created: October 16, 2025
"""
from enum import Enum
from typing import Dict, List, Set
from pathlib import Path
from pydantic import BaseModel
from .contracts import Capability

class ConsentLevel(str, Enum):
    """Consent levels for operations"""
    IMPLICIT = "implicit"
    EXPLICIT = "explicit"
    EXPLICIT_WITH_BACKUP = "explicit_with_backup"

class RiskLevel(str, Enum):
    """Risk levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SafetyPolicy(BaseModel):
    """Safety policy configuration"""
    
    # System paths that should never be modified
    protected_paths: List[Path] = [
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("/etc"),
        Path("/usr"),
        Path("/var"),
        Path("/bin"),
        Path("/sbin")
    ]
    
    # Default consent requirements for capabilities
    capability_consent: Dict[Capability, ConsentLevel] = {
        Capability.FILE_DELETE: ConsentLevel.EXPLICIT_WITH_BACKUP,
        Capability.FILE_MOVE: ConsentLevel.EXPLICIT,
        Capability.SYSTEM_CONFIG: ConsentLevel.EXPLICIT_WITH_BACKUP,
        Capability.CODE_EXEC: ConsentLevel.EXPLICIT,
        Capability.NETWORK_WRITE: ConsentLevel.EXPLICIT,
        Capability.UI_CONTROL: ConsentLevel.IMPLICIT
    }
    
    # Operations that require backup
    backup_required: Set[Capability] = {
        Capability.FILE_DELETE,
        Capability.FILE_MOVE,
        Capability.SYSTEM_CONFIG
    }
    
    # Capability combinations that are always denied
    denied_combinations: List[Set[Capability]] = [
        {Capability.FILE_DELETE, Capability.SYSTEM_CONFIG},
        {Capability.FILE_DELETE, Capability.NETWORK_WRITE}
    ]
    
    # Domains allowed for network operations
    allowed_domains: List[str] = [
        "github.com",
        "pypi.org",
        "npmjs.com"
    ]
    
    # Risk scoring weights
    risk_weights: Dict[str, float] = {
        "capability": 0.4,
        "reversibility": 0.3,
        "scope": 0.2,
        "uncertainty": 0.1
    }
    
    # Thresholds for risk levels
    risk_thresholds: Dict[RiskLevel, float] = {
        RiskLevel.LOW: 0.3,
        RiskLevel.MEDIUM: 0.6,
        RiskLevel.HIGH: 0.8
    }
    
    def get_consent_level(self, capabilities: Set[Capability]) -> ConsentLevel:
        """Get required consent level for a set of capabilities"""
        highest_level = ConsentLevel.IMPLICIT
        
        for cap in capabilities:
            level = self.capability_consent.get(cap, ConsentLevel.IMPLICIT)
            if level.value > highest_level.value:
                highest_level = level
                
        return highest_level
    
    def requires_backup(self, capabilities: Set[Capability]) -> bool:
        """Check if operation requires backup"""
        return bool(capabilities & self.backup_required)
    
    def is_combination_allowed(self, capabilities: Set[Capability]) -> bool:
        """Check if capability combination is allowed"""
        return not any(
            denied <= capabilities  # Is denied set a subset?
            for denied in self.denied_combinations
        )
    
    def calculate_risk_score(
        self,
        capabilities: Set[Capability],
        reversible: bool,
        scope: str,
        uncertainty: float
    ) -> float:
        """Calculate risk score for an operation"""
        capability_score = len(capabilities) / 10  # 0.1 per capability
        reversibility_score = 0.0 if reversible else 1.0
        scope_scores = {"file": 0.2, "directory": 0.5, "system": 1.0}
        scope_score = scope_scores.get(scope, 0.5)
        
        weighted_scores = [
            (capability_score, self.risk_weights["capability"]),
            (reversibility_score, self.risk_weights["reversibility"]),
            (scope_score, self.risk_weights["scope"]),
            (uncertainty, self.risk_weights["uncertainty"])
        ]
        
        return sum(score * weight for score, weight in weighted_scores)
    
    def get_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert risk score to risk level"""
        for level, threshold in sorted(
            self.risk_thresholds.items(),
            key=lambda x: x[1]
        ):
            if risk_score <= threshold:
                return level
        return RiskLevel.HIGH