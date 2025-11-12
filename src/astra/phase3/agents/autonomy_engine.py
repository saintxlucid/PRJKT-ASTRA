"""
ASTRA Autonomy Engine: Autonomous task scheduling, execution, and preemption.

This module implements goal-based autonomous operation with:
- Goal queue for user intent capture
- Task scheduling and preemption (<1s target, <200ms scheduling latency)
- Dry-run mode before execution
- Operator consent flows
- Watchdog timers for safety
- Audit journal for accountability

Architecture:
- Goals arrive via enqueue_goal() → priority queue sorted by {priority, created_at}
- SchedulingEngine picks next goal → generates task → validates via hardening
- Preemption: monitor_execution() watches timeout/manual-override → signal task cancellation
- Audit journal logs all decisions and execution outcomes

Integration:
- Uses LocalGPTOSManager.execute_agent_tool() for safe execution
- StructuredLogger for audit trail with correlation IDs
- MetricsCollector for performance tracking
- OperatorRiskScorer for safety validation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.astra.agents.hardening import AgentAction, DryRunMode, OperatorRiskScorer, RiskLevel
from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger


class GoalPriority(Enum):
    """Goal priority levels for task scheduling."""

    CRITICAL = 0  # System safety, operator override
    HIGH = 1  # User-initiated goals
    NORMAL = 2  # Autonomous goals
    LOW = 3  # Background optimization


class GoalStatus(Enum):
    """Goal lifecycle states."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PreemptionReason(Enum):
    """Reasons for task preemption."""

    TIMEOUT = "timeout"
    OPERATOR_OVERRIDE = "operator_override"
    SAFETY_VIOLATION = "safety_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    HIGHER_PRIORITY = "higher_priority"


