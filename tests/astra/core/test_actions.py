"""Unit tests for action registry."""

import pytest
from datetime import datetime, UTC, timedelta
from astra.core.actions import (
    ActionRegistry,
    action,
    get_action_registry,
    ActionContext,
    ActionResult
)

def test_action_registration():
    """Test basic action registration and execution."""
    registry = ActionRegistry()
    
    @registry.register("test.add",
                      description="Add two numbers",
                      supports_dry_run=True)
    def add(a: int, b: int) -> int:
        return a + b
        
    assert len(registry.list_actions()) == 1
    action_info = registry.list_actions()[0]
    assert action_info["name"] == "test.add"
    assert action_info["description"] == "Add two numbers"
    assert action_info["supports_dry_run"] == True
    
    # Test normal execution
    result = registry.execute("test.add", 2, 3)
    assert result == 5
    
    # Test dry run
    result = registry.execute("test.add", 2, 3, dry_run=True)
    assert result is None  # dry run returns None for supported actionsdef test_action_decorator():
    """Test action decorator functionality."""
    registry = ActionRegistry()
    
    multiply = registry.register(
        "test.multiply",
        timeout_s=5.0,
        description="Multiply two numbers",
        metadata={"category": "math"}
    )(lambda a, b: a * b)
        
    actions = registry.list_actions()
    assert len(actions) == 1
    action_info = actions[0]
    assert action_info["name"] == "test.multiply"
    assert action_info["timeout_s"] == 5.0
    assert action_info["metadata"] == {"category": "math"}

def test_action_results():
    """Test action result tracking."""
    registry = ActionRegistry()
    
    def register_action():
        @registry.register("test.divide")
        def divide(a: int, b: int) -> float:
            return a / b
    
    register_action()
    # Test successful execution
    result = registry.execute("test.divide", 10, 2)
    assert result == 5.0
    
    # Get last action result
    action_id = list(registry._results.keys())[-1]
    result = registry.get_result(action_id)
    assert isinstance(result, ActionResult)
    assert result.success == True
    assert result.result == 5.0
    assert result.error is None
    
    # Test failed execution
    with pytest.raises(ZeroDivisionError):
        registry.execute("test.divide", 1, 0)
    
    # Get failed action result    
    action_id = list(registry._results.keys())[-1]
    result = registry.get_result(action_id)
    assert isinstance(result, ActionResult)
    assert result.success == False
    assert result.error is not None
    
def test_action_context():
    """Test action context functionality."""
    registry = ActionRegistry()
    
    execution_order = []
    parent_id = None
    
    @registry.register("test.parent",
                      description="Parent action")
    def parent_action() -> str:
        nonlocal parent_id
        execution_order.append("parent_start")
        parent_id = registry.current_action_id
        assert parent_id is not None
        result = registry.execute("test.child", parent_id=parent_id)
        execution_order.append("parent_end")
        return result
    
    @registry.register("test.child",
                      description="Child action")
    def child_action() -> str:
        execution_order.append("child_start")
        result = registry.get_result(registry.current_action_id or "")
        assert result is not None
        assert result.parent_id == parent_id
        execution_order.append("child_end")
        return "done"
    
    result = registry.execute("test.parent")
    assert result == "done"
    assert execution_order == [
        "parent_start",
        "child_start",
        "child_end",
        "parent_end"
    ]

def test_invalid_actions():
    """Test error cases."""
    registry = ActionRegistry()
    
    # Test duplicate registration
    @registry.register("test.action")
    def action1(): pass
    
    with pytest.raises(ValueError):
        @registry.register("test.action")
        def action2(): pass
        
    # Test unknown action
    with pytest.raises(KeyError):
        registry.execute("unknown.action")
        
    # Test dry run on unsupported action
    @registry.register("test.no_dry_run",
                      supports_dry_run=False)
    def no_dry_run(): pass
    
    with pytest.raises(ValueError):
        registry.execute("test.no_dry_run", dry_run=True)