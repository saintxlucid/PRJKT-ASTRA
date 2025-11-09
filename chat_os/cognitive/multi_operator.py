"""
Multi-Operator Sovereignty System

Phase 4: Parallel execution of multiple operators with cognitive resource balancing.
Each operator maintains independent cognitive state with shared emotional context.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chat_os.cognitive.emotion.context_engine import EmotionalContextEngine
from chat_os.cognitive.meta_controller import CognitiveGovernor, MetaController, Task
from chat_os.executor import ExecutionContext


class OperatorStatus(Enum):
    """Status of an operator instance."""

    IDLE = "idle"
    BUSY = "busy"
    WAITING = "waiting"
    PAUSED = "paused"
    TERMINATED = "terminated"


class OperatorPriority(Enum):
    """Priority level for operator scheduling."""

    CRITICAL = 1  # Immediate execution
    HIGH = 2  # Execute soon
    NORMAL = 3  # Standard priority
    LOW = 4  # Execute when resources available
    BACKGROUND = 5  # Execute only when idle


@dataclass
class ResourceLimits:
    """Resource constraints for an operator."""

    max_cpu_percent: float = 25.0  # Max CPU usage per operator
    max_memory_mb: float = 512.0  # Max memory in MB
    max_token_budget: int = 100000  # Max tokens per session
    max_execution_time_ms: float = 60000  # Max execution time (1 minute)
    max_concurrent_tasks: int = 3  # Max parallel tasks


@dataclass
class ResourceUsage:
    """Current resource usage of an operator."""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    tokens_used: int = 0
    execution_time_ms: float = 0.0
    active_tasks: int = 0

    def exceeds(self, limits: ResourceLimits) -> bool:
        """Check if any resource limit is exceeded."""
        return (
            self.cpu_percent > limits.max_cpu_percent
            or self.memory_mb > limits.max_memory_mb
            or self.tokens_used > limits.max_token_budget
            or self.execution_time_ms > limits.max_execution_time_ms
            or self.active_tasks >= limits.max_concurrent_tasks
        )

    def utilization_ratio(self, limits: ResourceLimits) -> float:
        """Calculate overall resource utilization (0.0-1.0+)."""
        ratios = [
            self.cpu_percent / limits.max_cpu_percent,
            self.memory_mb / limits.max_memory_mb,
            self.tokens_used / limits.max_token_budget,
            self.execution_time_ms / limits.max_execution_time_ms,
            self.active_tasks / max(limits.max_concurrent_tasks, 1),
        ]
        return sum(ratios) / len(ratios)


@dataclass
class OperatorInstance:
    """
    Independent operator with its own cognitive state.

    Each operator maintains:
    - Unique ID and name
    - Independent execution context
    - Resource limits and usage tracking
    - Priority and status
    - Cognitive components (governor, meta-controller)
    """

    operator_id: str
    name: str
    priority: OperatorPriority = OperatorPriority.NORMAL
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    status: OperatorStatus = field(default=OperatorStatus.IDLE, init=False)
    usage: ResourceUsage = field(default_factory=ResourceUsage, init=False)

    # Cognitive state (independent per operator)
    governor: CognitiveGovernor | None = field(default=None, init=False)
    meta_controller: MetaController | None = field(default=None, init=False)
    execution_context: ExecutionContext | None = field(default=None, init=False)

    # Timing
    created_at: float = field(default_factory=time.time, init=False)
    last_active: float = field(default_factory=time.time, init=False)

    # Task queue
    pending_tasks: list[Task] = field(default_factory=list, init=False)
    completed_tasks: list[Task] = field(default_factory=list, init=False)

    def initialize_cognitive_components(
        self, emotion_engine: EmotionalContextEngine, lucid_weights: dict[str, float]
    ) -> None:
        """Initialize this operator's cognitive components."""
        from chat_os.cognitive.meta_controller import (
            ProceduralEngine,
            StatisticalEngine,
            SymbolicEngine,
        )

        # Independent governor with shared emotion awareness
        self.governor = CognitiveGovernor(
            lucid_weights=lucid_weights, emotion_engine=emotion_engine
        )

        # Independent reasoning engines
        symbolic = SymbolicEngine()
        statistical = StatisticalEngine(self.governor)
        procedural = ProceduralEngine()

        self.meta_controller = MetaController(
            governor=self.governor,
            symbolic=symbolic,
            statistical=statistical,
            procedural=procedural,
        )

    def submit_task(self, task: Task) -> None:
        """Submit a task to this operator's queue."""
        self.pending_tasks.append(task)
        self.last_active = time.time()

    def can_accept_task(self) -> bool:
        """Check if operator can accept another task."""
        if self.status == OperatorStatus.TERMINATED:
            return False
        if self.usage.exceeds(self.limits):
            return False
        return True

    def age_seconds(self) -> float:
        """Age of this operator in seconds."""
        return time.time() - self.created_at

    def idle_seconds(self) -> float:
        """Time since last activity in seconds."""
        return time.time() - self.last_active


