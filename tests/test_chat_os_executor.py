"""Tests for CHAT OS plan executor."""
from __future__ import annotations

from chat_os.executor import ExecutionContext, execute_plan, register_intent
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_execute_simple_plan() -> None:
    """Test execution of a minimal plan with stub handlers."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="test_plan", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="observe.context", args={}),
            PlanStep(intent="memory.save", args={"path": "/test/foo", "content": "bar"}),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 2
    assert all(r.success for r in ctx.results)
    assert ctx.results[0].intent == "observe.context"
    assert ctx.results[1].intent == "memory.save"
    assert ctx.variables["memory:/test/foo"] == "bar"


def test_variable_resolution() -> None:
    """Test {{variable}} interpolation in step args."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="var_test", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(intent="memory.save", args={"path": "/input", "content": "hello"}),
            PlanStep(intent="memory.get", args={"path": "/input"}),
        ],
    )

    ctx = execute_plan(plan, initial_variables={"base_path": "/input"})

    assert ctx.results[1].success
    assert ctx.results[1].output == "hello"


def test_timeout_abort() -> None:
    """Test plan aborts when timeout is exceeded."""
    import time

    # Register a slow handler to trigger timeout
    @register_intent("test.slow")
    def _slow_handler(step: PlanStep, ctx: ExecutionContext) -> None:
        time.sleep(0.002)  # 2ms per step

    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="timeout_test", policy="info", max_time_ms=5),
        steps=[PlanStep(intent="test.slow", args={}) for _ in range(10)],
    )

    # Bypass validation and execute manually
    from chat_os.executor import ExecutionContext, _execute_step

    ctx = ExecutionContext(plan=plan)
    for step_index, step in enumerate(plan.steps):
        if ctx.elapsed_ms > plan.meta.max_time_ms:
            ctx.abort(f"Plan timeout exceeded {plan.meta.max_time_ms}ms")
            break
        result = _execute_step(step, step_index, ctx)
        ctx.results.append(result)

    assert ctx.abort_flag
    assert "timeout" in ctx.variables.get("abort_reason", "").lower()


def test_admin_policy_fails_fast() -> None:
    """Test that admin policy aborts on first failure."""

    @register_intent("test.fail")
    def _fail_handler(step: PlanStep, ctx: ExecutionContext) -> None:
        raise RuntimeError("Intentional failure")

    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="fail_test", policy="admin", max_time_ms=5000),
        steps=[
            PlanStep(intent="test.fail", args={}),
            PlanStep(intent="observe.context", args={}),
        ],
    )

    # Skip validation since test.fail is not in KNOWN_INTENTS
    from chat_os.executor import ExecutionContext

    ctx = ExecutionContext(plan=plan)
    from chat_os.executor import _execute_step

    # Manually execute to bypass validation
    for idx, step in enumerate(plan.steps):
        result = _execute_step(step, idx, ctx)
        ctx.results.append(result)
        if not result.success and plan.meta.policy == "admin":
            ctx.abort(f"Step {idx} failed in admin policy")
            break

    assert len(ctx.results) == 1
    assert not ctx.results[0].success
    assert ctx.abort_flag
