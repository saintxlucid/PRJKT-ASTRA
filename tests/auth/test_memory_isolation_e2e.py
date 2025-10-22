"""
End-to-end tests for memory isolation system.
"""

import pytest
import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from astra.auth.isolation import memory_isolation
from astra.auth.middleware import MemoryIsolationMiddleware
from astra.auth.quota import QuotaConfig, quota_manager

# Test data models
class MemoryItem(BaseModel):
    key: str
    value: str

# Test dependencies
async def get_test_user_id(user_id: str = "test-user-1"):
    return user_id

# Create test app
app = FastAPI()
app.add_middleware(
    MemoryIsolationMiddleware,
    user_id_extractor=lambda req: req.headers.get("X-Test-User")
)

@app.post("/memory")
async def store_memory(
    item: MemoryItem,
    user_id: str = Depends(get_test_user_id)
):
    await memory_isolation.set_user_memory(user_id, item.key, item.value)
    return {"status": "success"}

@app.get("/memory/{key}")
async def get_memory(
    key: str,
    user_id: str = Depends(get_test_user_id)
):
    value = await memory_isolation.get_user_memory(user_id, key)
    if value is None:
        raise HTTPException(status_code=404)
    return {"key": key, "value": value}

@app.get("/memory")
async def list_memory(
    user_id: str = Depends(get_test_user_id)
):
    keys = await memory_isolation.list_user_memory(user_id)
    return {"keys": keys}

@app.delete("/memory/{key}")
async def delete_memory(
    key: str,
    user_id: str = Depends(get_test_user_id)
):
    success = await memory_isolation.delete_user_memory(user_id, key)
    if not success:
        raise HTTPException(status_code=404)
    return {"status": "success"}

# Tests
@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture(autouse=True)
async def clear_memory():
    # Clear memory before each test
    for user_id in ["test-user-1", "test-user-2"]:
        await memory_isolation.clear_user_memory(user_id)
        quota_manager.clear_usage(user_id)
    yield

def test_memory_isolation(test_client):
    """Test that memory is properly isolated between users."""
    # User 1 stores memory
    response = test_client.post(
        "/memory",
        json={"key": "test-key", "value": "user-1-value"},
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200

    # User 2 stores memory with same key
    response = test_client.post(
        "/memory",
        json={"key": "test-key", "value": "user-2-value"},
        headers={"X-Test-User": "test-user-2"}
    )
    assert response.status_code == 200

    # User 1 gets their value
    response = test_client.get(
        "/memory/test-key",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200
    assert response.json()["value"] == "user-1-value"

    # User 2 gets their value
    response = test_client.get(
        "/memory/test-key",
        headers={"X-Test-User": "test-user-2"}
    )
    assert response.status_code == 200
    assert response.json()["value"] == "user-2-value"

def test_quota_limits(test_client):
    """Test that memory quotas are enforced."""
    # Configure strict quotas for testing
    quota_manager.config = QuotaConfig(
        max_keys=2,
        max_value_size=20,
        max_total_size=50
    )

    # Test max keys limit
    for i in range(3):
        response = test_client.post(
            "/memory",
            json={"key": f"key-{i}", "value": "test"},
            headers={"X-Test-User": "test-user-1"}
        )
        if i < 2:
            assert response.status_code == 200
        else:
            assert response.status_code in [400, 422]

    # Test value size limit
    response = test_client.post(
        "/memory",
        json={"key": "big-value", "value": "x" * 30},
        headers={"X-Test-User": "test-user-2"}
    )
    assert response.status_code in [400, 422]

def test_concurrent_access(test_client):
    """Test concurrent access to memory."""
    async def concurrent_writes():
        tasks = []
        for i in range(10):
            tasks.append(
                memory_isolation.set_user_memory(
                    "test-user-1",
                    f"concurrent-{i}",
                    f"value-{i}"
                )
            )
        await asyncio.gather(*tasks)

    # Perform concurrent writes
    asyncio.run(concurrent_writes())

    # Verify all writes succeeded
    response = test_client.get(
        "/memory",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200
    assert len(response.json()["keys"]) == 10

def test_memory_operations(test_client):
    """Test basic memory CRUD operations."""
    # Create memory
    response = test_client.post(
        "/memory",
        json={"key": "test-key", "value": "test-value"},
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200

    # Read memory
    response = test_client.get(
        "/memory/test-key",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200
    assert response.json()["value"] == "test-value"

    # List memory
    response = test_client.get(
        "/memory",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200
    assert "test-key" in response.json()["keys"]

    # Delete memory
    response = test_client.delete(
        "/memory/test-key",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 200

    # Verify deletion
    response = test_client.get(
        "/memory/test-key",
        headers={"X-Test-User": "test-user-1"}
    )
    assert response.status_code == 404