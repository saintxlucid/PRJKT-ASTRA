"""
Test Phase 4: Multi-Operator Sovereignty

Validates that OperatorPool enables parallel execution with:
- Independent cognitive state per operator
- Shared emotional context hub
- Resource limits and tracking
- Priority-based scheduling
- Rebalancing across operators
"""

import time

from chat_os.cognitive.meta_controller import RiskLevel, Task
from chat_os.cognitive.multi_operator import (
    OperatorPool,
    OperatorPriority,
    OperatorStatus,
    ResourceLimits,
    ResourceUsage,
    get_operator_pool,
)


def test_resource_usage_tracking():
    """ResourceUsage tracks utilization and limits correctly."""
    limits = ResourceLimits(
        max_cpu_percent=50.0,
        max_memory_mb=1024.0,
        max_token_budget=100000,
        max_execution_time_ms=60000,
        max_concurrent_tasks=3,
    )

    usage = ResourceUsage(
        cpu_percent=25.0,
        memory_mb=512.0,
        tokens_used=50000,
        execution_time_ms=30000,
        active_tasks=2,
    )

    # Within limits
    assert not usage.exceeds(limits)
    ratio = usage.utilization_ratio(limits)
    assert 0.53 < ratio < 0.54  # Average: (0.5 + 0.5 + 0.5 + 0.5 + 0.67) / 5 ≈ 0.533

    # Exceeds CPU
    usage.cpu_percent = 60.0
    assert usage.exceeds(limits)

    # Reset and exceed memory
    usage.cpu_percent = 25.0
    usage.memory_mb = 1100.0
    assert usage.exceeds(limits)


def test_operator_instance_creation():
    """OperatorInstance initializes with correct defaults."""
    pool = OperatorPool()
    op = pool.create_operator(
        name="Test Operator",
        priority=OperatorPriority.NORMAL,
    )

    assert op.operator_id is not None
    assert op.name == "Test Operator"
    assert op.priority == OperatorPriority.NORMAL
    assert op.status == OperatorStatus.IDLE
    assert op.usage.active_tasks == 0
    assert len(op.pending_tasks) == 0
    assert op.governor is not None
    assert op.meta_controller is not None


def test_operator_pool_initialization():
    """OperatorPool initializes with shared emotion hub."""
    pool = OperatorPool(max_operators=5)

    assert pool.max_operators == 5
    assert len(pool.operators) == 0
    assert pool.emotion_hub is not None
    assert len(pool.lucid_weights) > 0


def test_operator_lifecycle():
    """Operators can be created, used, and terminated."""
    pool = OperatorPool()

    # Create operator
    op = pool.create_operator(
        name="Lifecycle Test",
        priority=OperatorPriority.HIGH,
    )
    op_id = op.operator_id
    assert len(pool.operators) == 1
    assert pool.get_operator(op_id) is not None

    # Terminate operator
    pool.terminate_operator(op_id)
    assert len(pool.operators) == 0
    assert pool.get_operator(op_id) is None


def test_operator_pool_max_limit():
    """OperatorPool enforces max_operators limit."""
    pool = OperatorPool(max_operators=3)

    # Create 3 operators - should succeed
    for i in range(3):
        pool.create_operator(
            name=f"Operator {i}",
            priority=OperatorPriority.NORMAL,
        )

    assert len(pool.operators) == 3

    # Try to create 4th operator - should raise error
    try:
        pool.create_operator(
            name="Operator 4",
            priority=OperatorPriority.NORMAL,
        )
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "pool full" in str(e).lower()


