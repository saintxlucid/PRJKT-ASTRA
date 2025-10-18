"""
ASTRA Planner L2 System
Multi-step planning with user consent loop and budget enforcement.

Architecture:
1. PLAN: Generate multi-step execution plan using LLM reasoning
2. ASK: Request user consent with plan details and budget display
3. ACT: Execute plan steps with real-time budget tracking and consent gates

Consent Flow:
- Plan generation: HIGH budget cost (5 tokens)
- Per-step execution: MEDIUM cost (1-2 tokens per step)
- Budget enforcement: Strict limits, no overages

Created: October 18, 2025
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import structlog

logger = structlog.get_logger()

# ============================================================================
# TYPES & ENUMS
# ============================================================================


class StepStatus(Enum):
    """Plan step execution status"""

    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class RiskLevel(Enum):
    """Risk assessment for plan steps"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlanStep:
    """Single step in execution plan"""

    id: str
    description: str
    tool: str
    action: str
    args: Dict[str, Any]
    risk_level: RiskLevel
    cost_estimate: int  # Budget tokens
    reversible: bool = True
    status: StepStatus = field(default=StepStatus.PENDING)
    error: Optional[str] = None
    result: Optional[Any] = None


@dataclass
class ExecutionPlan:
    """Multi-step execution plan"""

    id: str
    objective: str
    steps: List[PlanStep]
    total_cost: int
    created_at: datetime
    expires_at: datetime
    approved: bool = False
    approved_at: Optional[datetime] = None
    executed_steps: int = 0
    failed_steps: int = 0

    def is_expired(self) -> bool:
        """Check if plan has expired"""
        return datetime.now() > self.expires_at

    def remaining_cost(self) -> int:
        """Calculate remaining cost for unexecuted steps"""
        executed = self.executed_steps + self.failed_steps
        return sum(step.cost_estimate for step in self.steps[executed:])


@dataclass
class PlanConsentRequest:
    """User consent request for plan"""

    plan: ExecutionPlan
    user_callback: Optional[Callable[[ExecutionPlan], bool]] = None
    timeout_s: int = 300  # 5 minute timeout
    require_confirmation: bool = True
    high_risk_steps: List[PlanStep] = field(default_factory=list)


# ============================================================================
# PLAN GENERATOR
# ============================================================================


class PlanGenerator:
    """Generate multi-step execution plans from objectives"""

    def __init__(self, llm, tool_registry):
        """
        Initialize plan generator

        Args:
            llm: LLM backend with generate(prompt, max_tokens) method
            tool_registry: Tool registry for available actions
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.plan_counter = 0

    async def generate(
        self, objective: str, context: Dict[str, Any], max_steps: int = 10, budget_tokens: int = 20
    ) -> ExecutionPlan:
        """
        Generate execution plan for objective

        Args:
            objective: User's goal/objective
            context: Contextual information for planning
            max_steps: Maximum steps in plan
            budget_tokens: Total budget tokens available

        Returns:
            ExecutionPlan with steps and cost estimate
        """
        self.plan_counter += 1
        plan_id = f"plan_{self.plan_counter}"

        # Build prompt for plan generation
        prompt = self._build_prompt(objective, context, max_steps)

        logger.info("plan_generation_start", plan_id=plan_id, objective=objective)

        try:
            # Generate plan using LLM
            response = await asyncio.to_thread(self.llm.generate, prompt, max_tokens=1024)

            # Parse plan from response
            steps = self._parse_response(response, objective)

            # Validate and cost steps
            total_cost = 0
            for i, step in enumerate(steps):
                step.id = f"{plan_id}_step_{i}"
                step.cost_estimate = self._estimate_cost(step)
                total_cost += step.cost_estimate

            # Create plan
            plan = ExecutionPlan(
                id=plan_id,
                objective=objective,
                steps=steps[:max_steps],
                total_cost=min(total_cost, budget_tokens),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1),
            )

            logger.info(
                "plan_generation_complete",
                plan_id=plan_id,
                step_count=len(plan.steps),
                total_cost=plan.total_cost,
            )

            return plan

        except Exception as e:
            logger.error("plan_generation_failed", plan_id=plan_id, error=str(e))
            raise

    def _build_prompt(self, objective: str, context: Dict[str, Any], max_steps: int) -> str:
        """Build LLM prompt for plan generation"""
        return f"""Generate a step-by-step plan for: {objective}

Context:
{self._format_context(context)}

Requirements:
1. Maximum {max_steps} steps
2. Each step should be specific and actionable
3. Include error recovery if needed
4. Mark high-risk steps clearly

Format each step as:
- Description: [what to do]
- Tool: [tool name]
- Action: [action name]
- Risk: [low/medium/high]

