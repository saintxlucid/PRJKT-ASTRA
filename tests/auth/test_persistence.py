"""
Integration tests for memory persistence.
"""

import pytest
import os
import asyncio
from pathlib import Path
import aiosqlite

from astra.auth.persistence import MemoryStore
from astra.auth.config import AuthConfig

@pytest.fixture
async def test_db():
    """Create test database and cleanup after tests."""
    # Use test database path
    test_path = "data/test_memory.db"
    store = MemoryStore()
    store.db_path = test_path
    
    # Ensure clean state
    if os.path.exists(test_path):
        os.remove(test_path)
        
    # Create database
    await store.initialize()
    
    yield store
    
    # Cleanup
    if os.path.exists(test_path):
        os.remove(test_path)

@pytest.mark.asyncio
async def test_persistence_crud(test_db):
    """Test basic CRUD operations."""
    test_value = {"data": "test"}
    
    # Create
    await test_db.set("test-user", "test-key", test_value)
    
    # Read
    value = await test_db.get("test-user", "test-key")
    assert value == test_value
    
    # Update
    new_value = {"data": "updated"}
    await test_db.set("test-user", "test-key", new_value)
    value = await test_db.get("test-user", "test-key")
    assert value == new_value
    
    # Delete
    success = await test_db.delete("test-user", "test-key")
    assert success
    value = await test_db.get("test-user", "test-key")
    assert value is None

@pytest.mark.asyncio
async def test_persistence_list_keys(test_db):
    """Test listing keys."""
    # Add multiple values
    values = {
        "key1": {"data": "value1"},
        "key2": {"data": "value2"},
        "key3": {"data": "value3"}
    }
    
    for key, value in values.items():
        await test_db.set("test-user", key, value)
    
    # List keys
    keys = await test_db.list_keys("test-user")
    assert set(keys) == set(values.keys())
    
    # Different user should have no keys
    keys = await test_db.list_keys("other-user")
    assert len(keys) == 0

@pytest.mark.asyncio
async def test_persistence_clear(test_db):
    """Test clearing user memory."""
    # Add values for multiple users
    users = ["user1", "user2"]
    for user in users:
        await test_db.set(user, "key", {"data": f"value-{user}"})
    
    # Clear one user
    await test_db.clear("user1")
    
    # Check user1 cleared
    value = await test_db.get("user1", "key")
    assert value is None
    
    # Check user2 unaffected
    value = await test_db.get("user2", "key")
    assert value == {"data": "value-user2"}

@pytest.mark.asyncio
async def test_persistence_load_all(test_db):
    """Test loading all memory for a user."""
    # Add multiple values
    values = {
        "key1": {"data": "value1"},
        "key2": {"data": "value2"},
        "key3": {"data": "value3"}
    }
    
    for key, value in values.items():
        await test_db.set("test-user", key, value)
    
    # Load all
    memory = await test_db.load_all("test-user")
    assert memory == values

@pytest.mark.asyncio
async def test_persistence_concurrent_access(test_db):
    """Test concurrent access to persistence."""
    # Create multiple tasks writing to same key
    async def write_value(i):
        await test_db.set("test-user", "concurrent-key", {"count": i})
        
    tasks = [write_value(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    # Verify last write won
    value = await test_db.get("test-user", "concurrent-key")
    assert value["count"] in range(10)

@pytest.mark.asyncio
async def test_persistence_error_handling(test_db):
    """Test error handling in persistence operations."""
    # Test with invalid JSON
    with pytest.raises(Exception):
        await test_db.set("test-user", "key", object())
    
    # Test with closed database
    os.remove(test_db.db_path)
    with pytest.raises(Exception):
        await test_db.get("test-user", "key")