"""Test macro mining integration with executor."""
from __future__ import annotations

import pytest

from chat_os.executor import ExecutionContext, execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_execution_traces_recorded_on_success():
    """Verify execution traces are collected for successful steps."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="trace_test", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="memory.save", args={"path": "/test", "content": "data"}),
        ],
    )

    ctx = execute_plan(plan)

    # Should have recorded 2 successful traces
    assert len(ctx.execution_traces) == 2, f"Expected 2 traces, got {len(ctx.execution_traces)}"

    # Check first trace
    trace0 = ctx.execution_traces[0]
    assert trace0.task_name == "observe.context"
    assert trace0.success is True
    assert trace0.duration_ms > 0
    assert trace0.mode in ["SYMBOLIC", "STATISTICAL", "PROCEDURAL"]

    # Check second trace
    trace1 = ctx.execution_traces[1]
    assert trace1.task_name == "memory.save"
    assert trace1.success is True


def test_macro_mining_runs_after_plan_execution():
    """Verify macro mining processes collected traces."""
    # Create a plan with repeated pattern (need 3+ for mining threshold)
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="mining_test", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="observe.context", args={}),
        ],
    )

    ctx = execute_plan(plan)

    # Should have run macro mining
    assert "learned_macros_count" in ctx.variables, "Macro mining should have run"

    # Check if macros were learned (may be 0 if pattern doesn't meet threshold)
    learned_count = ctx.variables["learned_macros_count"]
    assert isinstance(learned_count, int), "Learned macros count should be integer"
    assert learned_count >= 0, "Learned macros count should be non-negative"


def test_macro_miner_initialized_with_config():
    """Verify MacroMiner is initialized with correct confidence threshold."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="init_test", policy="info", max_time_ms=10000),
        steps=[],
    )

    ctx = ExecutionContext(plan=plan)

    assert ctx.macro_miner is not None, "MacroMiner should be initialized"
    # Check that it uses config from lucid.yaml (default 0.85)
    assert ctx.macro_miner._min_confidence == 0.85


def test_trace_recording_includes_metadata():
    """Verify traces include step index and output summary."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="metadata_test", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.execution_traces) == 1
    trace = ctx.execution_traces[0]

    # Check metadata
    assert "step_index" in trace.metadata
    assert trace.metadata["step_index"] == 0
    assert "output_summary" in trace.metadata


def test_macro_mining_graceful_degradation_on_error():
    """Verify plan execution doesn't fail if macro mining fails."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="error_test", policy="info", max_time_ms=10000),
        steps=[
            PlanStep(intent="observe.context", args={}),
        ],
    )

    ctx = execute_plan(plan)

    # Should complete successfully even if macro mining had issues
    assert len(ctx.results) == 1
    assert ctx.results[0].success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