Plan:"""

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt"""
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _parse_response(self, response: str, objective: str) -> List[PlanStep]:
        """Parse LLM response into plan steps"""
        steps = []

        # Simple parsing - in production, would be more sophisticated
        lines = response.split("\n")
        current_step = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_step:
                    steps.append(self._create_step(current_step, objective))
                    current_step = {}
            elif line.startswith("- Description:"):
                current_step["description"] = line.replace("- Description:", "").strip()
            elif line.startswith("- Tool:"):
                current_step["tool"] = line.replace("- Tool:", "").strip()
            elif line.startswith("- Action:"):
                current_step["action"] = line.replace("- Action:", "").strip()
            elif line.startswith("- Risk:"):
                risk_str = line.replace("- Risk:", "").strip().lower()
                current_step["risk"] = risk_str

        # Add last step
        if current_step:
            steps.append(self._create_step(current_step, objective))

        return steps

    def _create_step(self, data: Dict[str, Any], objective: str) -> PlanStep:
        """Create PlanStep from parsed data"""
        risk_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        risk_str = data.get("risk", "low").lower()
        return PlanStep(
            id="",  # Will be set by caller
            description=data.get("description", "Unknown action"),
            tool=data.get("tool", "unknown"),
            action=data.get("action", "unknown"),
            args={},
            risk_level=risk_map.get(risk_str, RiskLevel.MEDIUM),
            cost_estimate=0,  # Will be set by caller
        )

    def _estimate_cost(self, step: PlanStep) -> int:
        """Estimate budget cost for a step"""
        base_cost = 1

        # Risk multiplier
        risk_multiplier = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 5,
        }

        return base_cost * risk_multiplier.get(step.risk_level, 1)


# ============================================================================
# CONSENT MANAGER
# ============================================================================


