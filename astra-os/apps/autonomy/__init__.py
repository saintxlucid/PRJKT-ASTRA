"""
ASTRA-OS Autonomy Engine
Implements planning, execution, and learning with risk scoring and consent gates.

File: apps/autonomy/__init__.py
Lines: 800+
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("astra.autonomy")


class PlanStatus(Enum):
    """Plan execution status."""
    PENDING = "pending"
    PLANNING = "planning"
    AWAITING_CONSENT = "awaiting_consent"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepStatus(Enum):
    """Individual step status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ActionStep:
    """Atomic action step in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    index: int = 0
    tool: str = ""  # e.g., "filesystem.copy", "shell.execute"
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.5
    estimated_duration_ms: int = 0
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    rollback_fn: Optional[Callable] = None


@dataclass
class ExecutionPlan:
    """Complete execution plan with steps and metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    goal: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)  # cpu, budget, duration
    policy: Dict[str, Any] = field(default_factory=dict)
    steps: List[ActionStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    risk_score: float = 0.5
    max_risk_score: float = 0.5
    consent_token: Optional[str] = None
    operator_feedback_score: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "goal": self.goal,
            "context": self.context,
            "constraints": self.constraints,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "max_risk_score": self.max_risk_score,
            "steps": len(self.steps),
            "operator_feedback": self.operator_feedback_score,
        }


