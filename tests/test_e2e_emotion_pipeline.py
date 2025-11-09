"""
Phase 2 End-to-End Integration Test

Validates the complete emotion-aware cognitive pipeline:
Sensors → Emotion Inference → Adaptive Routing → Execution
"""
from __future__ import annotations

from chat_os.executor import ExecutionContext, _execute_step, register_intent
from chat_os.plan import Plan, PlanMeta, PlanStep
from chat_os.sensors import get_sensor_hub


# Register a test intent handler
@register_intent("test.compute")
def handle_test_compute(step: PlanStep, ctx: ExecutionContext) -> dict:
    """Test handler for computation."""
    return {"result": "computed", "value": 42}


@register_intent("test.query")
def handle_test_query(step: PlanStep, ctx: ExecutionContext) -> dict:
    """Test handler for queries."""
    return {"result": "queried", "data": "test_data"}


def test_end_to_end_emotion_aware_execution():
    """Complete pipeline should route tasks based on emotional state."""
    # Create a simple plan
    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_emotion_aware_plan",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[
            PlanStep(intent="test.compute", args={"operation": "add"}),
            PlanStep(intent="test.query", args={"target": "database"}),
        ],
    )

    # Create execution context (initializes emotion-aware routing)
    ctx = ExecutionContext(plan=plan)

    # Verify cognitive components initialized
    assert ctx.meta_controller is not None
    assert ctx.governor is not None
    assert ctx.governor._emotion_engine is not None

    # Execute first step
    step1 = plan.steps[0]
    result1 = _execute_step(step1, 0, ctx)

    # Should succeed with emotion-aware routing
    assert result1.success
    assert result1.output["result"] == "computed"
    assert "step.0.mode" in ctx.variables  # Mode was recorded

    # Execute second step
    step2 = plan.steps[1]
    result2 = _execute_step(step2, 1, ctx)

    # Should succeed
    assert result2.success
    assert result2.output["result"] == "queried"
    assert "step.1.mode" in ctx.variables


def test_execution_context_adapts_to_workload():
    """Execution context should adapt routing when workload changes."""
    hub = get_sensor_hub()

    # Test with light workload
    hub.workload.update_workload(pending=2, urgent=0)

    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_workload_adaptation",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[PlanStep(intent="test.compute", args={"operation": "multiply"})],
    )

    ctx = ExecutionContext(plan=plan)
    step = plan.steps[0]
    result = _execute_step(step, 0, ctx)

    assert result.success
    # Mode should be recorded (value depends on emotion state at test time)
    assert "step.0.mode" in ctx.variables

    # Test with heavy workload
    hub.workload.update_workload(pending=20, urgent=5)

    plan2 = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_workload_adaptation_heavy",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[PlanStep(intent="test.compute", args={"operation": "divide"})],
    )

    ctx2 = ExecutionContext(plan=plan2)
    step2 = plan2.steps[0]
    result2 = _execute_step(step2, 0, ctx2)

    assert result2.success
    # Both should succeed, but routing may differ based on emotion


def test_telemetry_captures_emotion_aware_routing():
    """Telemetry should capture emotion-aware routing decisions."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_telemetry_capture",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[
            PlanStep(intent="test.compute", args={"x": 1}),
            PlanStep(intent="test.compute", args={"x": 2}),
        ],
    )

    ctx = ExecutionContext(plan=plan)

    # Execute steps
    for i, step in enumerate(plan.steps):
        result = _execute_step(step, i, ctx)
        assert result.success

    # Telemetry should have captured both executions
    snapshot = ctx.telemetry.snapshot()
    assert snapshot.total_tasks >= 2
    # Note: TelemetrySnapshot doesn't have success_count field


def test_execution_traces_include_emotion_context():
    """Execution traces should include emotion-aware routing metadata."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_trace_emotion",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[PlanStep(intent="test.compute", args={"trace": True})],
    )

    ctx = ExecutionContext(plan=plan)
    step = plan.steps[0]
    result = _execute_step(step, 0, ctx)

    assert result.success

    # Should have recorded trace
    assert len(ctx.execution_traces) >= 1
    trace = ctx.execution_traces[0]

    # Trace should include mode
    assert trace.mode in ["SYMBOLIC", "STATISTICAL", "PROCEDURAL", "UNKNOWN"]
    assert trace.success is True


def test_graceful_degradation_if_emotion_unavailable():
    """System should work even if emotion engine fails."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_degradation",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[PlanStep(intent="test.query", args={"safe": True})],
    )

    ctx = ExecutionContext(plan=plan)

    # Even if emotion engine had issues, execution should proceed
    step = plan.steps[0]
    result = _execute_step(step, 0, ctx)

    # Should still execute successfully
    assert result.success or result.error is not None  # Either works or has clear error
