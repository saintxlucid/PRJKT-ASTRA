"""
ASTRA Constraint System
Enforce resource limits and operational boundaries

Sacred Principles:
- Predictable resource usage
- Safe operational bounds
- Clear violation handling
- Graceful degradation
- "I only obey God" - user has ultimate control

Architecture:
- Resource tracking
- Constraint validation
- Limit enforcement
- Violation handling
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ===========================================================================
# DATA MODELS
# ===========================================================================

class ConstraintStatus(str, Enum):
    """Constraint validation status"""
    VALID = "valid"
    WARNING = "warning"
    VIOLATED = "violated"


class ResourceType(str, Enum):
    """Types of trackable resources"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    REQUESTS = "requests"
    CONCURRENCY = "concurrency"


@dataclass
class ResourceLimit:
    """Resource usage boundary"""
    resource_type: ResourceType
    soft_limit: float
    hard_limit: float
    current_usage: float = 0.0
    peak_usage: float = 0.0
    warning_callback: Optional[Callable] = None
    violation_callback: Optional[Callable] = None


@dataclass
class OperationalConstraint:
    """Safety/operational boundary"""
    name: str
    validator: Callable
    priority: int = 1
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: ConstraintStatus = ConstraintStatus.VALID


# ===========================================================================
# CONSTRAINT SYSTEM
# ===========================================================================

