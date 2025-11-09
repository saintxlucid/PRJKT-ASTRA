"""
Plan Preview Service - Generate visual representations of action plans before execution.

Part of Week-3 Days 21-24: Operator Console MVP

Features:
  - Convert action plans into visual graph data
  - Dependency analysis (which actions depend on which)
  - Risk scoring (high/medium/low based on action type)
  - Time estimation (expected duration per action)
  - Resource requirements (memory, CPU, network)
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class RiskLevel(str, Enum):
    """Risk levels for actions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Types of actions in a plan"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    MEMORY = "memory"
    QUERY = "query"


@dataclass
class ActionNode:
    """A single action in the plan"""
    id: str
    type: ActionType
    description: str
    risk_level: RiskLevel
    estimated_duration_ms: int
    dependencies: List[str]  # IDs of actions this depends on
    resources: Dict[str, str]  # e.g., {"file": "/etc/passwd", "permission": "read"}
    reversible: bool
    requires_consent: bool


@dataclass
class PlanGraph:
    """Visual representation of an action plan"""
    plan_id: str
    title: str
    description: str
    created_at: str
    nodes: List[ActionNode]
    total_duration_ms: int
    max_risk_level: RiskLevel
    requires_consent: bool
    reversible: bool  # Can the entire plan be rolled back?


class PlanPreviewService:
    """
    Generate visual plan previews for the Operator Console.
    
    This service analyzes action plans and produces graph data
    suitable for visualization in the frontend (Svelte).
    """
    
    # Risk scoring rules
    RISK_RULES = {
        ActionType.READ: {
            "sensitive_paths": ["/etc", "/sys", "C:\\Windows\\System32"],
            "base_risk": RiskLevel.LOW,
        },
        ActionType.WRITE: {
            "sensitive_paths": ["/etc", "/sys", "C:\\Windows", "/usr"],
            "base_risk": RiskLevel.MEDIUM,
        },
        ActionType.EXECUTE: {
            "dangerous_commands": ["rm", "del", "format", "dd", "mkfs"],
            "base_risk": RiskLevel.HIGH,
        },
        ActionType.NETWORK: {
            "base_risk": RiskLevel.MEDIUM,
        },
    }
    
    # Duration estimates (milliseconds)
    DURATION_ESTIMATES = {
        ActionType.READ: 50,
        ActionType.WRITE: 100,
        ActionType.EXECUTE: 500,
        ActionType.NETWORK: 1000,
        ActionType.MEMORY: 10,
        ActionType.QUERY: 200,
    }
    
    def __init__(self):
        self.plans: Dict[str, PlanGraph] = {}
    
    def create_plan_preview(
        self,
        plan_id: str,
        title: str,
        description: str,
        actions: List[Dict],
    ) -> PlanGraph:
        """
        Create a visual preview of an action plan.
        
        Args:
            plan_id: Unique plan identifier
            title: Human-readable plan title
            description: Plan description
            actions: List of action dicts with keys:
                - type: ActionType
                - description: str
                - resources: dict
                - dependencies: list[str]
        
        Returns:
            PlanGraph ready for visualization
        """
        nodes = []
        max_risk = RiskLevel.LOW
        total_duration = 0
        any_requires_consent = False
        all_reversible = True
        
        for i, action in enumerate(actions):
            action_type = ActionType(action.get("type", "read"))
            resources = action.get("resources", {})
            dependencies = action.get("dependencies", [])
            
            # Calculate risk
            risk = self._calculate_risk(action_type, resources)
            if self._risk_order(risk) > self._risk_order(max_risk):
                max_risk = risk
            
            # Estimate duration
            duration = self._estimate_duration(action_type, resources)
            total_duration += duration
            
            # Determine if reversible
            reversible = self._is_reversible(action_type, resources)
            if not reversible:
                all_reversible = False
            
            # Determine if requires consent
            requires_consent = risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            if requires_consent:
                any_requires_consent = True
            
            node = ActionNode(
                id=f"{plan_id}_action_{i}",
                type=action_type,
                description=action.get("description", "No description"),
                risk_level=risk,
                estimated_duration_ms=duration,
                dependencies=dependencies,
                resources=resources,
                reversible=reversible,
                requires_consent=requires_consent,
            )
            nodes.append(node)
        
        plan = PlanGraph(
            plan_id=plan_id,
            title=title,
            description=description,
            created_at=datetime.utcnow().isoformat() + "Z",
            nodes=nodes,
            total_duration_ms=total_duration,
            max_risk_level=max_risk,
            requires_consent=any_requires_consent,
            reversible=all_reversible,
        )
        
        self.plans[plan_id] = plan
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[PlanGraph]:
        """Retrieve a plan by ID"""
        return self.plans.get(plan_id)
    
    def to_dict(self, plan: PlanGraph) -> Dict:
        """Convert plan to dict for JSON serialization"""
        return {
            "plan_id": plan.plan_id,
            "title": plan.title,
            "description": plan.description,
            "created_at": plan.created_at,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type.value,
                    "description": n.description,
                    "risk_level": n.risk_level.value,
                    "estimated_duration_ms": n.estimated_duration_ms,
                    "dependencies": n.dependencies,
                    "resources": n.resources,
                    "reversible": n.reversible,
                    "requires_consent": n.requires_consent,
                }
                for n in plan.nodes
            ],
            "total_duration_ms": plan.total_duration_ms,
            "max_risk_level": plan.max_risk_level.value,
            "requires_consent": plan.requires_consent,
            "reversible": plan.reversible,
        }
    
    def _calculate_risk(self, action_type: ActionType, resources: Dict) -> RiskLevel:
        """Calculate risk level for an action"""
        rules = self.RISK_RULES.get(action_type, {})
        base_risk = rules.get("base_risk", RiskLevel.LOW)
        
        # Check for sensitive paths
        if "file" in resources or "path" in resources:
            path = resources.get("file") or resources.get("path", "")
            sensitive_paths = rules.get("sensitive_paths", [])
            for sensitive in sensitive_paths:
                if sensitive in path:
                    return self._escalate_risk(base_risk)
        
        # Check for dangerous commands
        if "command" in resources:
            cmd = resources["command"].lower()
            dangerous = rules.get("dangerous_commands", [])
            for danger in dangerous:
                if danger in cmd:
                    return RiskLevel.CRITICAL
        
        return base_risk
    
    def _estimate_duration(self, action_type: ActionType, resources: Dict) -> int:
        """Estimate action duration in milliseconds"""
        base_duration = self.DURATION_ESTIMATES.get(action_type, 100)
        
        # Network actions with remote hosts take longer
        if action_type == ActionType.NETWORK and "remote" in resources:
            return base_duration * 3
        
        # Large file operations take longer
        if "size_bytes" in resources:
            size_mb = resources["size_bytes"] / (1024 * 1024)
            if size_mb > 10:
                return base_duration * int(size_mb / 10)
        
        return base_duration
    
    def _is_reversible(self, action_type: ActionType, resources: Dict) -> bool:
        """Determine if an action can be reversed"""
        # Reads are always reversible (no side effects)
        if action_type == ActionType.READ:
            return True
        
        # Writes to temp directories are reversible
        if action_type == ActionType.WRITE:
            path = resources.get("file", resources.get("path", ""))
            if "tmp" in path.lower() or "temp" in path.lower():
                return True
            return False  # Other writes may not be reversible
        
        # Executions are generally not reversible
        if action_type == ActionType.EXECUTE:
            return False
        
        # Network actions depend on idempotency
        if action_type == ActionType.NETWORK:
            return resources.get("method", "").upper() in ["GET", "HEAD"]
        
        # Memory and query operations are reversible
        return True
    
    def _escalate_risk(self, current: RiskLevel) -> RiskLevel:
        """Escalate risk by one level"""
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        idx = order.index(current)
        if idx < len(order) - 1:
            return order[idx + 1]
        return current
    
    def _risk_order(self, risk: RiskLevel) -> int:
        """Get numeric order of risk level for comparison"""
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return order.get(risk, 0)


