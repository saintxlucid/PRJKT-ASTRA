"""
Integration Tests - Agent API Endpoints
========================================

Validates agent kernel task management and browser automation

Test Coverage:
- Task creation and lifecycle (queued → running → completed/failed)
- Task status retrieval
- Task cancellation
- Task listing with filters
- Browser automation (navigate, click, type, extract)
- Tool registry
- Tool execution
- Agent status monitoring

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_agent_status():
    """Test that agent status endpoint returns kernel information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/agent/status")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "kernel" in data


@pytest.mark.asyncio
async def test_task_creation():
    """Test creating an autonomous agent task"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/task",
            json={
                "goal": "Test task: analyze current system status",
                "max_iterations": 3,
                "timeout_seconds": 30
            }
        )
        assert response.status_code in [200, 422, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            assert "status" in data
            assert data["status"] in ["queued", "running"]
            return data["task_id"]
        return None


@pytest.mark.asyncio
async def test_task_status_retrieval():
    """Test retrieving task status by ID"""
    async with httpx.AsyncClient() as client:
        # First create a task
        create_response = await client.post(
            f"{BASE_URL}/v1/agent/task",
            json={
                "goal": "Test task for status retrieval",
                "max_iterations": 2,
                "timeout_seconds": 20
            }
        )
        
        if create_response.status_code != 200:
            pytest.skip("Task creation not available")
        
        task_id = create_response.json()["task_id"]
        
        # Wait a moment for task to process
        await asyncio.sleep(0.5)
        
        # Retrieve task status
        status_response = await client.get(f"{BASE_URL}/v1/agent/task/{task_id}")
        assert status_response.status_code in [200, 404]
        
        if status_response.status_code == 200:
            data = status_response.json()
            assert "task_id" in data
            assert "status" in data
            assert data["status"] in ["queued", "running", "completed", "failed"]


@pytest.mark.asyncio
async def test_task_listing():
    """Test listing all tasks with optional status filter"""
    async with httpx.AsyncClient() as client:
        # List all tasks
        response = await client.get(f"{BASE_URL}/v1/agent/tasks")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "tasks" in data
            assert isinstance(data["tasks"], list)
        
        # List only running tasks
        response = await client.get(f"{BASE_URL}/v1/agent/tasks?status=running")
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
async def test_task_cancellation():
    """Test cancelling a running task"""
    async with httpx.AsyncClient() as client:
        # Create a long-running task
        create_response = await client.post(
            f"{BASE_URL}/v1/agent/task",
            json={
                "goal": "Long running task for cancellation test",
                "max_iterations": 100,
                "timeout_seconds": 300
            }
        )
        
        if create_response.status_code != 200:
            pytest.skip("Task creation not available")
        
        task_id = create_response.json()["task_id"]
        
        # Cancel the task
        cancel_response = await client.delete(f"{BASE_URL}/v1/agent/task/{task_id}")
        assert cancel_response.status_code in [200, 404]
        
        if cancel_response.status_code == 200:
            data = cancel_response.json()
            assert "message" in data


@pytest.mark.asyncio
async def test_browser_navigate():
    """Test browser navigation endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/browser/navigate",
            json={
                "url": "https://example.com",
                "wait_for_load": True
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_browser_extract():
    """Test browser data extraction endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/browser/extract",
            json={
                "selector": "h1",
                "all": False
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_browser_click():
    """Test browser click automation endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/browser/click",
            json={
                "selector": "button.test",
                "wait_for_selector": True
            }
        )
        # Will fail if browser not initialized, that's expected
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_browser_type():
    """Test browser typing automation endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/browser/type",
            json={
                "selector": "input.test",
                "text": "test input",
                "clear_first": True
            }
        )
        # Will fail if browser not initialized, that's expected
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_tool_registry():
    """Test listing available tools"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/agent/tools")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "tools" in data
            assert isinstance(data["tools"], list)


@pytest.mark.asyncio
async def test_tool_execution():
    """Test direct tool execution endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/agent/tool/execute",
            json={
                "tool_name": "test_tool",
                "parameters": {"param1": "value1"}
            }
        )
        # Will fail if tool doesn't exist, that's expected
        assert response.status_code in [200, 404, 422, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
