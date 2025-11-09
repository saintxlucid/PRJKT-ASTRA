# tests/test_agent_kernel.py
"""Unit tests for agent kernel planning loop."""
import time

from agent_kernel.planner import AgentKernel, AgentState, create_agent
from agent_kernel.tools import ToolRegistry


def test_agent_creation():
    """Test agent can be created with defaults."""
    agent = create_agent()

    assert agent is not None
    assert agent.state == AgentState.IDLE
    assert agent.iteration == 0
    assert agent.tool_calls == 0


def test_tool_registry_registration():
    """Test tool registration."""
    registry = ToolRegistry()

    def test_func(args):
        return {"ok": True, "result": "test"}

    registry.register(
        name="test.tool",
        func=test_func,
        description="Test tool",
        scope="info",
        requires_token=False,
    )

    tool = registry.get("test.tool")
    assert tool is not None
    assert tool.name == "test.tool"


def test_tool_call_without_token():
    """Test calling a tool that doesn't require token."""
    registry = ToolRegistry()

    registry.register(
        name="info.test",
        func=lambda args: {"result": "success"},
        description="Test info tool",
        scope="info",
        requires_token=False,
    )

    result = registry.call("info.test", {})

    assert result["ok"] is True
    assert "result" in result
    assert "latency_ms" in result


def test_tool_call_requires_token():
    """Test tool that requires token fails without one."""
    registry = ToolRegistry()

    registry.register(
        name="action.test",
        func=lambda args: {"result": "success"},
        description="Test action tool",
        scope="action",
        requires_token=True,
    )

    result = registry.call("action.test", {})

    assert result["ok"] is False
    assert "requires valid token" in result["error"]


def test_tool_call_with_auto_token():
    """Test call_with_auto_token generates token automatically."""
    registry = ToolRegistry()

    registry.register(
        name="action.test",
        func=lambda args: {"result": args.get("input", "default")},
        description="Test action tool",
        scope="action",
        requires_token=True,
    )

    result = registry.call_with_auto_token("action.test", {"input": "hello"})

    assert result["ok"] is True
    assert result["result"] == "hello"


def test_agent_run_with_mock_llm():
    """Test agent run with mock LLM."""
    registry = ToolRegistry()

    # Register a simple info tool
    registry.register(
        name="info.echo",
        func=lambda args: {"result": args.get("message", "echo")},
        description="Echo a message",
        scope="info",
        requires_token=False,
    )

    # Create agent with custom LLM that returns answer immediately
    def mock_llm(prompt):
        return "ANSWER: Task completed successfully"

    agent = AgentKernel(
        tool_registry=registry,
        llm_func=mock_llm,
        max_iterations=5,
    )

    result = agent.run("Test task")

    assert result["ok"] is True
    assert "answer" in result
    assert result["iterations"] >= 1


def test_agent_calls_tool():
    """Test agent can call a tool during planning."""
    registry = ToolRegistry()

    call_count = [0]

    def counting_func(args):
        call_count[0] += 1
        return {"result": f"Called {call_count[0]} times"}

    registry.register(
        name="test.counter",
        func=counting_func,
        description="Count calls",
        scope="info",
        requires_token=False,
    )

    iteration_count = [0]

    def mock_llm(prompt):
        iteration_count[0] += 1
        if iteration_count[0] == 1:
            # First call: invoke tool
            return "CALL_TOOL: test.counter {}"
        else:
            # Second call: return answer
            return "ANSWER: Counter called successfully"

    agent = AgentKernel(
        tool_registry=registry,
        llm_func=mock_llm,
        max_iterations=5,
    )

    result = agent.run("Count something")

    assert result["ok"] is True
    assert call_count[0] == 1  # Tool was called once
    assert result["tool_calls"] == 1


def test_agent_max_iterations_abort():
    """Test agent aborts after max iterations."""
    registry = ToolRegistry()

    def infinite_llm(prompt):
        # Always try to call a tool (infinite loop)
        return "CALL_TOOL: info.time {}"

    registry.register(
        name="info.time",
        func=lambda args: {"result": time.time()},
        description="Get time",
        scope="info",
        requires_token=False,
    )

    agent = AgentKernel(
        tool_registry=registry,
        llm_func=infinite_llm,
        max_iterations=3,  # Very low limit
    )

    result = agent.run("Loop forever")

    assert result["ok"] is False
    assert "Max iterations" in result["error"]
    assert result["iterations"] >= 3


def test_tool_list():
    """Test listing available tools."""
    registry = ToolRegistry()

    registry.register(
        name="tool1",
        func=lambda args: {},
        description="First tool",
        scope="info",
    )

    registry.register(
        name="tool2",
        func=lambda args: {},
        description="Second tool",
        scope="action",
    )

    tools = registry.list_tools()

    assert len(tools) == 2
    assert any(t["name"] == "tool1" for t in tools)
    assert any(t["name"] == "tool2" for t in tools)


def test_agent_event_logging():
    """Test agent emits events during execution."""
    registry = ToolRegistry()

    events = []

    def event_logger(event):
        events.append(event)

    def mock_llm(prompt):
        return "ANSWER: Done"

    agent = AgentKernel(
        tool_registry=registry,
        llm_func=mock_llm,
        event_logger=event_logger,
    )

    agent.run("Test task")

    # Should have at least: start, state transitions, plan, answer
    assert len(events) > 0
    assert any(e["event"] == "agent.start" for e in events)
    assert any(e["event"] == "agent.answer" for e in events)