# Example usage
if __name__ == "__main__":
    service = PlanPreviewService()
    
    # Example plan: "Update system configuration"
    plan = service.create_plan_preview(
        plan_id="plan_001",
        title="Update System Configuration",
        description="Modify nginx config and restart service",
        actions=[
            {
                "type": "read",
                "description": "Read current nginx config",
                "resources": {"file": "/etc/nginx/nginx.conf"},
                "dependencies": [],
            },
            {
                "type": "write",
                "description": "Write updated config",
                "resources": {"file": "/etc/nginx/nginx.conf"},
                "dependencies": ["plan_001_action_0"],
            },
            {
                "type": "execute",
                "description": "Restart nginx service",
                "resources": {"command": "systemctl restart nginx"},
                "dependencies": ["plan_001_action_1"],
            },
        ],
    )
    
    print("Plan Preview:")
    print(f"  Title: {plan.title}")
    print(f"  Risk: {plan.max_risk_level.value}")
    print(f"  Duration: {plan.total_duration_ms}ms")
    print(f"  Requires Consent: {plan.requires_consent}")
    print(f"  Reversible: {plan.reversible}")
    print(f"\n  Actions ({len(plan.nodes)}):")
    for node in plan.nodes:
        print(f"    - {node.description} ({node.type.value}, {node.risk_level.value})")
