"""
Tests for ASTRA Autonomy Engine: goal queuing, scheduling, execution, and preemption.

Test coverage includes:
- Goal enqueueing with priority ordering
- Task scheduling latency <200ms target
- Dry-run mode and consent flows
- Task execution with timeout/preemption
- Audit journal logging
- Operator override controls
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.astra.agents.hardening import OperatorRiskScorer, RiskLevel
from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger
from src.astra.phase3.agents.autonomy_engine import (
    AutonomyEngine,
    Goal,
    GoalPriority,
    GoalStatus,
    PreemptionReason,
    Task,
)


@pytest.fixture
def mock_local_gpt_manager():
    """Mock LocalGPTOSManager for testing."""
    manager = AsyncMock()
    manager.execute_agent_tool = AsyncMock(return_value={"status": "success", "data": "test"})
    return manager


@pytest.fixture
def mock_risk_scorer():
    """Mock OperatorRiskScorer."""
    scorer = MagicMock(spec=OperatorRiskScorer)
    scorer.score_action = MagicMock(return_value=(RiskLevel.NORMAL, "normal_risk"))
    return scorer


@pytest.fixture
def mock_logger():
    """Mock StructuredLogger."""
    logger = MagicMock(spec=StructuredLogger)
    logger.log_event = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Mock MetricsCollector."""
    metrics = MagicMock(spec=MetricsCollector)
    metrics.record_latency = MagicMock()
    return metrics


@pytest.fixture
def autonomy_engine(mock_local_gpt_manager, mock_risk_scorer, mock_logger, mock_metrics):
    """Create AutonomyEngine instance for testing."""
    engine = AutonomyEngine(
        local_gpt_manager=mock_local_gpt_manager,
        risk_scorer=mock_risk_scorer,
        logger=mock_logger,
        metrics=mock_metrics,
        max_concurrent_tasks=5,
    )
    return engine


class TestGoalEnqueuing:
    """Test goal enqueueing and priority ordering."""

    @pytest.mark.asyncio
    async def test_enqueue_single_goal(self, autonomy_engine):
        """Enqueue single goal successfully."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.HIGH,
            intent="read the data",
            parameters={"file": "data.txt"},
            created_at=time.time(),
        )

        goal_id = await autonomy_engine.enqueue_goal(goal)

        assert goal_id == "goal-1"
        assert len(autonomy_engine.goal_queue) == 1
        assert autonomy_engine.goal_queue[0].id == "goal-1"

    @pytest.mark.asyncio
    async def test_enqueue_multiple_goals_priority_ordering(self, autonomy_engine):
        """Enqueue multiple goals and verify priority ordering."""
        goal_low = Goal(
            id="goal-low",
            priority=GoalPriority.LOW,
            intent="background task",
            parameters={},
            created_at=time.time(),
        )
        goal_critical = Goal(
            id="goal-critical",
            priority=GoalPriority.CRITICAL,
            intent="system safety",
            parameters={},
            created_at=time.time() + 0.1,  # Later timestamp
        )
        goal_high = Goal(
            id="goal-high",
            priority=GoalPriority.HIGH,
            intent="user task",
            parameters={},
            created_at=time.time() + 0.2,
        )

        await autonomy_engine.enqueue_goal(goal_low)
        await autonomy_engine.enqueue_goal(goal_high)
        await autonomy_engine.enqueue_goal(goal_critical)

        # Should be ordered: CRITICAL, HIGH, LOW
        assert len(autonomy_engine.goal_queue) == 3
        assert autonomy_engine.goal_queue[0].priority == GoalPriority.CRITICAL
        assert autonomy_engine.goal_queue[1].priority == GoalPriority.HIGH
        assert autonomy_engine.goal_queue[2].priority == GoalPriority.LOW

    @pytest.mark.asyncio
    async def test_goal_enqueue_latency_metric(self, autonomy_engine, mock_metrics):
        """Verify goal enqueue latency is recorded."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.NORMAL,
            intent="test",
            parameters={},
            created_at=time.time(),
        )

        await autonomy_engine.enqueue_goal(goal)

        mock_metrics.record_latency.assert_called()
        call_args = mock_metrics.record_latency.call_args
        assert call_args[0][0] == "goal_enqueue_latency"


