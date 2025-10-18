"""
Tests for ASTRA Event Bus and Tool Registry integration
"""

import pytest
import asyncio
from typing import List, Dict, Any
from astra.core.event_bus import Event, get_event_bus
from astra.core.tool_bus import ToolRegistry, ToolError, ToolTimeoutError, ToolContext


# Test Helpers
class EventCollector:
    """Helper to collect emitted events"""

    def __init__(self):
        self.events: List[Event] = []

    def collect(self, event: Event):
        self.events.append(event)


async def mock_tool(value: str) -> str:
    """Mock tool that returns input"""
    return f"Processed: {value}"


async def slow_tool(delay: float) -> str:
    """Mock tool that sleeps"""
    await asyncio.sleep(delay)
    return "Done"


async def error_tool() -> None:
    """Mock tool that raises error"""
    raise ValueError("Tool error")


# Tests
def test_event_bus_creation():
    """Test event bus singleton"""
    bus1 = get_event_bus()
    bus2 = get_event_bus()
    assert bus1 is bus2


def test_event_subscription():
    """Test event subscription and collection"""
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe
    bus.subscribe("test.event", collector.collect)

    # Emit event
    bus.emit("test.event", {"value": 42})

    # Verify
    assert len(collector.events) == 1
    assert collector.events[0].name == "test.event"
    assert collector.events[0].data["value"] == 42


def test_event_unsubscription():
    """Test event unsubscription"""
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe and then unsubscribe
    bus.subscribe("test.event", collector.collect)
    bus.unsubscribe("test.event", collector.collect)

    # Emit event
    bus.emit("test.event", {"value": 42})

    # Verify no events collected
    assert len(collector.events) == 0


@pytest.mark.asyncio
async def test_tool_execution_events():
    """Test events emitted during tool execution"""
    registry = ToolRegistry()
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe to events
    bus.subscribe("astra.tool.before", collector.collect)
    bus.subscribe("astra.tool.executed", collector.collect)

    # Register mock tool
    registry.register(
        name="mock",
        description="Mock tool",
        handler=mock_tool,
        schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
    )

    # Execute tool
    result = await registry.execute("mock", {"value": "test"})

    # Verify events
    assert len(collector.events) == 2

    before_event = collector.events[0]
    assert before_event.name == "astra.tool.before"
    assert before_event.data["tool"] == "mock"
    assert before_event.data["args"] == {"value": "test"}

    after_event = collector.events[1]
    assert after_event.name == "astra.tool.executed"
    assert after_event.data["tool"] == "mock"
    assert after_event.data["args"] == {"value": "test"}
    assert after_event.data["result"] == "Processed: test"
    assert after_event.data["success"] is True


@pytest.mark.asyncio
async def test_tool_timeout_events():
    """Test events emitted on tool timeout"""
    registry = ToolRegistry()
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe to events
    bus.subscribe("astra.tool.before", collector.collect)
    bus.subscribe("astra.tool.executed", collector.collect)

    # Register slow tool with timeout
    registry.register(
        name="slow",
        description="Slow tool",
        handler=slow_tool,
        schema={
            "type": "object",
            "properties": {"delay": {"type": "number"}},
            "required": ["delay"],
        },
        timeout=0.1,  # Short timeout
    )

    # Execute tool
    with pytest.raises(ToolTimeoutError):
        await registry.execute("slow", {"delay": 1.0})

    # Verify events
    assert len(collector.events) == 2

    before_event = collector.events[0]
    assert before_event.name == "astra.tool.before"
    assert before_event.data["tool"] == "slow"

    error_event = collector.events[1]
    assert error_event.name == "astra.tool.executed"
    assert error_event.data["tool"] == "slow"
    assert error_event.data["success"] is False
    assert error_event.data["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_tool_error_events():
    """Test events emitted on tool error"""
    registry = ToolRegistry()
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe to events
    bus.subscribe("astra.tool.before", collector.collect)
    bus.subscribe("astra.tool.executed", collector.collect)

    # Register error tool
    registry.register(
        name="error",
        description="Error tool",
        handler=error_tool,
        schema={
            "type": "object",
            "properties": {},
        },
    )

    # Execute tool
    with pytest.raises(ToolError):
        await registry.execute("error", {})

    # Verify events
    assert len(collector.events) == 2

    before_event = collector.events[0]
    assert before_event.name == "astra.tool.before"
    assert before_event.data["tool"] == "error"

    error_event = collector.events[1]
    assert error_event.name == "astra.tool.executed"
    assert error_event.data["tool"] == "error"
    assert error_event.data["success"] is False
    assert error_event.data["error_type"] == "execution"
    assert "Tool error" in error_event.data["error"]


@pytest.mark.asyncio
async def test_tool_context_in_events():
    """Test tool context included in events"""
    registry = ToolRegistry()
    bus = get_event_bus()
    collector = EventCollector()

    # Subscribe to events
    bus.subscribe("astra.tool.before", collector.collect)
    bus.subscribe("astra.tool.executed", collector.collect)

    # Register tool
    registry.register(
        name="mock",
        description="Mock tool",
        handler=mock_tool,
        schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
    )

    # Execute with context
    context = ToolContext(tool_id="test_context", metadata={"trace_id": "abc123"})

    await registry.execute("mock", {"value": "test"}, context=context)

    # Verify context in events
    for event in collector.events:
        assert event.data["context"] is not None
        assert event.data["context"]["tool_id"] == "test_context"
        assert event.data["context"]["metadata"]["trace_id"] == "abc123"
