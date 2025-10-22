"""
ASTRA Task Planner Module
Decompose high-level tasks into executable steps

Sacred Principles:
- Cost-aware decomposition
- Resource-constrained planning
- Safety-first execution
- Predictable scheduling
- "I only obey God" - user has ultimate veto

Architecture:
- Task decomposition
- Cost estimation 
- Resource allocation
- Execution scheduling
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
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

class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    SCHEDULED = "scheduled" 
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:
    """Atomic unit of work"""
    step_id: str
    action: str  
    tool: str
    args: Dict = field(default_factory=dict)
    estimated_cost: float = 1.0
    dependencies: Set[str] = field(default_factory=set)
    timeout_seconds: float = 30.0
    retry_count: int = 0
    

@dataclass
class TaskPlan:
    """Complete execution plan"""
    plan_id: str
    objective: str
    steps: List[TaskStep]
    total_cost: float = 0.0
    estimated_duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING


# ===========================================================================
# TASK PLANNER
# ===========================================================================

class TaskPlanner:
    """
    Task decomposition and planning engine
    
    Responsibilities:
    - Break tasks into steps
    - Estimate costs
    - Allocate resources
    - Schedule execution
    """

    def __init__(
        self,
        tool_registry,
        max_parallel_steps: int = 3,
        max_retries: int = 2,
        default_timeout: float = 30.0
    ):
        """Initialize task planner"""
        self.tool_registry = tool_registry
        self.max_parallel = max_parallel_steps
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.active_plans: Dict[str, TaskPlan] = {}
        
        # Base cost matrix (tool.action -> estimated cost)
        self.cost_matrix = {
            "file.read": 1.0,
            "file.write": 2.0,
            "file.delete": 3.0,
            "process.start": 5.0,
            "process.kill": 3.0,
            "network.request": 2.0,
            "db.query": 2.0,
            "db.write": 4.0,
        }

        logger.info(
            "task_planner_initialized",
            max_parallel=max_parallel_steps,
            max_retries=max_retries
        )

    def create_plan(self, task: Dict) -> TaskPlan:
        """
        Create execution plan from task definition
        
        Strategy:
        1. Generate unique plan ID
        2. Extract objective and constraints
        3. Decompose into steps
        4. Calculate dependencies
        5. Estimate costs
        6. Create TaskPlan
        
        Args:
            task: Task definition dict with:
                - objective (str): What to accomplish
                - constraints (dict): Resource/timing limits
                - template (str, optional): Plan template name
                
        Returns:
            TaskPlan: Complete execution plan
        """
        # Create plan ID
        plan_id = str(uuid.uuid4())
        
        # Extract core fields
        objective = task["objective"]
        constraints = task.get("constraints", {})
        template = task.get("template")
        
        # Get template if specified
        if template and hasattr(self, 'plan_templates') and template in self.plan_templates:
            base_steps = self.plan_templates[template].copy()
        else:
            # Dynamic decomposition
            base_steps = self._decompose_task(objective, constraints)
            
        # Enhance steps with IDs and metadata
        steps = []
        for step in base_steps:
            step_id = f"{plan_id}.{step['tool']}.{step['action']}"
            
            # Create TaskStep
            task_step = TaskStep(
                step_id=step_id,
                action=step["action"],
                tool=step["tool"],
                args=step.get("args", {}),
                estimated_cost=self.estimate_cost(step),
                dependencies=set(step.get("depends_on", [])),
                timeout_seconds=step.get("timeout", self.default_timeout)
            )
            steps.append(task_step)
        
        # Calculate total cost
        total_cost = sum(step.estimated_cost for step in steps)
        
        # Estimate duration (simplified)
        parallel_groups = self._analyze_parallelism(steps)
        estimated_duration = sum(
            max(s.timeout_seconds for s in group)
            for group in parallel_groups
        )
        
        # Create plan
        plan = TaskPlan(
            plan_id=plan_id,
            objective=objective,
            steps=steps,
            total_cost=total_cost,
            estimated_duration=estimated_duration
        )
        
        # Register active plan
        self.active_plans[plan_id] = plan
        
        logger.info(
            "plan_created",
            plan_id=plan_id,
            steps=len(steps),
            cost=total_cost,
            duration=estimated_duration
        )
        
        return plan

    def estimate_cost(self, step: Dict) -> float:
        """
        Estimate computational cost of step
        
        Strategy:
        1. Get base cost from matrix
        2. Apply complexity multipliers
        3. Add resource penalties
        4. Scale by data size
        
        Args:
            step: Step definition with tool, action, args
            
        Returns:
            float: Estimated cost (higher = more expensive)
        """
        # Get base cost
        base_key = f"{step['tool']}.{step['action']}"
        base_cost = self.cost_matrix.get(base_key, 1.0)
        
        # Complexity multiplier
        args = step.get("args", {})
        if "recursive" in args and args["recursive"]:
            base_cost *= 2.0
        if "force" in args and args["force"]:
            base_cost *= 1.5
            
        # Resource penalties
        if "memory_mb" in args:
            memory_mb = float(args["memory_mb"])
            if memory_mb > 1000:
                base_cost *= 1.5
                
        # Data size scaling
        if "size_mb" in args:
            size_mb = float(args["size_mb"]) 
            if size_mb > 100:
                base_cost *= (size_mb / 100.0)
                
        return round(base_cost, 2)

    def _decompose_task(self, objective: str, constraints: Dict) -> List[Dict]:
        """
        Break task into atomic steps
        
        Strategy:
        1. Analyze objective text
        2. Match action patterns
        3. Extract dependencies
        4. Apply constraints
        
        Args:
            objective: Task objective string
            constraints: Resource/timing constraints
            
        Returns:
            list: Step definitions
        """
        # For demo, create generic test steps
        steps = [
            {
                "tool": "test",
                "action": "action1",
                "args": {"step": 1}
            },
            {
                "tool": "test",
                "action": "action2",
                "args": {"step": 2},
                "depends_on": ["step1"]
            }
        ]
        
        # Apply time constraints
        if "time_limit" in constraints:
            for step in steps:
                step["timeout"] = min(
                    step.get("timeout", self.default_timeout),
                    constraints["time_limit"] / len(steps)
                )
                
        return steps

    def _analyze_parallelism(self, steps: List[TaskStep]) -> List[List[TaskStep]]:
        """
        Group steps that can run in parallel
        
        Strategy:
        1. Build dependency graph
        2. Find independent step groups
        3. Respect max_parallel limit
        
        Args:
            steps: List of TaskSteps
            
        Returns:
            List of step groups that can run in parallel
        """
        # Map of step_id -> step
        step_map = {step.step_id: step for step in steps}
        
        # Find root steps (no dependencies)
        roots = [s for s in steps if not s.dependencies]
        
        groups = []
        current_group = []
        
        # Simple grouping - one level of parallelism
        for step in steps:
            # Start new group if current is full
            if len(current_group) >= self.max_parallel:
                groups.append(current_group)
                current_group = []
            
            # Add step to current group if no conflicts
            group_ids = {s.step_id for s in current_group}
            if not (step.dependencies & group_ids):
                current_group.append(step)
                
        # Add final group
        if current_group:
            groups.append(current_group)
            
        return groups

    async def execute_plan(
        self,
        plan: TaskPlan,
        progress_callback = None
    ) -> Dict:
        """
        Execute plan with progress tracking
        
        Strategy:
        1. Update plan status
        2. Group parallel steps
        3. Execute groups in sequence
        4. Track progress
        5. Handle failures
        
        Args:
            plan: TaskPlan to execute
            progress_callback: Optional callback(step_id, status)
            
        Returns:
            dict: Execution results
        """
        # Update status
        plan.status = TaskStatus.RUNNING
        
        # Get parallel groups
        groups = self._analyze_parallelism(plan.steps)
        
        results = {}
        group_num = 0
        
        try:
            # Execute groups sequentially
            for group in groups:
                group_num += 1
                logger.info(
                    "executing_step_group",
                    plan_id=plan.plan_id,
                    group=group_num,
                    size=len(group)
                )
                
                # Launch parallel steps
                tasks = []
                for step in group:
                    # Skip if dependencies failed
                    deps_ok = all(
                        results.get(dep, {}).get("ok", False)
                        for dep in step.dependencies
                    )
                    if not deps_ok:
                        results[step.step_id] = {
                            "ok": False,
                            "error": "Dependencies failed"
                        }
                        continue
                        
                    # Create execution task
                    task = asyncio.create_task(
                        self._execute_step(step, progress_callback)
                    )
                    tasks.append(task)
                    
                # Wait for group completion
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Store results
                for step, result in zip(group, group_results):
                    if isinstance(result, Exception):
                        results[step.step_id] = {
                            "ok": False,
                            "error": str(result)
                        }
                    else:
                        results[step.step_id] = result
                        
            # Update final status
            success = all(r.get("ok", False) for r in results.values())
            plan.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            
            return {
                "ok": success,
                "plan_id": plan.plan_id,
                "status": plan.status,
                "results": results
            }
            
        except Exception as e:
            logger.error(
                "plan_execution_failed",
                plan_id=plan.plan_id,
                error=str(e)
            )
            plan.status = TaskStatus.FAILED
            return {
                "ok": False,
                "plan_id": plan.plan_id,
                "status": plan.status,
                "error": str(e)
            }

    async def _execute_step(
        self,
        step: TaskStep,
        progress_callback = None
    ) -> Dict:
        """Execute single task step"""
        try:
            # Update progress
            if progress_callback:
                await progress_callback(step.step_id, "started")
            
            logger.info(
                "executing_step",
                step_id=step.step_id,
                tool=step.tool,
                action=step.action
            )
                
            # Execute via tool registry
            try:
                result = await self.tool_registry.execute(
                    name=f"{step.tool}.{step.action}",
                    args=step.args,
                    timeout=step.timeout_seconds
                )
                success = True
            except Exception as e:
                result = str(e)
                success = False
            
            execution_result = {
                "ok": success,
                "step_id": step.step_id,
                "result": result,
                "tool": step.tool,
                "action": step.action,
                "args": step.args
            }
            
            # Update progress
            status = "completed" if success else "failed"
            if progress_callback:
                await progress_callback(step.step_id, status)
                
            logger.info(
                "step_complete" if success else "step_failed",
                step_id=step.step_id,
                result=result
            )
                
            return execution_result
            
        except Exception as e:
            logger.error("step_execution_error", error=str(e), exc_info=True)
            if progress_callback:
                await progress_callback(step.step_id, "failed")
            raise

    def get_plan_status(self, plan_id: str) -> Optional[TaskPlan]:
        """Get current plan status"""
        return self.active_plans.get(plan_id)
        
    def list_active_plans(self) -> List[TaskPlan]:
        """Get all active plans"""
        return list(self.active_plans.values())


# ===========================================================================
# HELPERS
# ===========================================================================

    def create_task_step(
        self,
        action: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Set[str]] = None,
        timeout_seconds: Optional[float] = None,
        estimated_cost: Optional[float] = None
    ) -> TaskStep:
        """Create a new task step"""
        # Get tool info for cost if available
        if estimated_cost is None and self.tool_registry is not None:
            tool_name = f"{tool}.{action}"
            tool_info = self.tool_registry.get_tool_info(tool_name)
            if tool_info:
                estimated_cost = tool_info.cost_estimate
            else:
                estimated_cost = 1.0
                
        # Use registry timeout if available
        if timeout_seconds is None and self.tool_registry is not None:
            tool_name = f"{tool}.{action}"
            tool_info = self.tool_registry.get_tool_info(tool_name)
            if tool_info:
                timeout_seconds = tool_info.timeout
                
        return TaskStep(
            step_id=f"{tool}.{action}.{datetime.now().strftime('%H%M%S')}",
            action=action,
            tool=tool,
            args=args or {},
            estimated_cost=estimated_cost or 1.0,
            dependencies=dependencies or set(),
            timeout_seconds=timeout_seconds or self.default_timeout,
            retry_count=0
        )