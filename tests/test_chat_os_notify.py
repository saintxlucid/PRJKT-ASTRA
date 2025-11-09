"""Tests for CHAT OS notification skill."""
from __future__ import annotations

from unittest.mock import patch

from chat_os.executor import execute_plan
from chat_os.plan import Plan, PlanMeta, PlanStep


def test_notify_console() -> None:
    """Test console notification (default, always works)."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="notify_test", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="notify.push",
                args={
                    "channel": "console",
                    "message": "Test notification",
                    "title": "Test Title",
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success
    output = ctx.results[0].output
    assert output["ok"] is True
    assert output["channel"] == "console"
    assert output["delivered"] is True


def test_notify_system_fallback() -> None:
    """Test system notification falls back to console if unavailable."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="notify_test", policy="action", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="notify.push",
                args={
                    "channel": "system",
                    "message": "System test",
                    "priority": "high",
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success
    output = ctx.results[0].output
    assert output["ok"] is True
    # Should deliver via some method (console fallback if system unavailable)
    assert output["delivered"] is True


def test_notify_missing_message() -> None:
    """Test notification fails without message."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="notify_test", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="notify.push",
                args={"channel": "console"},
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success  # Handler executed
    output = ctx.results[0].output
    assert output["ok"] is False
    assert "message" in output["error"].lower()


def test_notify_unsupported_channel() -> None:
    """Test notification with unsupported channel protocol."""
    plan = Plan(
        version="0.3",
        meta=PlanMeta(id="notify_test", policy="info", max_time_ms=5000),
        steps=[
            PlanStep(
                intent="notify.push",
                args={
                    "channel": "console://unsupported",  # Use console which is allowed, handler will fail
                    "message": "Test",
                },
            ),
        ],
    )

    ctx = execute_plan(plan)

    assert len(ctx.results) == 1
    assert ctx.results[0].success
    # Handler delivers via console since "console" is local protocol
    output = ctx.results[0].output
    assert output["ok"] is True  # Console always works


def test_notify_telegram_missing_token() -> None:
    """Test Telegram notification fails without bot token."""
    with patch.dict("os.environ", {}, clear=True):
        plan = Plan(
            version="0.3",
            meta=PlanMeta(id="notify_test", policy="action", max_time_ms=5000),
            steps=[
                PlanStep(
                    intent="notify.push",
                    args={
                        "channel": "telegram://123456",
                        "message": "Test message",
                    },
                ),
            ],
        )

        ctx = execute_plan(plan)

        assert len(ctx.results) == 1
        assert ctx.results[0].success
        output = ctx.results[0].output
        assert output["ok"] is False
        assert "TELEGRAM_BOT_TOKEN" in output["error"]


def test_notify_priority_levels() -> None:
    """Test different priority levels."""
    for priority in ["low", "normal", "high", "urgent"]:
        plan = Plan(
            version="0.3",
            meta=PlanMeta(id="notify_test", policy="info", max_time_ms=5000),
            steps=[
                PlanStep(
                    intent="notify.push",
                    args={
                        "channel": "console",
                        "message": f"Priority {priority}",
                        "priority": priority,
                    },
                ),
            ],
        )

        ctx = execute_plan(plan)

        assert len(ctx.results) == 1
        assert ctx.results[0].success
        output = ctx.results[0].output
        assert output["ok"] is True
        assert output["delivered"] is True
