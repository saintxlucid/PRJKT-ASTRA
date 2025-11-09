"""Tests for telemetry collection integration in executor."""
from __future__ import annotations

from chat_os.executor import ExecutionContext, execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep
from chat_os.telemetry import TelemetrySnapshot


def test_telemetry_collector_initialized():
    """Verify telemetry collector is initialized in ExecutionContext."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_telemetry", policy="info", max_time_ms=5000),
        steps=[],
    )
    ctx = ExecutionContext(plan=plan)
    assert ctx.telemetry is not None
    assert hasattr(ctx.telemetry, "record_task")
    assert hasattr(ctx.telemetry, "snapshot")


def test_telemetry_records_task_metrics():
    """Test that telemetry records metrics for each executed step."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_metrics", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
        ],
    )
    ctx = execute_plan(plan)

    # Verify telemetry was collected
    assert "telemetry_snapshot" in ctx.variables
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]

    assert snapshot.total_tasks == 2
    assert snapshot.mode_distribution  # Should have mode counts
    assert snapshot.p95_latency_ms >= 0  # Should have latency data


def test_telemetry_snapshot_structure():
    """Test that telemetry snapshot has expected structure."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_snapshot", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="observe.context", args={}),
        ],
    )
    ctx = execute_plan(plan)
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]

    # Verify snapshot fields
    assert isinstance(snapshot.total_tasks, int)
    assert isinstance(snapshot.mode_distribution, dict)
    assert isinstance(snapshot.p95_latency_ms, float)
    assert isinstance(snapshot.rollback_count, int)
    assert isinstance(snapshot.macro_success_rate, float)
    assert isinstance(snapshot.emotional_states, dict)
    assert isinstance(snapshot.metadata, dict)


def test_telemetry_mode_distribution():
    """Test that mode distribution is captured correctly."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_mode", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
        ],
    )
    ctx = execute_plan(plan)
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]

    # Should have recorded modes for all steps
    total_mode_count = sum(snapshot.mode_distribution.values())
    assert total_mode_count == 3


def test_telemetry_records_failures():
    """Test that telemetry captures failed task metrics."""
    # Register a handler that will fail during execution
    from chat_os.executor import register_intent
    from chat_os.plan_checker import KNOWN_INTENTS

    # Add test intent to known intents
    KNOWN_INTENTS.add("test.failing")

    @register_intent("test.failing")
    def failing_handler(step, ctx):
        raise RuntimeError("Intentional test failure")

    # Create a plan with the failing intent
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_failure", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="test.failing", args={}),
        ],
    )

    # Execute plan - should not raise, but step will fail
    ctx = execute_plan(plan)

    # Verify telemetry still captured data (even for failures)
    assert "telemetry_snapshot" in ctx.variables
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]

    # Should have recorded 1 task (failed)
    assert snapshot.total_tasks == 1

    # Cleanup
    KNOWN_INTENTS.remove("test.failing")


def test_telemetry_latency_tracking():
    """Test that p95 latency is calculated correctly."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_latency", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}) for _ in range(10)
        ],
    )
    ctx = execute_plan(plan)
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]

    # P95 latency should be non-negative
    assert snapshot.p95_latency_ms >= 0

    # Should have recorded 10 tasks
    assert snapshot.total_tasks == 10


def test_telemetry_persists_across_steps():
    """Test that telemetry accumulates across multiple steps."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_persist", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
        ],
    )
    ctx = execute_plan(plan)

    # After first step, telemetry should have 1 task
    # After second step, telemetry should have 2 tasks
    snapshot: TelemetrySnapshot = ctx.variables["telemetry_snapshot"]
    assert snapshot.total_tasks == 2
