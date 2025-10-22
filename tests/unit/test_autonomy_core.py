"""
Test autonomy core functionality
"""

import asyncio
import pytest
import time
from datetime import datetime
from typing import Dict

from src.astra.autonomy.autonomy_core import (
    AutonomyCore, AutonomyState, RiskLevel, TaskContext
)


@pytest.fixture
def autonomy_core():
    """Create autonomy core instance"""
    return AutonomyCore(
        check_interval=0.1,
        min_priority=1,
        max_priority=10
    )


class TestAutonomyCore:
    """Test autonomy core functionality"""
    
    @pytest.mark.asyncio
    async def test_lifecycle(self, autonomy_core):
        """Test autonomy core lifecycle"""
        # Check initial state
        assert autonomy_core.state == AutonomyState.IDLE
        
        # Start
        await autonomy_core.start()
        assert autonomy_core.state == AutonomyState.RUNNING
        
        # Pause
        await autonomy_core.pause()
        assert autonomy_core.state == AutonomyState.PAUSED
        
        # Resume  
        await autonomy_core.resume()
        assert autonomy_core.state == AutonomyState.RUNNING
        
        # Stop
        await autonomy_core.stop()
        assert autonomy_core.state == AutonomyState.STOPPED

    @pytest.mark.asyncio
    async def test_task_submission(self, autonomy_core):
        """Test task submission and tracking"""
        # Start core
        await autonomy_core.start()
        
        # Submit task with longer timeout
        task_id = await autonomy_core.submit_task({
            "objective": "Test task",
            "priority": 5,
            "risk_level": RiskLevel.LOW,
            "timeout": 2.0  # Longer timeout
        })
        
        assert task_id is not None
        assert task_id in autonomy_core.active_tasks
        
        # Check initial status
        status = autonomy_core.get_task_status(task_id)
        assert status is not None
        assert status["status"] == "active"
        
        # Wait for task to start execution
        await asyncio.sleep(0.3)
        
        # Wait for task completion (should take ~0.2 seconds with 2s timeout)
        start_time = time.time()
        while True:
            status = autonomy_core.get_task_status(task_id)
            if status["status"] == "completed":
                break
                
            # Timeout after 2 seconds
            if time.time() - start_time > 2:
                raise TimeoutError("Task did not complete in time")
                
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_sensor_triggers(self, autonomy_core):
        """Test sensor monitoring and trigger firing"""
        # Add test trigger
        trigger = {
            "id": "test_trigger",
            "conditions": {
                "test_sensor": 5.0
            },
            "task": {
                "objective": "Test task",
                "priority": 3
            }
        }
        autonomy_core.add_trigger(trigger)
        
        # Start core
        await autonomy_core.start()
        
        # Update sensor below threshold
        autonomy_core.update_sensors({
            "test_sensor": 3.0
        })
        await asyncio.sleep(0.2)  # Wait for check cycle
        assert autonomy_core.stats["trigger_fires"] == 0
        
        # Update sensor above threshold
        autonomy_core.update_sensors({
            "test_sensor": 6.0
        })
        await asyncio.sleep(0.2)  # Wait for check cycle
        assert autonomy_core.stats["trigger_fires"] == 1
        
        await autonomy_core.stop()

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self, autonomy_core):
        """Test concurrent task execution"""
        # Configure core for testing
        autonomy_core.check_interval = 0.1  # Faster check interval
        await autonomy_core.start()
        
        # Submit tasks with longer timeouts
        task_count = 3
        task_timeouts = [2.0, 2.0, 2.0]  # All tasks take 2 seconds
        task_ids = []
        
        for i in range(task_count):
            task = {
                "objective": f"Task {i}",
                "priority": i + 1,
                "timeout": task_timeouts[i]
            }
            task_id = await autonomy_core.submit_task(task)
            assert task_id is not None, f"Failed to submit task {i}"
            task_ids.append(task_id)
            await asyncio.sleep(0.1)  # Brief delay between submissions
            
        # Verify all tasks are active
        assert len(autonomy_core.active_tasks) == task_count, (
            f"Expected {task_count} active tasks, got {len(autonomy_core.active_tasks)}. "
            f"Tasks: {task_ids}, Active: {list(autonomy_core.active_tasks.keys())}"
        )
        
        # Wait for tasks to start executing (should take about 1 second)
        await asyncio.sleep(1.0)
        
        # Should still be executing
        active_tasks = len(autonomy_core.active_tasks)
        assert active_tasks > 0, (
            f"Expected tasks still running after 1s, but found none. "
            f"Active: {active_tasks}, Completed: {len(autonomy_core.completed_tasks)}"
        )
        
        # Wait for completion (should take another 1 second)
        await asyncio.sleep(1.5)
        
        # Verify all tasks completed
        assert len(autonomy_core.completed_tasks) == task_count, (
            f"Not all tasks completed. Active: {len(autonomy_core.active_tasks)}, "
            f"Completed: {len(autonomy_core.completed_tasks)}, "
            f"Failed: {len(autonomy_core.failed_tasks)}"
        )
        
        # Verify no tasks failed
        assert len(autonomy_core.failed_tasks) == 0, (
            f"Found failed tasks: {list(autonomy_core.failed_tasks.keys())}"
        )
        
        # Verify no tasks still active
        assert len(autonomy_core.active_tasks) == 0, (
            f"Tasks still active: {list(autonomy_core.active_tasks.keys())}"
        )
        
        await autonomy_core.stop()

    def test_risk_assessment(self, autonomy_core):
        """Test task risk assessment"""
        tasks = [
            {
                "objective": "Low risk task",
                "risk_level": RiskLevel.LOW
            },
            {
                "objective": "Medium risk task", 
                "risk_level": RiskLevel.MEDIUM
            },
            {
                "objective": "High risk task",
                "risk_level": RiskLevel.HIGH
            },
            {
                "objective": "Critical risk task",
                "risk_level": RiskLevel.CRITICAL
            }
        ]
        
        for task in tasks:
            context = TaskContext(
                task_id="test",
                objective=task["objective"],
                risk_level=task["risk_level"]
            )
            assert context.risk_level == task["risk_level"]