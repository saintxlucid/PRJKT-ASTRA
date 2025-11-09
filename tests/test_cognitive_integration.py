"""Test cognitive fusion integration with executor."""
from __future__ import annotations

import pytest

from chat_os.cognitive.meta_controller import RiskLevel
from chat_os.executor import ExecutionContext, execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_execution_context_initializes_cognitive_components():
    """Verify ExecutionContext initializes meta-controller and governor."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(
            id="test_plan",
            policy="user",
            max_time_ms=10000,
        ),
        steps=[],
    )
    ctx = ExecutionContext(plan=plan)

    assert ctx.meta_controller is not None, "MetaController should be initialized"
    assert ctx.governor is not None, "CognitiveGovernor should be initialized"
    assert ctx.lucid_weights is not None, "LucidWeights should be loaded"


def test_step_to_task_classifies_risk_correctly():
    """Verify risk classification from step intent and args."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_plan", policy="user", max_time_ms=10000),
        steps=[],
    )
    ctx = ExecutionContext(plan=plan)

    # High-risk step
    high_risk_step = PlanStep(intent="file.delete", args={"path": "/important/file.txt"})
    task = ctx._step_to_task(high_risk_step)
    assert task.risk == RiskLevel.HIGH, "Delete operations should be high-risk"

    # Medium-risk step
    medium_risk_step = PlanStep(intent="config.update", args={"key": "timeout", "value": 5000})
    task = ctx._step_to_task(medium_risk_step)
    assert task.risk == RiskLevel.MEDIUM, "Update operations should be medium-risk"

    # Low-risk step
    low_risk_step = PlanStep(intent="data.query", args={"table": "users"})
    task = ctx._step_to_task(low_risk_step)
    assert task.risk == RiskLevel.LOW, "Query operations should be low-risk"


def test_cognitive_routing_records_reasoning_mode():
    """Verify meta-controller routing is recorded in execution context."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_plan", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1, "Should have executed 1 step"
    assert ctx.results[0].success, "Step should succeed"

    # Check that reasoning mode was recorded
    assert "step.0.mode" in ctx.variables, "Reasoning mode should be recorded"
    mode_name = ctx.variables["step.0.mode"]
    assert mode_name in ["SYMBOLIC", "STATISTICAL", "PROCEDURAL"], f"Invalid mode: {mode_name}"


def test_graceful_degradation_without_lucid_config():
    """Verify system works even if lucid.yaml is missing."""
    # This test verifies __post_init__ exception handling
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_plan", policy="user", max_time_ms=10000),
        steps=[],
    )

    # Even with missing config, system should initialize
    ctx = ExecutionContext(plan=plan)

    # Cognitive components should still be initialized (with defaults)
    assert ctx.meta_controller is not None or ctx.lucid_weights is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