class ConsentManager:
    """Manages user consent requests and approvals"""

    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize consent manager

        Args:
            callback: Optional callback for consent requests
        """
        self.callback = callback
        self.pending_requests: Dict[str, PlanConsentRequest] = {}
        self.approvals: Dict[str, bool] = {}

    async def request_approval(self, plan: ExecutionPlan, timeout_s: int = 300) -> bool:
        """
        Request user approval for plan

        Args:
            plan: Plan to request approval for
            timeout_s: Timeout for approval in seconds

        Returns:
            True if approved, False if rejected or timeout
        """
        request = PlanConsentRequest(plan=plan, user_callback=self.callback, timeout_s=timeout_s)

        self.pending_requests[plan.id] = request

        logger.info(
            "consent_request_issued",
            plan_id=plan.id,
            step_count=len(plan.steps),
            total_cost=plan.total_cost,
            timeout_s=timeout_s,
        )

        # Emit consent event
        from astra.core.event_bus import get_event_bus

        bus = get_event_bus()
        bus.emit(
            "astra.plan.consent_requested",
            {
                "plan_id": plan.id,
                "objective": plan.objective,
                "step_count": len(plan.steps),
                "total_cost": plan.total_cost,
                "high_risk_steps": [
                    s.id for s in plan.steps if s.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                ],
            },
        )

        # Wait for approval
        try:
            if self.callback:
                # Use callback if provided
                approved = await asyncio.wait_for(
                    asyncio.to_thread(self.callback, plan), timeout=timeout_s
                )
            else:
                # Auto-approve low-cost plans for testing
                approved = plan.total_cost <= 3
        except asyncio.TimeoutError:
            logger.warning("consent_request_timeout", plan_id=plan.id)
            approved = False

        # Record approval
        self.approvals[plan.id] = approved
        del self.pending_requests[plan.id]

        logger.info("consent_decision_made", plan_id=plan.id, approved=approved)

        # Emit approval event
        bus.emit("astra.plan.consent_decision", {"plan_id": plan.id, "approved": approved})

        return approved


# ============================================================================
# PLAN EXECUTOR
# ============================================================================


class PlanExecutor:
    """Executes approved plans with budget enforcement"""

    def __init__(self, tool_registry, event_bus):
        """
        Initialize plan executor

        Args:
            tool_registry: Tool registry for execution
            event_bus: Event bus for emissions
        """
        self.tool_registry = tool_registry
        self.event_bus = event_bus

    async def execute(
        self, plan: ExecutionPlan, budget_tokens: int, on_step_complete: Optional[Callable] = None
    ) -> bool:
        """
        Execute approved plan

        Args:
            plan: Plan to execute
            budget_tokens: Budget tokens available
            on_step_complete: Optional callback on step completion

        Returns:
            True if all steps succeeded, False otherwise
        """
        if not plan.approved:
            logger.error("execute_plan_not_approved", plan_id=plan.id)
            return False

        if plan.is_expired():
            logger.error("execute_plan_expired", plan_id=plan.id)
            return False

        logger.info(
            "execute_plan_start",
            plan_id=plan.id,
            step_count=len(plan.steps),
            budget_tokens=budget_tokens,
        )

        # Emit execution start event
        self.event_bus.emit(
            "astra.plan.execution_start",
            {"plan_id": plan.id, "objective": plan.objective, "step_count": len(plan.steps)},
        )

        remaining_budget = budget_tokens

        for i, step in enumerate(plan.steps):
            # Check budget
            if remaining_budget < step.cost_estimate:
                logger.warning(
                    "execute_plan_budget_exhausted",
                    plan_id=plan.id,
                    step_index=i,
                    remaining_budget=remaining_budget,
                )
                step.status = StepStatus.SKIPPED
                continue

            # Execute step
            success = await self._execute_step(step, plan)
            remaining_budget -= step.cost_estimate

            if success:
                plan.executed_steps += 1
            else:
                plan.failed_steps += 1

            # Call completion callback
            if on_step_complete:
                on_step_complete(step, success)

        success = plan.failed_steps == 0

        logger.info(
            "execute_plan_complete",
            plan_id=plan.id,
            executed_steps=plan.executed_steps,
            failed_steps=plan.failed_steps,
            success=success,
        )

        # Emit execution complete event
        self.event_bus.emit(
            "astra.plan.execution_complete",
            {
                "plan_id": plan.id,
                "executed_steps": plan.executed_steps,
                "failed_steps": plan.failed_steps,
                "success": success,
            },
        )

        return success

    async def _execute_step(self, step: PlanStep, plan: ExecutionPlan) -> bool:
        """Execute single plan step"""
        logger.info(
            "execute_step_start", plan_id=plan.id, step_id=step.id, description=step.description
        )

        # Emit step start event
        self.event_bus.emit(
            "astra.plan.step_execution_start",
            {"plan_id": plan.id, "step_id": step.id, "tool": step.tool, "action": step.action},
        )

        step.status = StepStatus.EXECUTING

        try:
            # Execute tool action
            result = await asyncio.to_thread(self._execute_tool, step.tool, step.action, step.args)

            step.status = StepStatus.SUCCESS
            step.result = result

            logger.info("execute_step_success", plan_id=plan.id, step_id=step.id)

            # Emit step success event
            self.event_bus.emit(
                "astra.plan.step_execution_success",
                {"plan_id": plan.id, "step_id": step.id, "result": result},
            )

            return True

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)

            logger.error("execute_step_failed", plan_id=plan.id, step_id=step.id, error=str(e))

            # Emit step failure event
            self.event_bus.emit(
                "astra.plan.step_execution_failed",
                {"plan_id": plan.id, "step_id": step.id, "error": str(e)},
            )

            return False

    def _execute_tool(self, tool: str, action: str, args: Dict[str, Any]) -> Any:
        """Execute tool action (blocking)"""
        # In production, would call actual tool
        return f"Executed {tool}.{action} with {args}"


# ============================================================================
# PLANNER L2 ORCHESTRATOR
# ============================================================================


class PlannerL2:
    """
    Multi-step planner with consent loop

    Architecture: PLAN -> ASK -> ACT
    - PLAN: Generate execution plan
    - ASK: Request user consent
    - ACT: Execute with budget enforcement
    """

    def __init__(self, llm, tool_registry, consent_callback: Optional[Callable] = None):
        """
        Initialize Planner L2

        Args:
            llm: LLM backend for plan generation
            tool_registry: Tool registry for execution
            consent_callback: Optional callback for consent requests
        """
        self.llm = llm
        self.tool_registry = tool_registry

        from astra.core.event_bus import get_event_bus

        self.event_bus = get_event_bus()

        self.generator = PlanGenerator(llm, tool_registry)
        self.consent_mgr = ConsentManager(consent_callback)
        self.executor = PlanExecutor(tool_registry, self.event_bus)

        logger.info("planner_l2_initialized")

    async def execute_objective(
        self,
        objective: str,
        context: Dict[str, Any] = None,
        budget_tokens: int = 20,
        max_steps: int = 10,
    ) -> bool:
        """
        Execute objective using Plan->Ask->Act workflow

        Args:
            objective: User's goal
            context: Optional contextual information
            budget_tokens: Budget tokens for plan execution
            max_steps: Maximum steps in plan

        Returns:
            True if execution succeeded, False otherwise
        """
        context = context or {}

        logger.info("planner_l2_objective_start", objective=objective, budget_tokens=budget_tokens)

        try:
            # PLAN: Generate execution plan
            logger.info("planner_l2_phase_plan")
            plan = await self.generator.generate(objective, context, max_steps, budget_tokens)

            # ASK: Request user consent
            logger.info("planner_l2_phase_ask")
            approved = await self.consent_mgr.request_approval(plan)

            if not approved:
                logger.info("planner_l2_objective_rejected", objective=objective)
                return False

            # Mark plan as approved
            plan.approved = True
            plan.approved_at = datetime.now()

            # ACT: Execute plan
            logger.info("planner_l2_phase_act")
            success = await self.executor.execute(plan, budget_tokens)

            logger.info("planner_l2_objective_complete", objective=objective, success=success)

            return success

        except Exception as e:
            logger.error("planner_l2_objective_failed", objective=objective, error=str(e))
            return False