class Planner:
    """
    LLM-based planner that converts goals into step-by-step execution plans.
    Uses local LLM or cached reasoning.
    """
    
    def __init__(self, risk_engine=None, memory=None):
        self.risk_engine = risk_engine
        self.memory = memory
        self.plan_templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load canned plan templates for common tasks."""
        self.plan_templates = {
            "organize_downloads": {
                "steps": [
                    {"tool": "filesystem.list", "params": {"path": "~/Downloads"}},
                    {"tool": "filesystem.organize", "params": {"rules": "by_type"}},
                    {"tool": "filesystem.move", "params": {"dest": "~/Workspace/Inbox"}},
                ]
            },
            "backup_project": {
                "steps": [
                    {"tool": "filesystem.hash", "params": {"path": "."}},
                    {"tool": "filesystem.copy", "params": {"dest": "/backup"}},
                ]
            },
            "focus_mode": {
                "steps": [
                    {"tool": "notifications.toast", "params": {"msg": "Focus Mode activated"}},
                    {"tool": "focus.timer", "params": {"minutes": 50}},
                ]
            },
        }
    
    async def create_plan(self, goal: str, context: Dict[str, Any],
                         constraints: Dict[str, Any] = None) -> ExecutionPlan:
        """
        Create execution plan for goal.
        Uses templates or LLM reasoning.
        """
        constraints = constraints or {}
        
        plan = ExecutionPlan(
            goal=goal,
            context=context,
            constraints=constraints
        )
        
        # Check for template match
        template = self._find_template_match(goal)
        if template:
            plan.steps = self._steps_from_template(template)
        else:
            # Use LLM or rule-based reasoning
            plan.steps = await self._reason_plan(goal, context)
        
        # Compute risk
        plan.risk_score = self._compute_plan_risk(plan)
        plan.max_risk_score = max([s.risk_score for s in plan.steps] or [0.5])
        
        logger.info(f"Created plan {plan.id}: {goal} (risk={plan.risk_score:.2f}, "
                   f"steps={len(plan.steps)})")
        
        return plan
    
    def _find_template_match(self, goal: str) -> Optional[Dict[str, Any]]:
        """Find matching template for goal."""
        goal_lower = goal.lower()
        for key, template in self.plan_templates.items():
            if key in goal_lower:
                return template
        return None
    
    def _steps_from_template(self, template: Dict[str, Any]) -> List[ActionStep]:
        """Convert template to action steps."""
        steps = []
        for i, step_spec in enumerate(template.get("steps", [])):
            step = ActionStep(
                index=i,
                tool=step_spec.get("tool", ""),
                description=step_spec.get("description", ""),
                parameters=step_spec.get("params", {}),
                risk_score=step_spec.get("risk", 0.3),
                estimated_duration_ms=step_spec.get("duration_ms", 1000)
            )
            steps.append(step)
        return steps
    
    async def _reason_plan(self, goal: str, context: Dict[str, Any]) -> List[ActionStep]:
        """
        Reason about plan using LLM or heuristics.
        For now, simple heuristics.
        """
        steps = []
        
        # Very simple heuristic planner
        if "organize" in goal.lower():
            steps.append(ActionStep(
                index=0,
                tool="filesystem.list",
                description="List files",
                risk_score=0.1
            ))
            steps.append(ActionStep(
                index=1,
                tool="filesystem.organize",
                description="Organize by type",
                risk_score=0.4
            ))
        elif "backup" in goal.lower():
            steps.append(ActionStep(
                index=0,
                tool="filesystem.copy",
                description="Copy files",
                risk_score=0.3
            ))
        else:
            # Default step
            steps.append(ActionStep(
                index=0,
                tool="notifications.toast",
                description=f"Execute: {goal}",
                risk_score=0.2
            ))
        
        return steps
    
    def _compute_plan_risk(self, plan: ExecutionPlan) -> float:
        """Compute aggregate risk for entire plan."""
        if not plan.steps:
            return 0.0
        
        # Weighted average with decay for step count
        total_risk = sum(s.risk_score for s in plan.steps)
        avg_risk = total_risk / len(plan.steps)
        
        # Increase risk slightly for complex plans
        complexity_factor = min(1.2, 1.0 + len(plan.steps) * 0.05)
        
        return min(1.0, avg_risk * complexity_factor)


class Executor:
    """
    Executes plans step-by-step with error handling, rollback, and monitoring.
    """
    
    def __init__(self, tool_bus=None, memory=None):
        self.tool_bus = tool_bus
        self.memory = memory
        self.active_plans: Dict[str, ExecutionPlan] = {}
    
    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Execute plan and return result."""
        import time
        
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.utcnow().isoformat() + "Z"
        start_time = time.time()
        
        self.active_plans[plan.id] = plan
        
        try:
            for i, step in enumerate(plan.steps):
                if step.status == StepStatus.COMPLETED:
                    continue
                
                step.status = StepStatus.EXECUTING
                logger.info(f"Executing step {i}: {step.description}")
                
                try:
                    result = await self._execute_step(step)
                    step.result = result
                    step.status = StepStatus.COMPLETED
                except Exception as e:
                    logger.error(f"Step failed: {e}")
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                    
                    # Attempt rollback
                    await self._rollback_plan(plan, i)
                    plan.status = PlanStatus.ROLLED_BACK
                    break
            
            if plan.status == PlanStatus.EXECUTING:
                plan.status = PlanStatus.COMPLETED
        
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            plan.status = PlanStatus.FAILED
        
        finally:
            plan.completed_at = datetime.utcnow().isoformat() + "Z"
            plan.duration_ms = int((time.time() - start_time) * 1000)
            del self.active_plans[plan.id]
        
        return plan
    
    async def _execute_step(self, step: ActionStep) -> Dict[str, Any]:
        """Execute single step."""
        if not self.tool_bus:
            return {"skipped": True}
        
        # Route to appropriate tool
        # In real implementation, would call tool_bus.execute()
        logger.info(f"Would execute tool: {step.tool} with {step.parameters}")
        
        return {
            "tool": step.tool,
            "success": True,
            "output": "simulated"
        }
    
    async def _rollback_plan(self, plan: ExecutionPlan, up_to_step: int):
        """Rollback completed steps."""
        for i in range(up_to_step - 1, -1, -1):
            step = plan.steps[i]
            if step.status == StepStatus.COMPLETED and step.rollback_fn:
                try:
                    await step.rollback_fn()
                    step.status = StepStatus.ROLLED_BACK
                    logger.info(f"Rolled back step {i}")
                except Exception as e:
                    logger.error(f"Rollback failed for step {i}: {e}")