class TestTaskScheduling:
    """Test task scheduling and latency."""

    @pytest.mark.asyncio
    async def test_schedule_next_task_from_queue(self, autonomy_engine):
        """Schedule next task picks highest priority goal."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.HIGH,
            intent="fetch data via HTTP from API endpoint",
            parameters={"source": "api"},
            created_at=time.time(),
        )

        await autonomy_engine.enqueue_goal(goal)
        task = await autonomy_engine.schedule_next_task()

        assert task is not None
        assert task.goal_id == "goal-1"
        assert task.tool_name == "web_scraper"  # Inferred from "HTTP" in intent
        assert task in autonomy_engine.active_tasks.values()

    @pytest.mark.asyncio
    async def test_schedule_empty_queue_returns_none(self, autonomy_engine):
        """Schedule from empty queue returns None."""
        task = await autonomy_engine.schedule_next_task()
        assert task is None

    @pytest.mark.asyncio
    async def test_scheduling_latency_under_200ms(self, autonomy_engine, mock_metrics):
        """Verify task scheduling latency meets <200ms target."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.NORMAL,
            intent="process data",
            parameters={},
            created_at=time.time(),
        )

        await autonomy_engine.enqueue_goal(goal)

        start = time.time()
        task = await autonomy_engine.schedule_next_task()
        elapsed = time.time() - start

        assert task is not None
        assert elapsed < 0.2  # 200ms target
        assert mock_metrics.record_latency.called

    @pytest.mark.asyncio
    async def test_infer_tool_name_read(self, autonomy_engine):
        """Infer tool name for read operations."""
        tool = autonomy_engine._infer_tool_name("read the file from disk")
        assert tool == "file_reader"

    @pytest.mark.asyncio
    async def test_infer_tool_name_write(self, autonomy_engine):
        """Infer tool name for write operations."""
        tool = autonomy_engine._infer_tool_name("write data to file")
        assert tool == "file_writer"

    @pytest.mark.asyncio
    async def test_infer_tool_name_web(self, autonomy_engine):
        """Infer tool name for web operations."""
        tool = autonomy_engine._infer_tool_name("fetch data from HTTP endpoint")
        assert tool == "web_scraper"


class TestTaskExecution:
    """Test task execution with consent flows and dry-run."""

    @pytest.mark.asyncio
    async def test_execute_task_normal_risk(self, autonomy_engine, mock_local_gpt_manager):
        """Execute normal risk task without consent."""
        autonomy_engine.risk_scorer.score_action.return_value = (
            RiskLevel.NORMAL,
            "normal read",
        )

        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="file_reader",
            arguments={"file": "data.txt"},
            estimated_duration=1.0,
            timeout_sec=30.0,
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task

        result = await autonomy_engine.execute_task_with_consent(task)

        assert result["status"] == "completed"
        assert mock_local_gpt_manager.execute_agent_tool.called

    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, autonomy_engine):
        """Task execution with timeout."""
        async def slow_tool(**kwargs):
            await asyncio.sleep(10)
            return {"status": "done"}

        autonomy_engine.local_gpt_manager.execute_agent_tool = slow_tool
        autonomy_engine.risk_scorer.score_action.return_value = (
            RiskLevel.NORMAL,
            "normal",
        )

        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="slow_tool",
            arguments={},
            estimated_duration=1.0,
            timeout_sec=0.1,  # Very short timeout
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task

        result = await autonomy_engine.execute_task_with_consent(task)

        assert result["status"] == "timeout"
        assert task.id in result or "timeout_sec" in result

    @pytest.mark.asyncio
    async def test_execute_task_audit_log_entry(self, autonomy_engine):
        """Task execution creates audit log entry."""
        autonomy_engine.risk_scorer.score_action.return_value = (
            RiskLevel.NORMAL,
            "normal",
        )
        autonomy_engine.local_gpt_manager.execute_agent_tool = AsyncMock(
            return_value={"status": "success"}
        )

        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="file_reader",
            arguments={},
            estimated_duration=1.0,
            timeout_sec=30.0,
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task

        await autonomy_engine.execute_task_with_consent(task)

        # Check audit journal has entries
        assert len(autonomy_engine.audit_journal) > 0
        assert any(e.event_type == "task_completed" for e in autonomy_engine.audit_journal)