@dataclass
class OperatorPool:
    """
    Pool of operator instances with resource balancing.

    Manages:
    - Operator lifecycle (create, schedule, terminate)
    - Resource allocation and balancing
    - Task scheduling across operators
    - Shared emotional context hub
    """

    max_operators: int = 5
    default_limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Operator registry
    operators: dict[str, OperatorInstance] = field(default_factory=dict, init=False)

    # Shared emotional context
    emotion_hub: EmotionalContextEngine = field(default_factory=EmotionalContextEngine, init=False)

    # Lucid configuration (shared)
    lucid_weights: dict[str, float] = field(
        default_factory=lambda: {
            "truth_compassion": 0.5,
            "logic_intuition": 0.4,
            "order_freedom": 0.4,
            "efficiency_safety": 0.6,
        },
        init=False,
    )

    def create_operator(
        self,
        name: str,
        priority: OperatorPriority = OperatorPriority.NORMAL,
        limits: ResourceLimits | None = None,
    ) -> OperatorInstance:
        """
        Create a new operator instance.

        Args:
            name: Human-readable operator name
            priority: Scheduling priority
            limits: Resource limits (uses defaults if None)

        Returns:
            New operator instance
        """
        if len(self.operators) >= self.max_operators:
            raise RuntimeError(f"Operator pool full (max: {self.max_operators})")

        operator_id = str(uuid.uuid4())[:8]
        operator = OperatorInstance(
            operator_id=operator_id,
            name=name,
            priority=priority,
            limits=limits or self.default_limits,
        )

        # Initialize with shared emotion hub
        operator.initialize_cognitive_components(self.emotion_hub, self.lucid_weights)

        self.operators[operator_id] = operator
        return operator

    def get_operator(self, operator_id: str) -> OperatorInstance | None:
        """Get operator by ID."""
        return self.operators.get(operator_id)

    def list_operators(self, status: OperatorStatus | None = None) -> list[OperatorInstance]:
        """
        List all operators, optionally filtered by status.

        Args:
            status: Filter by status (None for all)

        Returns:
            List of operators
        """
        ops = list(self.operators.values())
        if status is not None:
            ops = [op for op in ops if op.status == status]
        return ops

    def terminate_operator(self, operator_id: str) -> bool:
        """
        Terminate an operator and clean up resources.

        Args:
            operator_id: ID of operator to terminate

        Returns:
            True if terminated, False if not found
        """
        operator = self.operators.get(operator_id)
        if not operator:
            return False

        operator.status = OperatorStatus.TERMINATED
        operator.pending_tasks.clear()

        # Clean up cognitive components
        operator.governor = None
        operator.meta_controller = None
        operator.execution_context = None

        del self.operators[operator_id]
        return True

    def find_available_operator(
        self, priority: OperatorPriority = OperatorPriority.NORMAL
    ) -> OperatorInstance | None:
        """
        Find the best available operator for a task.

        Selection criteria:
        1. Must be able to accept tasks (not over limits)
        2. Prefer matching priority
        3. Prefer IDLE over BUSY
        4. Prefer lower resource utilization

        Args:
            priority: Desired priority level

        Returns:
            Best available operator, or None if all busy
        """
        candidates = [op for op in self.operators.values() if op.can_accept_task()]

        if not candidates:
            return None

        # Score operators (lower is better)
        def score_operator(op: OperatorInstance) -> tuple[int, int, float]:
            # 1. Priority mismatch penalty
            priority_penalty = abs(op.priority.value - priority.value)

            # 2. Status preference (IDLE=0, BUSY=1)
            status_penalty = 0 if op.status == OperatorStatus.IDLE else 1

            # 3. Resource utilization
            utilization = op.usage.utilization_ratio(op.limits)

            return (priority_penalty, status_penalty, utilization)

        return min(candidates, key=score_operator)

    def schedule_task(
        self, task: Task, priority: OperatorPriority = OperatorPriority.NORMAL
    ) -> OperatorInstance | None:
        """
        Schedule a task to an available operator.

        Args:
            task: Task to schedule
            priority: Priority level

        Returns:
            Operator that accepted the task, or None if pool full
        """
        operator = self.find_available_operator(priority)
        if operator:
            operator.submit_task(task)
            operator.status = OperatorStatus.BUSY
        return operator

    def get_pool_stats(self) -> dict[str, Any]:
        """
        Get pool-wide statistics.

        Returns:
            Dict with operator counts, resource usage, etc.
        """
        total_operators = len(self.operators)
        status_counts = {}
        for status in OperatorStatus:
            count = len([op for op in self.operators.values() if op.status == status])
            status_counts[status.value] = count

        total_usage = ResourceUsage()
        for op in self.operators.values():
            total_usage.cpu_percent += op.usage.cpu_percent
            total_usage.memory_mb += op.usage.memory_mb
            total_usage.tokens_used += op.usage.tokens_used
            total_usage.active_tasks += op.usage.active_tasks

        # Get current emotional context for pool-wide awareness
        emotion_data = self.emotion_hub.infer()
        
        return {
            "total_operators": total_operators,
            "max_operators": self.max_operators,
            "status_counts": status_counts,
            "total_cpu_percent": total_usage.cpu_percent,
            "total_memory_mb": total_usage.memory_mb,
            "total_tokens_used": total_usage.tokens_used,
            "total_active_tasks": total_usage.active_tasks,
            "emotion_context": emotion_data.get("state", "unknown"),
        }

    def rebalance_operators(self) -> None:
        """
        Rebalance tasks across operators.

        Moves pending tasks from overloaded operators to available ones.
        """
        overloaded = [
            op for op in self.operators.values() if op.usage.exceeds(op.limits) and op.pending_tasks
        ]
        available = [op for op in self.operators.values() if op.can_accept_task()]

        for overloaded_op in overloaded:
            while overloaded_op.pending_tasks and available:
                task = overloaded_op.pending_tasks.pop(0)
                target_op = self.find_available_operator(overloaded_op.priority)
                if target_op:
                    target_op.submit_task(task)

    async def execute_operator_task(self, operator: OperatorInstance, task: Task) -> Any:
        """
        Execute a task on a specific operator.

        Args:
            operator: Operator to execute on
            task: Task to execute

        Returns:
            Task execution result
        """
        if not operator.meta_controller:
            raise RuntimeError(f"Operator {operator.operator_id} not initialized")

        start_time = time.time()
        operator.status = OperatorStatus.BUSY
        operator.usage.active_tasks += 1

        try:
            # Route and execute task through operator's meta-controller
            _mode = operator.meta_controller.route(task)  # Determine reasoning mode
            result = operator.meta_controller.run(task)  # Execute with selected mode

            # Update usage
            elapsed_ms = (time.time() - start_time) * 1000
            operator.usage.execution_time_ms += elapsed_ms

            # Mark completed
            operator.completed_tasks.append(task)
            operator.last_active = time.time()

            return result

        finally:
            operator.usage.active_tasks -= 1
            if not operator.pending_tasks and operator.usage.active_tasks == 0:
                operator.status = OperatorStatus.IDLE


# Global operator pool singleton
_operator_pool: OperatorPool | None = None


def get_operator_pool() -> OperatorPool:
    """Get global operator pool singleton."""
    global _operator_pool
    if _operator_pool is None:
        _operator_pool = OperatorPool()
    return _operator_pool