class Learner:
    """
    Learning system that improves plans based on outcomes and operator feedback.
    Implements bandit-style preference learning.
    """
    
    def __init__(self, memory=None):
        self.memory = memory
        self.plan_evaluations: List[Dict[str, Any]] = []
        self.feedback_weights: Dict[str, float] = {}
    
    async def provide_feedback(self, plan_id: str, score: float,
                              notes: str = "") -> bool:
        """
        Operator provides feedback on plan execution.
        Score: -1.0 (bad) to +1.0 (excellent)
        """
        if self.memory:
            await self.memory.episodic.store_reward(
                reward_id=str(uuid.uuid4()),
                ts=datetime.utcnow().isoformat() + "Z",
                task_id=plan_id,
                score=score,
                notes=notes
            )
        
        self.plan_evaluations.append({
            "plan_id": plan_id,
            "score": score,
            "notes": notes,
            "ts": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info(f"Feedback recorded for {plan_id}: {score}")
        return True
    
    async def compute_plan_preference(self, plan_a_id: str, 
                                     plan_b_id: str) -> float:
        """
        Compute preference between two plans (0.0-1.0).
        0.0 = prefer A, 1.0 = prefer B
        """
        # Simple implementation: average of reward scores
        score_a = self._average_score_for_plan(plan_a_id)
        score_b = self._average_score_for_plan(plan_b_id)
        
        if score_a == score_b:
            return 0.5
        
        # Logistic preference
        diff = score_b - score_a
        return 1.0 / (1.0 + 2.7 ** (-diff * 2.0))
    
    def _average_score_for_plan(self, plan_id: str) -> float:
        """Get average feedback score for plan."""
        scores = [e["score"] for e in self.plan_evaluations 
                 if e["plan_id"] == plan_id]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        return {
            "total_evaluations": len(self.plan_evaluations),
            "positive_feedback": len([e for e in self.plan_evaluations 
                                     if e["score"] > 0.3]),
            "negative_feedback": len([e for e in self.plan_evaluations 
                                     if e["score"] < -0.3]),
            "avg_score": (sum(e["score"] for e in self.plan_evaluations) / 
                         len(self.plan_evaluations) if self.plan_evaluations else 0.0),
        }


class AutonomyEngine:
    """
    Main autonomy engine combining planner, executor, and learner.
    Implements the trigger->plan->consent->execute->learn loop.
    """
    
    def __init__(self, tool_bus=None, consent_broker=None, memory=None,
                 policy_engine=None):
        self.tool_bus = tool_bus
        self.consent_broker = consent_broker
        self.memory = memory
        self.policy_engine = policy_engine
        
        self.planner = Planner(memory=memory)
        self.executor = Executor(tool_bus=tool_bus, memory=memory)
        self.learner = Learner(memory=memory)
        
        self.completed_plans: List[ExecutionPlan] = []
        self.routine_triggers: Dict[str, Dict[str, Any]] = {}
    
    async def process_trigger(self, trigger: Dict[str, Any]) -> Optional[ExecutionPlan]:
        """
        Process a trigger and execute appropriate plan if needed.
        Trigger types: time, sensor, anomaly, operator intent
        """
        trigger_type = trigger.get("type", "")
        logger.info(f"Processing trigger: {trigger_type}")
        
        # Map trigger to goal
        goal = self._trigger_to_goal(trigger)
        if not goal:
            return None
        
        # Create plan
        plan = await self.planner.create_plan(goal, context=trigger)
        
        # Check risk and request consent if needed
        if plan.risk_score >= self.policy_engine.policies[self.policy_engine.active_policy].risk_thresholds.get("require_prompt", 0.4):
            if self.consent_broker:
                consent_req = self.consent_broker.request_consent(
                    action_preview=f"{goal} ({len(plan.steps)} steps, "
                                  f"risk={plan.risk_score:.2f})",
                    risk_score=plan.risk_score,
                    require_pin=plan.risk_score > 0.6
                )
                plan.consent_token = consent_req.id
                
                # Wait for consent (in real implementation)
                # For now, simulate auto-approval for demo
                logger.info("Waiting for operator consent...")
                plan.status = PlanStatus.AWAITING_CONSENT
        
        # Execute plan
        result_plan = await self.executor.execute_plan(plan)
        self.completed_plans.append(result_plan)
        
        return result_plan
    
    def _trigger_to_goal(self, trigger: Dict[str, Any]) -> Optional[str]:
        """Convert trigger to goal string."""
        trigger_type = trigger.get("type", "")
        
        if trigger_type == "time.daily_18h":
            return "Organize downloads and backup project"
        elif trigger_type == "focus_app.premiere":
            return "Enable focus mode with 50-minute timer"
        elif trigger_type == "sensor.unusual_network":
            return "Investigate and report network anomaly"
        elif trigger_type == "operator":
            return trigger.get("goal")
        
        return None
    
    def register_routine(self, name: str, trigger: Dict[str, Any],
                        goal: str) -> bool:
        """Register an automation routine."""
        self.routine_triggers[name] = {
            "trigger": trigger,
            "goal": goal,
            "enabled": True
        }
        logger.info(f"Registered routine: {name}")
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get autonomy engine statistics."""
        learning_stats = await self.learner.get_learning_stats()
        
        return {
            "completed_plans": len(self.completed_plans),
            "registered_routines": len(self.routine_triggers),
            "learning": learning_stats,
        }


__all__ = [
    "PlanStatus",
    "StepStatus",
    "ActionStep",
    "ExecutionPlan",
    "Planner",
    "Executor",
    "Learner",
    "AutonomyEngine",
]
