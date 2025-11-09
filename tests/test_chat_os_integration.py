"""Integration tests for CHAT OS + Agent Kernel."""
from agent_kernel.memory import MemoryManager
from agent_kernel.tools import ToolRegistry
from chat_os.agent_integration import (
    register_chat_os_tools,
    tool_execute_plan,
    tool_load_plan_from_memory,
)
from chat_os.executor import register_intent


@register_intent("test.echo")
def handle_test_echo(step, ctx):
    """Test handler that echoes input."""
    return step.args.get("message", "no message")


@register_intent("test.increment")
def handle_test_increment(step, ctx):
    """Test handler that increments a counter."""
    value = step.args.get("value", 0)
    return value + 1


def test_tool_execute_plan_success():
    """Test executing a simple plan via tool interface."""
    plan_dict = {
        "id": "test_plan_001",
        "meta": {
            "description": "Test plan",
            "author": "pytest",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "Hello"}},
            {"intent": "test.increment", "args": {"value": 10}},
        ],
    }

    result = tool_execute_plan({"plan": plan_dict, "admin_mode": True})

    assert result["ok"] is True
    assert result["result"]["steps_completed"] == 2
    assert result["result"]["outputs"] == ["Hello", 11]
    assert len(result["steps"]) == 2
    assert result["steps"][0]["intent"] == "test.echo"
    assert result["steps"][1]["intent"] == "test.increment"


def test_tool_execute_plan_with_variables():
    """Test plan execution with variable passing."""
    plan_dict = {
        "id": "test_plan_002",
        "meta": {
            "description": "Plan with variables",
            "author": "pytest",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.increment", "args": {"value": "{{input_value}}"}},
            {"intent": "test.increment", "args": {"value": "{{step.0}}"}},
        ],
    }

    result = tool_execute_plan({
        "plan": plan_dict,
        "variables": {"input_value": 5},
        "admin_mode": True,
    })

    assert result["ok"] is True
    assert result["result"]["outputs"] == [6, 7]


def test_tool_execute_plan_failure():
    """Test plan execution with unknown intent."""
    plan_dict = {
        "id": "test_plan_003",
        "meta": {
            "description": "Plan with unknown intent",
            "author": "pytest",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "Hi"}},
            {"intent": "unknown.intent", "args": {}},
        ],
    }

    result = tool_execute_plan({"plan": plan_dict, "admin_mode": True})

    assert result["ok"] is False
    assert "unknown.intent" in result["error"].lower()


def test_tool_load_plan_from_memory():
    """Test loading plan from memory."""
    memory = MemoryManager()

    # Store a plan in memory
    plan_data = {
        "id": "stored_plan_001",
        "meta": {
            "description": "Stored plan",
            "author": "pytest",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "Loaded"}},
        ],
    }
    memory.write("plans.test_workflow", plan_data, tier="L2")

    # Load it via tool
    result = tool_load_plan_from_memory({
        "key": "plans.test_workflow",
        "memory": memory,
    })

    assert result["ok"] is True
    assert result["result"]["id"] == "stored_plan_001"
    assert len(result["result"]["steps"]) == 1


def test_tool_load_plan_not_found():
    """Test loading non-existent plan from memory."""
    memory = MemoryManager()

    result = tool_load_plan_from_memory({
        "key": "plans.nonexistent",
        "memory": memory,
    })

    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_register_chat_os_tools():
    """Test registering tools with agent kernel."""
    tool_registry = ToolRegistry()

    # Register CHAT OS tools
    register_chat_os_tools(tool_registry)

    # Check tools are registered
    tools = tool_registry.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "plan.execute" in tool_names
    assert "plan.load" in tool_names

    # Check tool metadata
    plan_execute_tool = next(t for t in tools if t["name"] == "plan.execute")
    assert plan_execute_tool["scope"] == "action"
    assert plan_execute_tool["requires_token"] is True

    plan_load_tool = next(t for t in tools if t["name"] == "plan.load")
    assert plan_load_tool["scope"] == "info"


def test_end_to_end_plan_execution_via_registry():
    """Test executing a plan through the full tool registry flow."""
    tool_registry = ToolRegistry()
    register_chat_os_tools(tool_registry)

    plan_dict = {
        "id": "e2e_plan",
        "meta": {
            "description": "End-to-end test",
            "author": "pytest",
            "max_time_ms": 5000,
        },
        "steps": [
            {"intent": "test.echo", "args": {"message": "E2E"}},
        ],
    }

    # Execute via tool registry (requires token)
    result = tool_registry.call_with_auto_token(
        name="plan.execute",
        args={"plan": plan_dict, "admin_mode": True},
        ttl_s=10,
        budget_ms=5000,
    )

    assert result["ok"] is True
    assert result["result"]["steps_completed"] == 1
    assert result["result"]["outputs"][0] == "E2E"