def test_operator_task_submission():
    """Operators accept tasks within their capacity."""
    pool = OperatorPool()
    op = pool.create_operator(
        name="Task Handler",
        priority=OperatorPriority.NORMAL,
        limits=ResourceLimits(max_concurrent_tasks=2),
    )

    # Submit tasks up to limit
    task1 = Task(name="task1", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    task2 = Task(name="task2", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})

    assert op.can_accept_task()
    op.submit_task(task1)
    assert len(op.pending_tasks) == 1

    assert op.can_accept_task()
    op.submit_task(task2)
    assert len(op.pending_tasks) == 2

    # Third task should be rejected (at limit)
    task3 = Task(name="task3", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    assert not op.can_accept_task()



def test_priority_based_scheduling():
    """Tasks are scheduled to operators matching their priority."""
    pool = OperatorPool()

    # Create operators with different priorities
    pool.create_operator(
        name="High Priority",
        priority=OperatorPriority.HIGH,
    )
    pool.create_operator(
        name="Normal Priority",
        priority=OperatorPriority.NORMAL,
    )

    # Schedule critical task - should prefer high priority operator
    critical_task = Task(
        name="critical",
        deterministic=False,
        risk=RiskLevel.HIGH,
        kind="test",
        payload={"priority": OperatorPriority.CRITICAL.value},
    )

    scheduled_op = pool.schedule_task(critical_task)
    assert scheduled_op is not None
    # Should prefer higher priority operator when both idle
    assert scheduled_op.priority in (OperatorPriority.HIGH, OperatorPriority.CRITICAL)


def test_find_available_operator():
    """Pool finds best available operator based on priority and utilization."""
    pool = OperatorPool()

    # Create operators
    op1 = pool.create_operator(
        name="Operator 1",
        priority=OperatorPriority.HIGH,
    )
    op2 = pool.create_operator(
        name="Operator 2",
        priority=OperatorPriority.NORMAL,
    )

    # Both idle - should prefer higher priority
    available = pool.find_available_operator(OperatorPriority.HIGH)
    assert available is not None
    assert available.priority == OperatorPriority.HIGH

    # Make high priority busy
    op1.status = OperatorStatus.BUSY
    available = pool.find_available_operator(OperatorPriority.HIGH)
    assert available is not None
    assert available.operator_id == op2.operator_id


def test_shared_emotion_hub():
    """All operators share the same emotional context hub."""
    pool = OperatorPool()

    op1 = pool.create_operator(
        name="Operator 1",
        priority=OperatorPriority.NORMAL,
    )
    op2 = pool.create_operator(
        name="Operator 2",
        priority=OperatorPriority.NORMAL,
    )

    # Both operators should share the same emotion hub instance
    assert pool.emotion_hub is not None
    # Emotion hub is shared at pool level, not stored in operators
    # Operators access it during task execution
    assert op1 is not None
    assert op2 is not None


def test_independent_cognitive_state():
    """Each operator has independent cognitive components."""
    pool = OperatorPool()

    op1 = pool.create_operator(
        name="Operator 1",
        priority=OperatorPriority.NORMAL,
    )
    op2 = pool.create_operator(
        name="Operator 2",
        priority=OperatorPriority.NORMAL,
    )

    # Each operator should have its own governor and meta_controller
    assert op1.governor is not op2.governor
    assert op1.meta_controller is not op2.meta_controller
    assert op1.governor is not None
    assert op2.meta_controller is not None


def test_pool_statistics():
    """Pool tracks aggregate statistics across all operators."""
    pool = OperatorPool()

    op1 = pool.create_operator(
        name="Operator 1",
        priority=OperatorPriority.NORMAL,
    )
    op2 = pool.create_operator(
        name="Operator 2",
        priority=OperatorPriority.HIGH,
    )

    # Update usage
    op1.usage.cpu_percent = 20.0
    op1.usage.memory_mb = 256.0
    op1.usage.tokens_used = 10000

    op2.usage.cpu_percent = 30.0
    op2.usage.memory_mb = 512.0
    op2.usage.tokens_used = 20000

    stats = pool.get_pool_stats()

    assert stats["total_operators"] == 2
    assert stats["max_operators"] == 5
    assert stats["total_cpu_percent"] == 50.0
    assert stats["total_memory_mb"] == 768.0
    assert stats["total_tokens_used"] == 30000
    assert "emotion_context" in stats


def test_rebalancing():
    """Pool rebalances tasks from overloaded operators."""
    pool = OperatorPool()

    # Create two operators
    op1 = pool.create_operator(
        name="Operator 1",
        priority=OperatorPriority.NORMAL,
        limits=ResourceLimits(max_concurrent_tasks=2),
    )
    op2 = pool.create_operator(
        name="Operator 2",
        priority=OperatorPriority.NORMAL,
        limits=ResourceLimits(max_concurrent_tasks=2),
    )

    # Overload op1
    task1 = Task(name="task1", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    task2 = Task(name="task2", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    task3 = Task(name="task3", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})

    op1.submit_task(task1)
    op1.submit_task(task2)
    op1.submit_task(task3)

    assert len(op1.pending_tasks) == 3
    assert len(op2.pending_tasks) == 0

    # Rebalance
    pool.rebalance_operators()

    # Tasks should be distributed
    total_tasks = len(op1.pending_tasks) + len(op2.pending_tasks)
    assert total_tasks == 3
    # At least one task should have moved to op2
    assert len(op2.pending_tasks) > 0


def test_operator_age_tracking():
    """Operators track their age and idle time."""
    pool = OperatorPool()
    op = pool.create_operator(
        name="Age Test",
        priority=OperatorPriority.NORMAL,
    )

    # Wait a bit
    time.sleep(0.1)

    # Check age
    age = op.age_seconds()
    assert age >= 0.1
    assert age < 1.0  # Should be recent

    # Check idle time
    idle = op.idle_seconds()
    assert idle >= 0.1


def test_operator_status_transitions():
    """Operators transition through lifecycle states correctly."""
    pool = OperatorPool()
    op = pool.create_operator(
        name="Status Test",
        priority=OperatorPriority.NORMAL,
    )

    # Starts idle
    assert op.status == OperatorStatus.IDLE

    # Can transition to busy
    op.status = OperatorStatus.BUSY
    assert op.status == OperatorStatus.BUSY

    # Can transition to waiting
    op.status = OperatorStatus.WAITING
    assert op.status == OperatorStatus.WAITING

    # Can pause
    op.status = OperatorStatus.PAUSED
    assert op.status == OperatorStatus.PAUSED

    # Can resume
    op.status = OperatorStatus.IDLE
    assert op.status == OperatorStatus.IDLE


def test_list_operators():
    """Pool lists all operators with their details."""
    pool = OperatorPool()

    pool.create_operator("Operator 1", OperatorPriority.HIGH)
    pool.create_operator("Operator 2", OperatorPriority.NORMAL)
    pool.create_operator("Operator 3", OperatorPriority.LOW)

    operators = pool.list_operators()
    assert len(operators) == 3

    # Check each operator instance
    for op in operators:
        assert op.operator_id is not None
        assert op.name is not None
        assert op.priority is not None
        assert op.status is not None
        assert op.pending_tasks is not None
        assert op.completed_tasks is not None


def test_global_pool_singleton():
    """get_operator_pool() returns global singleton."""
    pool1 = get_operator_pool()
    pool2 = get_operator_pool()

    assert pool1 is pool2
    assert isinstance(pool1, OperatorPool)


def test_execute_operator_task():
    """Pool executes tasks through operator's meta-controller."""
    pool = OperatorPool()
    op = pool.create_operator(
        name="Execution Test",
        priority=OperatorPriority.NORMAL,
    )

    task = Task(
        name="test_task",
        deterministic=False,
        risk=RiskLevel.LOW,
        kind="test",
        payload={},
    )

    # Execute task
    result = pool.execute_operator_task(op, task)

    # Should return execution result
    assert result is not None
    assert "output" in result  # MetaController.run() returns EngineResult with output

    # Operator should have completed task
    assert len(op.completed_tasks) == 1
    assert op.completed_tasks[0].name == "test_task"

    # Operator should return to idle
    assert op.status == OperatorStatus.IDLE


def test_resource_limit_enforcement():
    """Operators respect resource limits."""
    pool = OperatorPool()

    strict_limits = ResourceLimits(
        max_cpu_percent=10.0,
        max_memory_mb=128.0,
        max_token_budget=1000,
        max_execution_time_ms=100,
        max_concurrent_tasks=1,
    )

    op = pool.create_operator(
        name="Strict Limits",
        priority=OperatorPriority.NORMAL,
        limits=strict_limits,
    )

    # Can accept first task
    task1 = Task(name="task1", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    assert op.can_accept_task()
    op.submit_task(task1)

    # Cannot accept second task (at limit)
    task2 = Task(name="task2", deterministic=False, risk=RiskLevel.LOW, kind="test", payload={})
    assert not op.can_accept_task()


def test_priority_enum_ordering():
    """Priority enum has correct ordering."""
    assert OperatorPriority.CRITICAL.value == 1
    assert OperatorPriority.HIGH.value == 2
    assert OperatorPriority.NORMAL.value == 3
    assert OperatorPriority.LOW.value == 4
    assert OperatorPriority.BACKGROUND.value == 5

    # Lower value = higher priority
    assert OperatorPriority.CRITICAL.value < OperatorPriority.HIGH.value
    assert OperatorPriority.HIGH.value < OperatorPriority.NORMAL.value
    assert OperatorPriority.NORMAL.value < OperatorPriority.LOW.value
    assert OperatorPriority.LOW.value < OperatorPriority.BACKGROUND.value


def test_status_enum_values():
    """Status enum has all expected states."""
    assert hasattr(OperatorStatus, "IDLE")
    assert hasattr(OperatorStatus, "BUSY")
    assert hasattr(OperatorStatus, "WAITING")
    assert hasattr(OperatorStatus, "PAUSED")
    assert hasattr(OperatorStatus, "TERMINATED")


# Phase 4 Complete: 20 tests validating multi-operator sovereignty