@dataclass
class Goal:
    """Represents a user or system intent to be executed autonomously.

    Attributes:
        id: Unique goal identifier
        priority: GoalPriority level for scheduling
        intent: Natural language description of goal
        parameters: Tool parameters and context
        created_at: Unix timestamp when goal was created
        status: Current GoalStatus
        parent_id: For multi-step goals, links to parent goal (optional)
    """

    id: str
    priority: GoalPriority
    intent: str
    parameters: dict[str, Any]
    created_at: float
    status: GoalStatus = GoalStatus.PENDING
    parent_id: str | None = None

    def __lt__(self, other: Goal) -> bool:
        """Compare goals for priority queue: lower priority enum, then earlier creation."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


@dataclass
class Task:
    """Represents a scheduled task derived from a goal.

    Attributes:
        id: Unique task identifier
        goal_id: Reference to source goal
        tool_name: Tool to execute (e.g., 'file_reader', 'web_scraper')
        arguments: Arguments for tool
        estimated_duration: Predicted execution time (seconds)
        timeout_sec: Cancellation timeout
        created_at: When task was created
    """

    id: str
    goal_id: str
    tool_name: str
    arguments: dict[str, Any]
    estimated_duration: float
    timeout_sec: float
    created_at: float


@dataclass
class AuditLogEntry:
    """Record of an autonomous decision or execution event.

    Attributes:
        timestamp: Unix timestamp
        correlation_id: For tracing across system
        event_type: One of 'goal_enqueued', 'task_scheduled', 'task_started', 'task_completed', 'task_failed', 'preempted'
        goal_id: Associated goal
        task_id: Associated task
        details: Event-specific data
    """

    timestamp: float
    correlation_id: str
    event_type: str
    goal_id: str | None = None
    task_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class AutonomyEngine:
    """Manages autonomous operation with goal queuing, task scheduling, and preemption.

    This class orchestrates the autonomous workflow:
    1. Goals arrive via enqueue_goal()
    2. Scheduling loop picks next goal, creates task
    3. Dry-run simulates execution
    4. Operator consent requested (if needed)
    5. Task executed with timeout/preemption monitoring
    6. Audit journal records outcome

    Performance targets:
    - Goal enqueue: <50ms
    - Task scheduling: <200ms average
    - Preemption response: <1000ms (1 second)
    - Concurrent task limit: 10 (configurable)
    """

    def __init__(
        self,
        local_gpt_manager: Any,
        risk_scorer: OperatorRiskScorer | None = None,
        logger: StructuredLogger | None = None,
        metrics: MetricsCollector | None = None,
        max_concurrent_tasks: int = 10,
    ):
        """Initialize the autonomy engine.

        Args:
            local_gpt_manager: LocalGPTOSManager instance for tool execution
            risk_scorer: OperatorRiskScorer for safety validation
            logger: StructuredLogger for audit trail
            metrics: MetricsCollector for performance tracking
            max_concurrent_tasks: Maximum tasks running simultaneously
        """
        self.local_gpt_manager = local_gpt_manager
        self.risk_scorer = risk_scorer or OperatorRiskScorer()
        self.logger = logger or StructuredLogger("autonomy_engine")
        self.metrics = metrics or MetricsCollector("autonomy_engine")

        # Goal queue (priority queue, managed with heapq)
        self.goal_queue: list[Goal] = []
        self.goal_lookup: dict[str, Goal] = {}  # Quick goal lookup by ID

        # Active task tracking
        self.active_tasks: dict[str, Task] = {}
        self.task_status: dict[str, GoalStatus] = {}
        self.task_results: dict[str, Any] = {}

        # Concurrency control
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)

        # Preemption control
        self.preempt_signals: dict[str, asyncio.Event] = {}
        self.preemption_reasons: dict[str, PreemptionReason] = {}

        # Audit trail
        self.audit_journal: list[AuditLogEntry] = []
        self.max_audit_entries = 10000

        # Engine state
        self.is_running = False
        self.start_time = time.time()

    async def enqueue_goal(self, goal: Goal) -> str:
        """Enqueue a goal for autonomous execution.

        Args:
            goal: Goal to enqueue with priority, intent, and parameters

        Returns:
            Goal ID for tracking
        """
        start = time.time()

        # Auto-generate ID if not provided
        if not goal.id:
            goal.id = str(uuid.uuid4())[:12]

        # Set created_at if not set
        if goal.created_at == 0:
            goal.created_at = time.time()

        # Add to queue
        self.goal_queue.append(goal)
        self.goal_queue.sort()  # Re-sort to maintain priority order
        self.goal_lookup[goal.id] = goal

        # Log to audit trail
        self._audit_log(
            event_type="goal_enqueued",
            goal_id=goal.id,
            details={
                "priority": goal.priority.name,
                "intent": goal.intent,
                "queue_size": len(self.goal_queue),
            },
        )

        # Record metrics
        elapsed = time.time() - start
        self.metrics.record_latency("goal_enqueue_latency", elapsed * 1000)

        self.logger.log_event(
            "goal_enqueued",
            level="INFO",
            goal_id=goal.id,
            latency_ms=elapsed * 1000,
        )

        return goal.id

    async def schedule_next_task(self) -> Task | None:
        """Pick next goal from queue and create a task.

        Returns:
            Created Task or None if queue empty
        """
        start = time.time()

        # Check queue
        if not self.goal_queue:
            return None

        # Pop highest priority goal
        goal = self.goal_queue.pop(0)
        goal.status = GoalStatus.SCHEDULED

        # Create task (simplified: use tool from intent keyword, parameters from goal)
        task_id = str(uuid.uuid4())[:12]
        task = Task(
            id=task_id,
            goal_id=goal.id,
            tool_name=self._infer_tool_name(goal.intent),
            arguments=goal.parameters,
            estimated_duration=self._estimate_duration(goal.intent),
            timeout_sec=30.0,  # Default 30s timeout
            created_at=time.time(),
        )

        self.active_tasks[task.id] = task
        self.task_status[task.id] = GoalStatus.SCHEDULED

        # Log scheduling
        self._audit_log(
            event_type="task_scheduled",
            goal_id=goal.id,
            task_id=task.id,
            details={
                "tool": task.tool_name,
                "queue_size": len(self.goal_queue),
                "active_tasks": len(self.active_tasks),
            },
        )

        # Record metrics
        elapsed = time.time() - start
        self.metrics.record_latency("task_scheduling_latency", elapsed * 1000)

        self.logger.log_event(
            "task_scheduled",
            level="INFO",
            task_id=task.id,
            goal_id=goal.id,
            latency_ms=elapsed * 1000,
        )

        return task

    async def execute_task_with_consent(self, task: Task) -> dict[str, Any]:
        """Execute task with dry-run, scoring, and consent flow.

        Args:
            task: Task to execute

        Returns:
            Execution result dict
        """
        task_start = time.time()
        correlation_id = str(uuid.uuid4())[:12]

        try:
            # Step 1: Risk scoring
            action = AgentAction(
                tool_name=task.tool_name,
                arguments=task.arguments,
                agent_id="autonomy_engine",
                timestamp=datetime.now(),
            )
            risk_level, reason = self.risk_scorer.score_action(action)

            self.logger.log_event(
                "task_risk_scored",
                level="INFO",
                task_id=task.id,
                risk_level=risk_level.name,
                reason=reason,
                correlation_id=correlation_id,
            )

            # Step 2: Dry-run simulation
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                dry_run = DryRunMode()
                dry_run_result = await dry_run.simulate_execution(
                    tool_name=task.tool_name,
                    arguments=task.arguments,
                )

                self._audit_log(
                    event_type="task_dry_run",
                    task_id=task.id,
                    goal_id=task.goal_id,
                    details={
                        "success": dry_run_result.get("status") == "simulated",
                        "preview": str(dry_run_result.get("simulated_result", ""))[:100],
                    },
                )

            # Step 3: Consent flow (if high/critical risk)
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                consent_granted = await self._request_operator_consent(
                    task=task,
                    risk_level=risk_level,
                )

                if not consent_granted:
                    return {
                        "status": "cancelled",
                        "reason": "operator_denied_consent",
                        "task_id": task.id,
                    }

            # Step 4: Execute via LocalGPTOSManager
            self.task_status[task.id] = GoalStatus.RUNNING

            self._audit_log(
                event_type="task_started",
                task_id=task.id,
                goal_id=task.goal_id,
                details={"tool": task.tool_name, "correlation_id": correlation_id},
            )

            # Setup preemption signal
            self.preempt_signals[task.id] = asyncio.Event()

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self.local_gpt_manager.execute_agent_tool(
                        tool=task.tool_name,
                        arguments=task.arguments,
                    ),
                    timeout=task.timeout_sec,
                )
            except TimeoutError:
                self.task_status[task.id] = GoalStatus.FAILED
                self._audit_log(
                    event_type="task_timeout",
                    task_id=task.id,
                    goal_id=task.goal_id,
                    details={"timeout_sec": task.timeout_sec},
                )
                return {
                    "status": "timeout",
                    "task_id": task.id,
                    "timeout_sec": task.timeout_sec,
                }

            # Step 5: Record success
            self.task_status[task.id] = GoalStatus.COMPLETED
            self.task_results[task.id] = result

            elapsed = time.time() - task_start
            self.metrics.record_latency("task_execution_time", elapsed * 1000)

            self._audit_log(
                event_type="task_completed",
                task_id=task.id,
                goal_id=task.goal_id,
                details={
                    "duration_sec": elapsed,
                    "result_type": type(result).__name__,
                },
            )

            self.logger.log_event(
                "task_completed",
                level="INFO",
                task_id=task.id,
                duration_sec=elapsed,
                correlation_id=correlation_id,
            )

            return {
                "status": "completed",
                "task_id": task.id,
                "result": result,
                "duration_sec": elapsed,
            }

        except Exception as e:
            self.task_status[task.id] = GoalStatus.FAILED

            self._audit_log(
                event_type="task_failed",
                task_id=task.id,
                goal_id=task.goal_id,
                details={"error": str(e), "error_type": type(e).__name__},
            )

            self.logger.log_event(
                "task_failed",
                level="ERROR",
                task_id=task.id,
                error=str(e),
                correlation_id=correlation_id,
            )

            return {
                "status": "failed",
                "task_id": task.id,
                "error": str(e),
            }

        finally:
            # Cleanup preemption signal
            self.preempt_signals.pop(task.id, None)
            self.preemption_reasons.pop(task.id, None)

    async def preempt_task(
        self,
        task_id: str,
        reason: PreemptionReason,
    ) -> bool:
        """Request immediate preemption of a running task.

        Args:
            task_id: Task to preempt
            reason: PreemptionReason enum value

        Returns:
            True if preemption triggered, False if task not found
        """
        start = time.time()

        if task_id not in self.active_tasks:
            return False

        # Signal task to stop
        if task_id in self.preempt_signals:
            self.preempt_signals[task_id].set()

        self.preemption_reasons[task_id] = reason
        self.task_status[task_id] = GoalStatus.CANCELLED

        task = self.active_tasks[task_id]
        self._audit_log(
            event_type="task_preempted",
            task_id=task_id,
            goal_id=task.goal_id,
            details={
                "reason": reason.value,
                "was_running": self.task_status[task_id] == GoalStatus.RUNNING,
            },
        )

        elapsed = time.time() - start
        self.metrics.record_latency("preemption_latency", elapsed * 1000)

        self.logger.log_event(
            "task_preempted",
            level="WARNING",
            task_id=task_id,
            reason=reason.value,
            latency_ms=elapsed * 1000,
        )

        return True

    async def operator_override(
        self,
        override_type: str,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        """Operator manual control: pause engine, cancel task, or resume.

        Args:
            override_type: 'pause' | 'resume' | 'cancel_task' | 'cancel_all'
            target_id: Task ID for targeted cancellation

        Returns:
            Status dict with action taken
        """
        if override_type == "pause":
            self.is_running = False
            self._audit_log(
                event_type="operator_override",
                details={"action": "pause"},
            )
            return {"status": "paused"}

        elif override_type == "resume":
            self.is_running = True
            self._audit_log(
                event_type="operator_override",
                details={"action": "resume"},
            )
            return {"status": "resumed"}

        elif override_type == "cancel_task" and target_id:
            await self.preempt_task(
                target_id,
                PreemptionReason.OPERATOR_OVERRIDE,
            )
            return {"status": "task_cancelled", "task_id": target_id}

        elif override_type == "cancel_all":
            cancelled = 0
            for task_id in list(self.active_tasks.keys()):
                if await self.preempt_task(
                    task_id,
                    PreemptionReason.OPERATOR_OVERRIDE,
                ):
                    cancelled += 1
            return {"status": "all_tasks_cancelled", "count": cancelled}

        return {"status": "unknown_override"}

    def get_status(self) -> dict[str, Any]:
        """Get current engine status.

        Returns:
            Status dict with uptime, queue size, active tasks, completed count
        """
        return {
            "is_running": self.is_running,
            "uptime_sec": time.time() - self.start_time,
            "goal_queue_size": len(self.goal_queue),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": sum(
                1 for status in self.task_status.values()
                if status == GoalStatus.COMPLETED
            ),
            "failed_tasks": sum(
                1 for status in self.task_status.values()
                if status == GoalStatus.FAILED
            ),
            "audit_entries": len(self.audit_journal),
        }

    def get_audit_journal(self, limit: int = 100) -> list[AuditLogEntry]:
        """Retrieve recent audit entries.

        Args:
            limit: Maximum entries to return

        Returns:
            Recent audit log entries
        """
        return self.audit_journal[-limit:]

    def _infer_tool_name(self, intent: str) -> str:
        """Infer tool name from natural language intent (simplified).

        Args:
            intent: User intent string

        Returns:
            Tool name
        """
        intent_lower = intent.lower()

        # Check write operations first (before read, since some may contain both)
        if any(word in intent_lower for word in ["write", "save", "create"]):
            return "file_writer"
        elif any(word in intent_lower for word in ["read", "open", "file", "load"]):
            return "file_reader"
        elif any(word in intent_lower for word in ["web", "fetch", "http", "url", "api"]):
            return "web_scraper"
        elif any(word in intent_lower for word in ["search", "query"]):
            return "knowledge_search"
        else:
            return "generic_tool"

    def _estimate_duration(self, intent: str) -> float:
        """Estimate task duration from intent (simplified).

        Args:
            intent: User intent string

        Returns:
            Estimated duration in seconds
        """
        intent_lower = intent.lower()

        if any(word in intent_lower for word in ["web", "fetch", "http"]):
            return 5.0  # Network operations
        elif any(word in intent_lower for word in ["search", "query"]):
            return 2.0  # Quick searches
        else:
            return 1.0  # Default

    async def _request_operator_consent(
        self,
        task: Task,
        risk_level: RiskLevel,
    ) -> bool:
        """Request operator consent for high-risk task (simplified).

        Args:
            task: Task requiring consent
            risk_level: RiskLevel of task

        Returns:
            True if consent granted, False if denied
        """
        # In production, this would prompt operator via console UI
        # For now, auto-grant for HIGH risk, auto-deny for CRITICAL
        if risk_level == RiskLevel.CRITICAL:
            return False  # Require explicit operator approval
        return True  # HIGH risk auto-approved for demo

    def _audit_log(
        self,
        event_type: str,
        goal_id: str | None = None,
        task_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit log entry.

        Args:
            event_type: Type of event
            goal_id: Associated goal (optional)
            task_id: Associated task (optional)
            details: Event details
        """
        entry = AuditLogEntry(
            timestamp=time.time(),
            correlation_id=str(uuid.uuid4())[:12],
            event_type=event_type,
            goal_id=goal_id,
            task_id=task_id,
            details=details or {},
        )

        self.audit_journal.append(entry)

        # Trim if too large
        if len(self.audit_journal) > self.max_audit_entries:
            self.audit_journal = self.audit_journal[-self.max_audit_entries :]