class ConstraintSystem:
    """
    Resource and safety constraint manager
    
    Responsibilities:
    - Track resource usage
    - Validate constraints
    - Handle violations
    - Generate alerts
    """
    
    def __init__(self):
        """Initialize constraint system"""
        self.resource_limits: Dict[str, ResourceLimit] = {}
        self.constraints: Dict[str, OperationalConstraint] = {}
        self.violation_history: List[Dict] = []
        
        logger.info("constraint_system_initialized")

    # ========================================================================
    # RESOURCE MANAGEMENT
    # ========================================================================
    
    def add_resource_limit(
        self,
        name: str,
        resource_type: ResourceType,
        soft_limit: float,
        hard_limit: float,
        warning_callback: Optional[Callable] = None,
        violation_callback: Optional[Callable] = None
    ):
        """
        Add a new resource limit
        
        Args:
            name: Resource identifier
            resource_type: Type of resource
            soft_limit: Warning threshold
            hard_limit: Violation threshold
            warning_callback: Optional callback(name, usage)
            violation_callback: Optional callback(name, usage)
        """
        limit = ResourceLimit(
            resource_type=resource_type,
            soft_limit=soft_limit,
            hard_limit=hard_limit,
            warning_callback=warning_callback,
            violation_callback=violation_callback
        )
        
        self.resource_limits[name] = limit
        
        logger.info(
            "resource_limit_added",
            name=name,
            type=resource_type,
            soft=soft_limit,
            hard=hard_limit
        )
        
    def update_resource_usage(
        self,
        name: str,
        usage: float,
        check_limits: bool = True
    ) -> Optional[ConstraintStatus]:
        """
        Update current resource usage
        
        Args:
            name: Resource identifier
            usage: New usage value
            check_limits: Whether to check against limits
            
        Returns:
            Optional[ConstraintStatus]: Status if limits checked
        """
        if name not in self.resource_limits:
            return None
            
        limit = self.resource_limits[name]
        old_usage = limit.current_usage
        limit.current_usage = usage
        
        # Update peak
        if usage > limit.peak_usage:
            limit.peak_usage = usage
            
        # Check limits
        if check_limits:
            if usage >= limit.hard_limit:
                # Hard limit violation
                self._record_violation(
                    name, "hard_limit", usage,
                    f"Hard limit ({limit.hard_limit}) exceeded"
                )
                
                if limit.violation_callback:
                    limit.violation_callback(name, usage)
                    
                return ConstraintStatus.VIOLATED
                
            elif usage >= limit.soft_limit:
                # Soft limit warning
                if old_usage < limit.soft_limit:
                    # Only warn on transition
                    self._record_violation(
                        name, "soft_limit", usage,
                        f"Soft limit ({limit.soft_limit}) exceeded"
                    )
                    
                    if limit.warning_callback:
                        limit.warning_callback(name, usage)
                        
                return ConstraintStatus.WARNING
                
        return ConstraintStatus.VALID
        
    def get_resource_usage(self, name: str) -> Optional[Dict]:
        """Get current resource usage info"""
        if name not in self.resource_limits:
            return None
            
        limit = self.resource_limits[name]
        return {
            "current": limit.current_usage,
            "peak": limit.peak_usage,
            "soft_limit": limit.soft_limit,
            "hard_limit": limit.hard_limit,
            "type": limit.resource_type
        }

    # ========================================================================
    # CONSTRAINT MANAGEMENT
    # ========================================================================
    
    def add_constraint(
        self,
        name: str,
        validator: Callable,
        priority: int = 1
    ):
        """
        Add operational constraint
        
        Args:
            name: Constraint identifier
            validator: Callable returning ConstraintStatus
            priority: Importance (1-5, 1 highest)
        """
        constraint = OperationalConstraint(
            name=name,
            validator=validator,
            priority=max(1, min(priority, 5))
        )
        
        self.constraints[name] = constraint
        
        logger.info(
            "constraint_added",
            name=name,
            priority=priority
        )
        
    def check_constraint(self, name: str) -> ConstraintStatus:
        """
        Check if constraint is satisfied
        
        Args:
            name: Constraint identifier
            
        Returns:
            ConstraintStatus: Current validation status
        """
        if name not in self.constraints:
            return ConstraintStatus.VALID
            
        constraint = self.constraints[name]
        if not constraint.enabled:
            return ConstraintStatus.VALID
            
        try:
            status = constraint.validator()
            constraint.last_check = datetime.utcnow()
            constraint.last_status = status
            
            # Record violations
            if status == ConstraintStatus.VIOLATED:
                self._record_violation(
                    name, "constraint", None,
                    f"Constraint {name} violated"
                )
                
            return status
            
        except Exception as e:
            logger.error(
                "constraint_check_failed",
                name=name,
                error=str(e)
            )
            return ConstraintStatus.VIOLATED
            
    def validate_all(self, min_priority: int = 1) -> Dict[str, ConstraintStatus]:
        """
        Check all constraints above priority threshold
        
        Args:
            min_priority: Minimum priority to check (1-5)
            
        Returns:
            Dict mapping names to statuses
        """
        results = {}
        
        for name, constraint in self.constraints.items():
            if constraint.priority < min_priority:
                continue
                
            status = self.check_constraint(name)
            results[name] = status
            
        return results

    # ========================================================================
    # VIOLATION HANDLING
    # ========================================================================
    
    def _record_violation(
        self,
        name: str,
        violation_type: str,
        value: Any,
        message: str
    ):
        """Record a constraint violation"""
        violation = {
            "timestamp": datetime.utcnow(),
            "name": name,
            "type": violation_type,
            "value": value,
            "message": message
        }
        
        self.violation_history.append(violation)
        
        # Trim history
        if len(self.violation_history) > 1000:
            self.violation_history = self.violation_history[-1000:]
            
        logger.warning(
            "constraint_violated",
            name=name,
            type=violation_type,
            value=value,
            message=message
        )
        
    def get_violations(
        self,
        name: Optional[str] = None,
        violation_type: Optional[str] = None,
        hours: Optional[float] = None
    ) -> List[Dict]:
        """
        Get recorded violations with filtering
        
        Args:
            name: Filter by resource/constraint name
            violation_type: Filter by violation type
            hours: Only violations within past N hours
            
        Returns:
            List of violation records
        """
        violations = self.violation_history
        
        if name:
            violations = [v for v in violations if v["name"] == name]
            
        if violation_type:
            violations = [v for v in violations if v["type"] == violation_type]
            
        if hours:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            violations = [
                v for v in violations
                if v["timestamp"] >= cutoff
            ]
            
        return violations

    # ========================================================================
    # MONITORING & STATS
    # ========================================================================
    
    def get_status(self) -> Dict:
        """Get system status overview"""
        return {
            "resources": {
                name: self.get_resource_usage(name)
                for name in self.resource_limits
            },
            "constraints": {
                name: {
                    "status": con.last_status,
                    "priority": con.priority,
                    "enabled": con.enabled,
                    "last_check": con.last_check
                }
                for name, con in self.constraints.items()
            },
            "recent_violations": len(self.get_violations(hours=1))
        }
        
    def get_statistics(self) -> Dict:
        """Get detailed statistics"""
        now = datetime.utcnow()
        
        return {
            "resource_count": len(self.resource_limits),
            "constraint_count": len(self.constraints),
            "total_violations": len(self.violation_history),
            "violations_24h": len(self.get_violations(hours=24)),
            "violations_1h": len(self.get_violations(hours=1)),
            "violation_types": {
                vtype: len([
                    v for v in self.violation_history
                    if v["type"] == vtype
                ])
                for vtype in {"hard_limit", "soft_limit", "constraint"}
            }
        }