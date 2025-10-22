# tests/unit/test_task_planner.py
import pytest

pytestmark = pytest.mark.asyncio  # apply to all tests in this file

async def test_task_planner_basic_plan(task_planner):
    plan = await task_planner.create_plan({
        "objective": "Test objective",
        "constraints": {"time_limit": 10.0}
    })
    assert hasattr(plan, "steps")
    assert len(plan.steps) > 0, "planner should return at least one step"
    assert plan.total_cost > 0
    assert plan.estimated_duration > 0

async def test_policy_blocks_forbidden_paths(task_planner):
    with pytest.raises((PermissionError, RuntimeError)):
        await task_planner.create_plan({
            "objective": "write to system32",
            "template": "forbidden_paths"
        })

async def test_task_execution_basic(task_planner):
    plan = await task_planner.create_plan({
        "objective": "Test execution",
        "template": "basic_test"
    })
    result = await task_planner.execute_plan(plan)
    assert result is not None





@pytest.mark.asyncio
async def test_create_plan(task_planner: TaskPlanner):
    """Test plan creation"""
    task = {
        "objective": "Test objective",
        "constraints": {"time_limit": 10.0}
    }
    
    plan = task_planner.create_plan(task)
    
    assert plan.objective == task["objective"]
    assert plan.status == TaskStatus.PENDING
    assert len(plan.steps) > 0
    assert plan.total_cost > 0
    assert plan.estimated_duration > 0


@pytest.mark.asyncio
async def test_execute_success(task_planner: TaskPlanner):
    """Test successful execution"""
    # Create plan with success step
    plan = task_planner.create_plan({
        "objective": "Test success",
        "template": "success_test"
    })
    
    # Override steps for test
    plan.steps = [
        task_planner.create_task_step(
            "success",
            "test",
            {"arg1": "test"}
        )
    ]
    
    # Execute
    result = await task_planner.execute_plan(plan)
    
    assert result["ok"]
    assert plan.status == TaskStatus.COMPLETED
    assert len(result["results"]) == 1
    
    step_result = list(result["results"].values())[0]
    assert step_result["ok"]
    assert step_result["result"]["status"] == "success"


@pytest.mark.asyncio
async def test_execute_failure(task_planner: TaskPlanner):
    """Test failure handling"""
    # Create plan with failure step
    plan = task_planner.create_plan({
        "objective": "Test failure",
        "template": "failure_test"
    })
    
    # Override steps for test
    plan.steps = [
        task_planner.create_task_step(
            "failure",
            "test",
            {"arg1": "test"}
        )
    ]
    
    # Execute
    result = await task_planner.execute_plan(plan)
    
    assert not result["ok"]
    assert plan.status == TaskStatus.FAILED
    assert len(result["results"]) == 1
    
    step_result = list(result["results"].values())[0]
    assert not step_result["ok"]
    assert "Simulated failure" in str(step_result["result"])


@pytest.mark.asyncio
async def test_parallel_execution(task_planner: TaskPlanner):
    """Test concurrent step execution"""
    # Create plan with multiple slow steps
    plan = task_planner.create_plan({
        "objective": "Test parallel",
        "template": "parallel_test"
    })
    
    # Override with slow steps
    plan.steps = [
        task_planner.create_task_step(
            "slow",
            "test",
            {"id": i}
        )
        for i in range(3)
    ]
    
    # Execute with timing
    start = datetime.now()
    result = await task_planner.execute_plan(plan)
    duration = (datetime.now() - start).total_seconds()
    
    # Should complete in ~1 second (2 groups of parallel execution)
    assert duration < 2.0
    assert result["ok"]
    assert plan.status == TaskStatus.COMPLETED
    assert len(result["results"]) == 3
    
    # Verify all steps completed
    for step_result in result["results"].values():
        assert step_result["ok"]
        assert step_result["result"]["status"] == "slow_success"