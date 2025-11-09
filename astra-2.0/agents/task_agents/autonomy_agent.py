"""
ASTRA Autonomy Agent
Implements plan→act loop with confirmations and cooldowns
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import time
from datetime import datetime, timedelta

from ...core.neural_network.decision_limits import ResourceBudget, ResourceLimits
from ...core.security.permission_kernel import require_capability
from ...core.security.activity_audit import audit_action

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"

@dataclass
class PlanStep:
    action: str
    params: Dict[str, Any]
    risk: RiskLevel
    description: str
    requires_confirmation: bool
    cooldown_s: float = 0.0

@dataclass 
class Plan:
    steps: List[PlanStep]
    context: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    
class ConfirmationPolicy:
    """Determines when human confirmation is needed"""
    
    def __init__(self):
        self.auto_confirm_risks = {RiskLevel.LOW}
        
    def requires_confirmation(self, step: PlanStep) -> bool:
        if step.requires_confirmation:
            return True
            
        return step.risk not in self.auto_confirm_risks

class CooldownManager:
    """Manages operation cooldowns"""
    
    def __init__(self):
        self.last_execution: Dict[str, float] = {}
        
    def check_cooldown(self, action: str) -> Optional[float]:
        """Return remaining cooldown time if any"""
        if action not in self.last_execution:
            return None
            
        elapsed = time.time() - self.last_execution[action]
        return max(0.0, self.get_cooldown(action) - elapsed)
        
    def record_execution(self, action: str):
        """Record execution time for cooldown"""
        self.last_execution[action] = time.time()
        
    def get_cooldown(self, action: str) -> float:
        """Get cooldown period for action"""
        # Could be configurable per action
        return 5.0  # Default 5s cooldown

class AutonomyAgent:
    """Manages autonomous operations with safety controls"""
    
    def __init__(self):
        self.confirmation_policy = ConfirmationPolicy()
        self.cooldown_manager = CooldownManager()
        self.current_plan: Optional[Plan] = None
        
    @require_capability("system.autonomy.plan")
    async def create_plan(self,
                         objective: str,
                         context: Dict[str, Any],
                         budget: ResourceBudget) -> Plan:
        """Create execution plan for objective"""
        
        if not budget.allow_next():
            raise Exception("Insufficient budget for planning")
            
        # Log plan creation attempt
        audit_action("autonomy.plan.create", {
            "objective": objective,
            "context": context
        })
        
        # TODO: Use neural router to generate plan
        # For now, return dummy plan
        steps = [
            PlanStep(
                action="example.action",
                params={},
                risk=RiskLevel.LOW,
                description="Example step",
                requires_confirmation=False
            )
        ]
        
        plan = Plan(
            steps=steps,
            context=context,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        self.current_plan = plan
        return plan
        
    async def get_confirmation(self, step: PlanStep) -> bool:
        """Get confirmation for high-risk step"""
        # TODO: Implement actual confirmation UI
        return False
        
    @require_capability("system.autonomy.execute")
    async def execute_step(self,
                          step: PlanStep,
                          budget: ResourceBudget) -> bool:
        """Execute single plan step"""
        
        if not budget.allow_next():
            raise Exception("Insufficient budget for execution")
            
        # Check cooldown
        remaining_cooldown = self.cooldown_manager.check_cooldown(
            step.action
        )
        if remaining_cooldown:
            await asyncio.sleep(remaining_cooldown)
            
        # Get confirmation if needed
        if self.confirmation_policy.requires_confirmation(step):
            confirmed = await self.get_confirmation(step)
            if not confirmed:
                audit_action("autonomy.step.rejected", {
                    "step": step.__dict__
                })
                return False
                
        try:
            # TODO: Actually execute the action
            # For now just log it
            audit_action("autonomy.step.execute", {
                "step": step.__dict__
            })
            
            self.cooldown_manager.record_execution(step.action)
            return True
            
        except Exception as e:
            audit_action("autonomy.step.error", {
                "step": step.__dict__,
                "error": str(e)
            })
            raise
            
    @require_capability("system.autonomy.execute")  
    async def execute_plan(self,
                          plan: Optional[Plan] = None,
                          budget: Optional[ResourceBudget] = None) -> bool:
        """Execute full plan with safety controls"""
        
        if plan is None:
            plan = self.current_plan
        if plan is None:
            raise Exception("No plan to execute")
            
        if budget is None:
            budget = ResourceBudget(ResourceLimits())
            
        if not budget.allow_next():
            raise Exception("Insufficient budget for plan execution")
            
        # Check plan expiration
        if datetime.now() > plan.expires_at:
            audit_action("autonomy.plan.expired", {
                "plan_context": plan.context
            })
            return False
            
        audit_action("autonomy.plan.start", {
            "plan_context": plan.context
        })
        
        try:
            for step in plan.steps:
                success = await self.execute_step(step, budget)
                if not success:
                    audit_action("autonomy.plan.aborted", {
                        "plan_context": plan.context,
                        "failed_step": step.__dict__
                    })
                    return False
                    
            audit_action("autonomy.plan.complete", {
                "plan_context": plan.context
            })
            return True
            
        except Exception as e:
            audit_action("autonomy.plan.error", {
                "plan_context": plan.context,
                "error": str(e)
            })
            raise

# Initialize global agent instance
_AGENT = None

def get_agent() -> AutonomyAgent:
    """Get global autonomy agent instance"""
    global _AGENT
    if _AGENT is None:
        _AGENT = AutonomyAgent()
    return _AGENT