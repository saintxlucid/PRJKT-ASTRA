"""Tests for CHAT OS approval workflow skill."""
from __future__ import annotations

from unittest.mock import patch

from chat_os.executor import execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_approval_auto_approve() -> None:
    """Test auto-approval for testing."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Test action",
                    "scope": "notify.push",
                    "auto_approve": True,
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success
    output = ctx.results[0].output
    assert output["ok"] is True
    assert output["approved"] is True
    assert output["auto_approved"] is True


def test_approval_missing_summary() -> None:
    """Test approval request validates summary at plan check time."""
    from chat_os.plan_checker import PlanValidationError

    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={"scope": "test"},
            ),
        ],
    )

    # Should fail at validation, not execution
    try:
        execute_plan(plan)
        assert False, "Should have raised PlanValidationError"
    except PlanValidationError as e:
        assert "summary" in str(e).lower()


def test_approval_preapproved_info_scope() -> None:
    """Test pre-approved scope for info policy."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Read memory",
                    "scope": "memory.get",
                },
            ),
        ],
    )

    # Mock non-interactive mode
    with patch("chat_os.skills.approval._is_interactive", return_value=False):
        ctx = execute_plan(plan, initial_variables={"_plan_policy": "info"})

        assert len(ctx.results) == 1
        assert ctx.results[0].success
        output = ctx.results[0].output
        assert output["ok"] is True
        assert output["approved"] is True


def test_approval_denied_high_risk_scope() -> None:
    """Test denial for high-risk scope without admin policy."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Delete all memory",
                    "scope": "memory.delete",
                },
            ),
        ],
    )

    # Mock non-interactive mode
    with patch("chat_os.skills.approval._is_interactive", return_value=False):
        ctx = execute_plan(plan, initial_variables={"_plan_policy": "user"})

        assert len(ctx.results) == 1
        assert ctx.results[0].success
        output = ctx.results[0].output
        assert output["ok"] is True
        assert output["approved"] is False  # Should be denied


def test_approval_terminal_yes() -> None:
    """Test terminal approval with yes response."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Send notification",
                    "scope": "notify.push",
                },
            ),
        ],
    )

    # Mock interactive mode and user input
    with patch("chat_os.skills.approval._is_interactive", return_value=True):
        with patch("builtins.input", return_value="yes"):
            ctx = execute_plan(plan)

            assert len(ctx.results) == 1
            assert ctx.results[0].success
            output = ctx.results[0].output
            assert output["ok"] is True
            assert output["approved"] is True


def test_approval_terminal_no() -> None:
    """Test terminal approval with no response."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Delete files",
                    "scope": "file.delete",
                },
            ),
        ],
    )

    # Mock interactive mode and user input
    with patch("chat_os.skills.approval._is_interactive", return_value=True):
        with patch("builtins.input", return_value="no"):
            ctx = execute_plan(plan)

            assert len(ctx.results) == 1
            assert ctx.results[0].success
            output = ctx.results[0].output
            assert output["ok"] is True
            assert output["approved"] is False


def test_approval_with_reason() -> None:
    """Test approval request with detailed reason."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="approval_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="approval.request",
                args={
                    "summary": "Sensitive operation",
                    "scope": "notify.push",
                    "reason": "This will send data to external service",
                    "auto_approve": True,
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success
    output = ctx.results[0].output
    assert output["ok"] is True
    assert output["approved"] is True
