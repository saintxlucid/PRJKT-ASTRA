"""
Task System Integration Tests

Validates:
1. Component initialization
2. Task submission and execution
3. Agent registration and coordination
4. Constraint enforcement
5. Metrics collection
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

from astra.task.task_system import TaskSystemManager
from astra.coordinator.agent_coordinator import AgentCapability
from astra.constraints.constraint_system import ResourceType, ConstraintStatus


class MockExecutor:
    """Mock tool executor for testing"""
    
    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.calls = []
        
    async def execute(self, action: str, **kwargs):
        self.calls.append((action, kwargs))
        return self.responses.get(action, {"ok": True})


@pytest.fixture
async def task_system():
    """Create task system instance"""
    system = TaskSystemManager(
        max_parallel_tasks=2,
        max_retries=1
    )
    await system.start()
    yield system
    await system.stop()
    

@pytest.fixture
def mock_executor():
    """Create mock executor"""
    return MockExecutor()


@pytest.mark.asyncio
async def test_task_system_initialization(task_system):
    """Test system initialization"""
    assert task_system.started
    
    status = task_system.get_status()
    assert status["started"]
    assert len(status["agents"]) == 0
    assert status["tasks"]["active"] == 0
    

@pytest.mark.asyncio
async def test_agent_registration(task_system):
    """Test agent registration"""
    agent_id = task_system.register_agent(
        name="test_agent",
        capabilities=[{
            "tool": "test",
            "actions": ["execute"],
            "max_parallel": 2
        }]
    )
    
    assert agent_id
    
    # Update heartbeat
    await task_system.update_agent_heartbeat(agent_id)
    
    # Verify registration
    status = task_system.get_status()
    assert len(status["agents"]) == 1
    assert status["agents"][0]["id"] == agent_id
    

@pytest.mark.asyncio
async def test_task_submission(task_system, mock_executor):
    """Test task submission and execution"""
    # Register agent
    agent_id = task_system.register_agent(
        name="test_agent",
        capabilities=[{
            "tool": "test",
            "actions": ["execute"],
            "max_parallel": 2
        }]
    )
    
    # Submit task
    task = {
        "objective": "test task",
        "tool": "test",
        "action": "execute",
        "args": {"param": "value"}
    }
    
    result = await task_system.submit_task(task, mock_executor)
    assert result["ok"]
    assert result["agent_id"] == agent_id
    
    # Verify execution
    status = task_system.get_task_status(result["task_id"])
    assert status["ok"]
    assert status["status"] in ["completed", "running"]
    

@pytest.mark.asyncio
async def test_constraint_enforcement(task_system):
    """Test constraint enforcement"""
    # Update concurrency usage
    system = task_system.constraint_system
    system.update_resource_usage("system.concurrency", 8.0)
    
    # Validate constraints
    violations = system.validate_all()
    assert len(violations) == 1
    assert violations[0].resource == "system.concurrency"
    assert violations[0].status == ConstraintStatus.WARNING
    
    # Update to violation level
    system.update_resource_usage("system.concurrency", 12.0)
    violations = system.validate_all()
    assert len(violations) == 1
    assert violations[0].status == ConstraintStatus.VIOLATED
    

@pytest.mark.asyncio
async def test_metrics_collection(task_system, mock_executor):
    """Test metrics collection"""
    # Register agent
    task_system.register_agent(
        name="test_agent",
        capabilities=[{
            "tool": "test",
            "actions": ["execute"],
            "max_parallel": 2
        }]
    )
    
    # Submit tasks
    tasks = []
    for i in range(3):
        task = {
            "objective": f"test task {i}",
            "tool": "test",
            "action": "execute"
        }
        result = await task_system.submit_task(task, mock_executor)
        tasks.append(result)
        
    # Get metrics
    metrics = task_system.get_metrics()
    
    assert "execution" in metrics
    assert "constraints" in metrics
    assert "coordinator" in metrics
    
    execution = metrics["execution"]
    assert execution["active_tasks"] <= 2  # Max parallel
    assert execution["completed_tasks"] > 0
    

@pytest.mark.asyncio
async def test_system_shutdown(task_system):
    """Test clean system shutdown"""
    await task_system.stop()
    assert not task_system.started
    
    status = task_system.get_status()
    assert not status["started"]
    assert len(status["agents"]) == 0