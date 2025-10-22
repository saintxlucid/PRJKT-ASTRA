"""Test suite for Action Registry."""
import pytest
from astra.orchestrator.registry import (
    action, get_action, list_actions, get_action_timeout,
    start_dry_run, get_dry_run_plan, clear_dry_run
)

def test_action_registration():
    """Test basic action registration and retrieval."""
    @action("test.echo")
    def echo(msg: str):
        return {"msg": msg}
    
    # Action should be retrievable
    fn = get_action("test.echo")
    assert fn is not None
    
    # Should appear in action list
    assert "test.echo" in list_actions()

def test_action_execution():
    """Test action execution with success and failure."""
    @action("test.div")
    def div(a: int, b: int):
        return a / b
    
    # Successful execution
    result = div(10, 2)
    assert result["ok"] is True
    assert result["result"] == 5
    assert "latency_ms" in result
    
    # Failed execution
    result = div(1, 0)
    assert result["ok"] is False
    assert "division by zero" in result["error"]
    assert "latency_ms" in result

def test_action_lookup():
    """Test error handling for missing actions."""
    with pytest.raises(KeyError):
        get_action("nonexistent.action")

def test_action_timeout():
    """Test action timeout parameter."""
    @action("test.wait", timeout_s=1)
    def wait():
        return "done"
    
    assert get_action_timeout("test.wait") == 1

def test_dry_run():
    """Test action dry run functionality."""
    @action("test.add", deterministic=True)
    def add(a: int, b: int):
        return a + b

    @action("test.greet")
    def greet(name: str):
        return f"Hello {name}!"
    
    # Start dry run session
    plan_id = start_dry_run()
    
    # Record some actions
    add(5, 3, _dry_run_id=plan_id)
    greet("Alice", _dry_run_id=plan_id)
    
    # Get and validate plan
    plan = get_dry_run_plan(plan_id)
    assert len(plan) == 2
    
    # Verify first action (add)
    assert plan[0]["name"] == "test.add"
    assert plan[0]["args"] == (5, 3)
    assert plan[0]["deterministic"] == True
    
    # Verify second action (greet)
    assert plan[1]["name"] == "test.greet"
    assert plan[1]["args"] == ("Alice",)
    assert plan[1]["deterministic"] == False
    
    # Test plan cleanup
    clear_dry_run(plan_id)
    with pytest.raises(KeyError):
        get_dry_run_plan(plan_id)