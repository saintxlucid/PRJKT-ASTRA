"""
Tests for metrics exporter.

Validates Prometheus metrics collection from event bus.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import patch

# Mock prometheus_client before importing metrics_exporter
with patch("astra.monitoring.metrics_exporter.start_http_server"):
    from astra.monitoring.metrics_exporter import (
        MetricsExporter,
        ROUTER_CALLS,
        ROUTER_PHASES,
        TOOL_CALLS,
        CONSENT_REQUESTS,
        CONSENT_BYPASSES,
        BUDGET_EXHAUSTIONS,
        ACT_GATES,
        OS_ACTIONS,
        ACTIVE_PLANS,
        ACTIVE_CONSENTS,
    )

from astra.core.event_bus import Event, get_event_bus


# Fixtures


@pytest.fixture
def event_bus():
    """Get event bus instance."""
    return get_event_bus()


@pytest.fixture
def metrics_exporter():
    """Create metrics exporter."""
    exporter = MetricsExporter(port=9090)
    return exporter


@pytest.fixture
async def exporter_with_subscriptions(metrics_exporter):
    """Create exporter with subscriptions setup."""
    await metrics_exporter.setup_subscriptions()
    yield metrics_exporter


# Tests for Router Events


@pytest.mark.asyncio
async def test_route_selected_metric(exporter_with_subscriptions, event_bus):
    """Test route selection metrics."""
    # Emit route event
    event = Event(
        name="astra.router.route_selected",
        data={"mode": "code"},
        timestamp=datetime.now(),
    )
    event_bus.emit(event.name, event.data)

    # Check metric
    assert ROUTER_CALLS._metrics[("code",)]._value.get() >= 1


@pytest.mark.asyncio
async def test_phase_executing_metric(exporter_with_subscriptions, event_bus):
    """Test phase execution metrics."""
    # Emit phase events
    for phase in ["sense", "plan", "act"]:
        event = Event(
            name="astra.router.phase_executing",
            data={"phase": phase},
            timestamp=datetime.now(),
        )
        event_bus.emit(event.name, event.data)

    # Check metrics
    assert ROUTER_PHASES._metrics[("sense",)]._value.get() >= 1
    assert ROUTER_PHASES._metrics[("plan",)]._value.get() >= 1
    assert ROUTER_PHASES._metrics[("act",)]._value.get() >= 1


# Tests for Tool Events


@pytest.mark.asyncio
async def test_tool_execution_success_metric(exporter_with_subscriptions, event_bus):
    """Test successful tool execution metrics."""
    tool_id = "tool_1"
    tool_name = "TestTool"

    # Emit tool start
    start_event = Event(
        name="astra.tool.before",
        data={"tool_id": tool_id, "tool": tool_name},
        timestamp=datetime.now(),
    )
    event_bus.emit(start_event.name, start_event.data)

    await asyncio.sleep(0.05)

    # Emit tool completion
    end_event = Event(
        name="astra.tool.executed",
        data={"tool_id": tool_id, "tool": tool_name, "success": True},
        timestamp=datetime.now(),
    )
    event_bus.emit(end_event.name, end_event.data)

    # Check metrics
    assert TOOL_CALLS._metrics[(tool_name, "success")]._value.get() >= 1


@pytest.mark.asyncio
async def test_tool_execution_failure_metric(exporter_with_subscriptions, event_bus):
    """Test failed tool execution metrics."""
    tool_id = "tool_2"
    tool_name = "FailingTool"

    # Emit tool start
    start_event = Event(
        name="astra.tool.before",
        data={"tool_id": tool_id, "tool": tool_name},
        timestamp=datetime.now(),
    )
    event_bus.emit(start_event.name, start_event.data)

    await asyncio.sleep(0.05)

    # Emit tool failure
    end_event = Event(
        name="astra.tool.executed",
        data={"tool_id": tool_id, "tool": tool_name, "success": False},
        timestamp=datetime.now(),
    )
    event_bus.emit(end_event.name, end_event.data)

    # Check metrics
    assert TOOL_CALLS._metrics[(tool_name, "failed")]._value.get() >= 1


# Tests for Plan Events


@pytest.mark.asyncio
async def test_plan_execution_metric(exporter_with_subscriptions, event_bus):
    """Test plan execution metrics."""
    plan_id = "plan_2"

    # Emit execution start
    start_event = Event(
        name="astra.plan.execution_start",
        data={"plan_id": plan_id},
        timestamp=datetime.now(),
    )
    event_bus.emit(start_event.name, start_event.data)

    # Check active plans gauge
    assert ACTIVE_PLANS._value.get() >= 1

    await asyncio.sleep(0.05)

    # Emit execution complete
    end_event = Event(
        name="astra.plan.execution_complete",
        data={"plan_id": plan_id, "status": "success"},
        timestamp=datetime.now(),
    )
    event_bus.emit(end_event.name, end_event.data)

    # Check active plans decreased
    assert ACTIVE_PLANS._value.get() >= 0


# Tests for Consent Events


@pytest.mark.asyncio
async def test_consent_request_metric(exporter_with_subscriptions, event_bus):
    """Test consent request metrics."""
    request_id = "consent_1"

    # Emit consent request
    request_event = Event(
        name="astra.plan.consent_request",
        data={"request_id": request_id},
        timestamp=datetime.now(),
    )
    event_bus.emit(request_event.name, request_event.data)

    # Check active consents gauge
    assert ACTIVE_CONSENTS._value.get() >= 1


@pytest.mark.asyncio
async def test_consent_decision_approved_metric(exporter_with_subscriptions, event_bus):
    """Test approved consent metrics."""
    request_id = "consent_2"

    # Emit consent request
    request_event = Event(
        name="astra.plan.consent_request",
        data={"request_id": request_id},
        timestamp=datetime.now(),
    )
    event_bus.emit(request_event.name, request_event.data)

    await asyncio.sleep(0.05)

    # Emit approval
    decision_event = Event(
        name="astra.plan.consent_decision",
        data={"request_id": request_id, "approved": True},
        timestamp=datetime.now(),
    )
    event_bus.emit(decision_event.name, decision_event.data)

    # Check metrics
    assert CONSENT_REQUESTS._metrics[("approved",)]._value.get() >= 1
    assert ACTIVE_CONSENTS._value.get() >= 0


@pytest.mark.asyncio
async def test_consent_bypass_metric(exporter_with_subscriptions, event_bus):
    """Test consent bypass metrics."""
    # Emit bypass event
    bypass_event = Event(
        name="astra.plan.consent_bypass",
        data={},
        timestamp=datetime.now(),
    )
    event_bus.emit(bypass_event.name, bypass_event.data)

    # Check metric
    assert CONSENT_BYPASSES._value.get() >= 1


# Tests for Budget Events


@pytest.mark.asyncio
async def test_budget_exhaustion_metric(exporter_with_subscriptions, event_bus):
    """Test budget exhaustion metrics."""
    # Emit budget exhaustion
    exhaustion_event = Event(
        name="astra.plan.budget_exhaustion",
        data={"component": "steps"},
        timestamp=datetime.now(),
    )
    event_bus.emit(exhaustion_event.name, exhaustion_event.data)

    # Check metric
    assert BUDGET_EXHAUSTIONS._metrics[("steps",)]._value.get() >= 1


# Tests for ACT Gate Events


@pytest.mark.asyncio
async def test_act_gate_allowed_metric(exporter_with_subscriptions, event_bus):
    """Test ACT gate allowed metrics."""
    # Emit gate decision - allowed
    gate_event = Event(
        name="astra.act.gate_decision",
        data={"allowed": True},
        timestamp=datetime.now(),
    )
    event_bus.emit(gate_event.name, gate_event.data)

    # Check metric
    assert ACT_GATES._metrics[("allowed",)]._value.get() >= 1


@pytest.mark.asyncio
async def test_act_gate_blocked_metric(exporter_with_subscriptions, event_bus):
    """Test ACT gate blocked metrics."""
    # Emit gate decision - blocked
    gate_event = Event(
        name="astra.act.gate_decision",
        data={"allowed": False},
        timestamp=datetime.now(),
    )
    event_bus.emit(gate_event.name, gate_event.data)

    # Check metric
    assert ACT_GATES._metrics[("blocked",)]._value.get() >= 1


# Tests for OS Events


@pytest.mark.asyncio
async def test_os_action_success_metric(exporter_with_subscriptions, event_bus):
    """Test successful OS action metrics."""
    action_id = "os_1"
    operator = "file"

    # Emit OS action start
    start_event = Event(
        name="astra.os.action_start",
        data={"action_id": action_id, "operator": operator},
        timestamp=datetime.now(),
    )
    event_bus.emit(start_event.name, start_event.data)

    await asyncio.sleep(0.05)

    # Emit OS action complete
    end_event = Event(
        name="astra.os.action_complete",
        data={"action_id": action_id, "operator": operator, "success": True},
        timestamp=datetime.now(),
    )
    event_bus.emit(end_event.name, end_event.data)

    # Check metric
    assert OS_ACTIONS._metrics[(operator, "success")]._value.get() >= 1


@pytest.mark.asyncio
async def test_os_action_failure_metric(exporter_with_subscriptions, event_bus):
    """Test failed OS action metrics."""
    action_id = "os_2"
    operator = "process"

    # Emit OS action start
    start_event = Event(
        name="astra.os.action_start",
        data={"action_id": action_id, "operator": operator},
        timestamp=datetime.now(),
    )
    event_bus.emit(start_event.name, start_event.data)

    await asyncio.sleep(0.05)

    # Emit OS action failure
    end_event = Event(
        name="astra.os.action_complete",
        data={"action_id": action_id, "operator": operator, "success": False},
        timestamp=datetime.now(),
    )
    event_bus.emit(end_event.name, end_event.data)

    # Check metric
    assert OS_ACTIONS._metrics[(operator, "failed")]._value.get() >= 1


# Integration Tests


@pytest.mark.asyncio
async def test_full_workflow_metrics(exporter_with_subscriptions, event_bus):
    """Test complete workflow metrics collection."""
    # Simulate complete ASTRA workflow
    events = [
        ("astra.router.route_selected", {"mode": "code"}),
        ("astra.router.phase_executing", {"phase": "sense"}),
        ("astra.tool.before", {"tool_id": "t1", "tool": "CodeAnalyzer"}),
        ("astra.tool.executed", {"tool_id": "t1", "tool": "CodeAnalyzer", "success": True}),
        ("astra.plan.generation_start", {"plan_id": "p1"}),
        ("astra.plan.generation_complete", {"plan_id": "p1"}),
        ("astra.plan.execution_start", {"plan_id": "p1"}),
        ("astra.plan.consent_request", {"request_id": "c1"}),
        ("astra.plan.consent_decision", {"request_id": "c1", "approved": True}),
        ("astra.router.phase_executing", {"phase": "plan"}),
        ("astra.router.phase_executing", {"phase": "act"}),
        ("astra.act.gate_decision", {"allowed": True}),
        ("astra.os.action_start", {"action_id": "os1", "operator": "file"}),
        ("astra.os.action_complete", {"action_id": "os1", "operator": "file", "success": True}),
        ("astra.plan.execution_complete", {"plan_id": "p1", "status": "success"}),
    ]

    for event_name, data in events:
        event_bus.emit(event_name, data)
        await asyncio.sleep(0.01)

    # Verify key metrics were recorded
    assert ROUTER_CALLS._metrics[("code",)]._value.get() >= 1
    assert TOOL_CALLS._metrics[("CodeAnalyzer", "success")]._value.get() >= 1
    assert CONSENT_REQUESTS._metrics[("approved",)]._value.get() >= 1
    assert ACT_GATES._metrics[("allowed",)]._value.get() >= 1
    assert OS_ACTIONS._metrics[("file", "success")]._value.get() >= 1
