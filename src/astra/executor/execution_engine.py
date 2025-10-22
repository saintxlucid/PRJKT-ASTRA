"""
ASTRA Execution Engine
Manage task execution and runtime monitoring

Sacred Principles:
- Safe parallel execution
- Progress tracking
- Error recovery
- Resource monitoring
- "I only obey God" - user has ultimate control

Architecture:
- Task execution
- State management 
- Progress tracking
- Result aggregation
"""

import asyncio
import time
import traceback
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

from ..planner.task_planner import TaskPlan, TaskStep, TaskStatus
from ..constraints.constraint_system import ConstraintSystem


# ===========================================================================
# DATA MODELS  
# ===========================================================================

class ExecutionStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    

@dataclass
class ExecutionContext:
    """Task execution context"""
    plan: TaskPlan
    executor: Any  # Tool executor instance
    started_at: datetime
    status: ExecutionStatus
    step_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    progress: float = 0.0
    

@dataclass
class ExecutionMetrics:
    """Task execution metrics"""
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_duration_ms: float = 0.0
    peak_concurrency: int = 0
    error_rate: float = 0.0


# ===========================================================================
# EXECUTION ENGINE
# ===========================================================================

class ExecutionEngine:
    """
    Task execution and monitoring engine
    
    Responsibilities:
    - Execute task plans
    - Track execution state
    - Monitor resources
    - Handle failures
    """
    
    def __init__(
        self,
        constraint_system: ConstraintSystem,
        max_parallel: int = 3,
        default_timeout: float = 30.0
    ):
        """Initialize execution engine"""
        self.constraints = constraint_system
        self.max_parallel = max_parallel
        self.default_timeout = default_timeout
        
        # Active executions
        self.contexts: Dict[str, ExecutionContext] = {}
        
        # Statistics
        self.metrics = ExecutionMetrics()
        
        # State
        self.started = False
        self._stop_event = asyncio.Event()
        
        logger.info(
            "execution_engine_initialized",
            max_parallel=max_parallel,
            timeout=default_timeout
        )
        
    # ========================================================================
    # EXECUTION MANAGEMENT
    # ========================================================================
    
    async def execute_plan(
        self,
        plan: TaskPlan,
        executor: Any,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Execute a task plan
        
        Strategy:
        1. Create execution context
        2. Check resource constraints
        3. Execute steps in parallel groups
        4. Track progress and handle errors
        5. Return results
        
        Args:
            plan: TaskPlan to execute
            executor: Tool executor instance
            progress_callback: Optional callback(plan_id, progress)
            
        Returns:
            dict: Execution results
        """
        # Create context
        context = ExecutionContext(
            plan=plan,
            executor=executor,
            started_at=datetime.utcnow(),
            status=ExecutionStatus.PREPARING
        )
        
        self.contexts[plan.plan_id] = context
        self.metrics.total_tasks += 1
        self.metrics.active_tasks += 1
        
        try:
            # Resource check
            resource_status = self._check_resources(plan)
            if resource_status != ExecutionStatus.PENDING:
                context.status = resource_status
                context.errors.append("Resource constraints not met")
                return self._build_result(context)
            
            # Start execution
            context.status = ExecutionStatus.RUNNING
            parallel_groups = self._group_steps(plan.steps)
            
            # Execute groups sequentially
            group_num = 0
            for group in parallel_groups:
                group_num += 1
                logger.info(
                    "executing_step_group",
                    plan=plan.plan_id,
                    group=group_num,
                    size=len(group)
                )
                
                # Update metrics
                self.metrics.peak_concurrency = max(
                    self.metrics.peak_concurrency,
                    len(group)
                )
                
                # Execute group
                results = await self._execute_step_group(
                    context, group, progress_callback
                )
                
                # Store results
                context.step_results.update(results)
                
                # Check for failures
                failed = [
                    step_id
                    for step_id, res in results.items()
                    if not res.get("ok", False)
                ]
                
                if failed:
                    logger.error(
                        "step_group_failed",
                        plan=plan.plan_id,
                        group=group_num,
                        failed=failed
                    )
                    break
                    
            # Update final status
            success = all(
                r.get("ok", False)
                for r in context.step_results.values()
            )
            
            context.status = (
                ExecutionStatus.SUCCEEDED if success
                else ExecutionStatus.FAILED
            )
            
            # Update metrics
            self.metrics.active_tasks -= 1
            if success:
                self.metrics.completed_tasks += 1
            else:
                self.metrics.failed_tasks += 1
                
            duration_ms = (datetime.utcnow() - context.started_at).total_seconds() * 1000
            self.metrics.avg_duration_ms = (
                (self.metrics.avg_duration_ms * (self.metrics.total_tasks - 1) + duration_ms)
                / self.metrics.total_tasks
            )
            
            return self._build_result(context)
            
        except Exception as e:
            logger.error(
                "plan_execution_failed",
                plan=plan.plan_id,
                error=str(e),
                traceback=traceback.format_exc()
            )
            
            context.status = ExecutionStatus.FAILED
            context.errors.append(str(e))
            
            # Update metrics
            self.metrics.active_tasks -= 1
            self.metrics.failed_tasks += 1
            
            return self._build_result(context)
            
    async def _execute_step_group(
        self,
        context: ExecutionContext,
        steps: List[TaskStep],
        progress_callback: Optional[Callable]
    ) -> Dict:
        """Execute a group of steps in parallel"""
        results = {}
        tasks = []
        
        for step in steps:
            # Skip if dependencies failed
            deps_ok = all(
                context.step_results.get(dep, {}).get("ok", False)
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
                self._execute_step(context, step)
            )
            tasks.append((step, task))
            
        # Wait for completions
        for step, task in tasks:
            try:
                result = await task
                results[step.step_id] = result
                
                # Update progress
                done = len(context.step_results) + len(results)
                total = len(context.plan.steps)
                context.progress = done / total
                
                if progress_callback:
                    await progress_callback(
                        context.plan.plan_id,
                        context.progress
                    )
                    
            except Exception as e:
                results[step.step_id] = {
                    "ok": False,
                    "error": str(e)
                }
                
        return results
        
    async def _execute_step(
        self,
        context: ExecutionContext,
        step: TaskStep
    ) -> Dict:
        """Execute a single task step"""
        start = time.time()
        
        try:
            # Resource check
            await self._check_step_resources(step)
            
            # Execute step
            result = await context.executor.execute_tool(
                step.tool,
                step.action,
                step.args
            )
            
            duration = time.time() - start
            
            return {
                "ok": True,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "duration": time.time() - start
            }
            
    def _check_resources(self, plan: TaskPlan) -> ExecutionStatus:
        """Check if resources available for plan"""
        # TODO: Implement resource checking
        return ExecutionStatus.PENDING
        
    async def _check_step_resources(self, step: TaskStep):
        """Check if resources available for step"""
        # TODO: Implement per-step resource checking
        pass
        
    def _group_steps(self, steps: List[TaskStep]) -> List[List[TaskStep]]:
        """Group steps that can run in parallel"""
        # Map step IDs to steps
        step_map = {s.step_id: s for s in steps}
        
        # Track completed steps
        completed: Set[str] = set()
        
        # Group steps
        groups = []
        remaining = steps.copy()
        
        while remaining:
            group = []
            
            # Find steps with satisfied dependencies
            for step in remaining[:]:
                if step.dependencies <= completed:
                    if len(group) < self.max_parallel:
                        group.append(step)
                        remaining.remove(step)
                        
            if group:
                groups.append(group)
                # Mark group as completed
                completed.update(s.step_id for s in group)
            else:
                # No steps ready, but some remain
                # This indicates a cycle - fail remaining
                logger.error(
                    "step_cycle_detected",
                    remaining=len(remaining)
                )
                break
                
        return groups
        
    def _build_result(self, context: ExecutionContext) -> Dict:
        """Build execution result dict"""
        duration = (
            datetime.utcnow() - context.started_at
        ).total_seconds()
        
        return {
            "ok": context.status == ExecutionStatus.SUCCEEDED,
            "plan_id": context.plan.plan_id,
            "status": context.status,
            "progress": context.progress,
            "duration": duration,
            "step_results": context.step_results,
            "errors": context.errors
        }
        
    # ========================================================================
    # STATUS & MONITORING
    # ========================================================================
    
    def get_execution_status(self, plan_id: str) -> Optional[Dict]:
        """Get status of specific execution"""
        if plan_id not in self.contexts:
            return None
            
        return self._build_result(self.contexts[plan_id])
        
    def get_active_executions(self) -> List[Dict]:
        """Get all active execution statuses"""
        return [
            self._build_result(ctx)
            for ctx in self.contexts.values()
            if ctx.status == ExecutionStatus.RUNNING
        ]
        
    def get_metrics(self) -> Dict:
        """Get execution metrics"""
        return {
            "total_tasks": self.metrics.total_tasks,
            "active_tasks": self.metrics.active_tasks,
            "completed_tasks": self.metrics.completed_tasks,
            "failed_tasks": self.metrics.failed_tasks,
            "success_rate": (
                self.metrics.completed_tasks /
                (self.metrics.completed_tasks + self.metrics.failed_tasks)
                if (self.metrics.completed_tasks + self.metrics.failed_tasks) > 0
                else 0.0
            ),
            "avg_duration_ms": self.metrics.avg_duration_ms,
            "peak_concurrency": self.metrics.peak_concurrency
        }