class TestPreemption:
    """Test task preemption and cancellation."""

    @pytest.mark.asyncio
    async def test_preempt_running_task(self, autonomy_engine):
        """Preempt a running task."""
        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="long_operation",
            arguments={},
            estimated_duration=10.0,
            timeout_sec=30.0,
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task
        autonomy_engine.task_status[task.id] = GoalStatus.RUNNING

        success = await autonomy_engine.preempt_task(
            task.id,
            PreemptionReason.OPERATOR_OVERRIDE,
        )

        assert success is True
        assert autonomy_engine.task_status[task.id] == GoalStatus.CANCELLED
        assert autonomy_engine.preemption_reasons[task.id] == PreemptionReason.OPERATOR_OVERRIDE

    @pytest.mark.asyncio
    async def test_preempt_nonexistent_task_returns_false(self, autonomy_engine):
        """Preempt nonexistent task returns False."""
        success = await autonomy_engine.preempt_task(
            "nonexistent",
            PreemptionReason.TIMEOUT,
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_preemption_latency_recorded(self, autonomy_engine, mock_metrics):
        """Preemption latency is recorded in metrics."""
        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="op",
            arguments={},
            estimated_duration=1.0,
            timeout_sec=30.0,
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task
        autonomy_engine.task_status[task.id] = GoalStatus.RUNNING

        await autonomy_engine.preempt_task(task.id, PreemptionReason.TIMEOUT)

        mock_metrics.record_latency.assert_called()


class TestOperatorOverride:
    """Test operator manual control."""

    @pytest.mark.asyncio
    async def test_operator_pause(self, autonomy_engine):
        """Operator can pause engine."""
        autonomy_engine.is_running = True
        result = await autonomy_engine.operator_override("pause")

        assert result["status"] == "paused"
        assert autonomy_engine.is_running is False

    @pytest.mark.asyncio
    async def test_operator_resume(self, autonomy_engine):
        """Operator can resume engine."""
        autonomy_engine.is_running = False
        result = await autonomy_engine.operator_override("resume")

        assert result["status"] == "resumed"
        assert autonomy_engine.is_running is True

    @pytest.mark.asyncio
    async def test_operator_cancel_task(self, autonomy_engine):
        """Operator can cancel specific task."""
        task = Task(
            id="task-1",
            goal_id="goal-1",
            tool_name="op",
            arguments={},
            estimated_duration=1.0,
            timeout_sec=30.0,
            created_at=time.time(),
        )
        autonomy_engine.active_tasks[task.id] = task
        autonomy_engine.task_status[task.id] = GoalStatus.RUNNING

        result = await autonomy_engine.operator_override("cancel_task", target_id="task-1")

        assert result["status"] == "task_cancelled"
        assert autonomy_engine.task_status["task-1"] == GoalStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_operator_cancel_all(self, autonomy_engine):
        """Operator can cancel all tasks."""
        for i in range(3):
            task = Task(
                id=f"task-{i}",
                goal_id="goal-1",
                tool_name="op",
                arguments={},
                estimated_duration=1.0,
                timeout_sec=30.0,
                created_at=time.time(),
            )
            autonomy_engine.active_tasks[task.id] = task
            autonomy_engine.task_status[task.id] = GoalStatus.RUNNING

        result = await autonomy_engine.operator_override("cancel_all")

        assert result["status"] == "all_tasks_cancelled"
        assert result["count"] == 3


class TestEngineStatus:
    """Test engine status reporting."""

    @pytest.mark.asyncio
    async def test_get_status(self, autonomy_engine):
        """Get engine status."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.NORMAL,
            intent="test",
            parameters={},
            created_at=time.time(),
        )
        await autonomy_engine.enqueue_goal(goal)

        status = autonomy_engine.get_status()

        assert "is_running" in status
        assert "uptime_sec" in status
        assert "goal_queue_size" in status
        assert status["goal_queue_size"] == 1

    @pytest.mark.asyncio
    async def test_get_audit_journal(self, autonomy_engine):
        """Retrieve audit journal entries."""
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.NORMAL,
            intent="test",
            parameters={},
            created_at=time.time(),
        )
        await autonomy_engine.enqueue_goal(goal)

        journal = autonomy_engine.get_audit_journal(limit=10)

        assert len(journal) > 0
        assert all(hasattr(e, "event_type") for e in journal)


class TestConcurrency:
    """Test concurrent task handling."""

    @pytest.mark.asyncio
    async def test_concurrent_tasks_limited(self, autonomy_engine):
        """Concurrent task count is limited by semaphore."""
        assert autonomy_engine.max_concurrent_tasks == 5
        assert autonomy_engine.task_semaphore._value == 5


class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_goal_to_execution_workflow(self, autonomy_engine, mock_local_gpt_manager):
        """Complete workflow: goal → schedule → execute."""
        autonomy_engine.risk_scorer.score_action.return_value = (
            RiskLevel.NORMAL,
            "normal",
        )

        # Enqueue goal
        goal = Goal(
            id="goal-1",
            priority=GoalPriority.HIGH,
            intent="read file data",
            parameters={"file": "test.txt"},
            created_at=time.time(),
        )
        await autonomy_engine.enqueue_goal(goal)

        # Schedule task
        task = await autonomy_engine.schedule_next_task()
        assert task is not None

        # Execute task
        result = await autonomy_engine.execute_task_with_consent(task)
        assert result["status"] == "completed"
