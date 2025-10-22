"""
Unit tests for memory quota system.
"""

import pytest
import json
from astra.auth.quota import QuotaManager, QuotaConfig

@pytest.fixture
def strict_quota_manager():
    """Create quota manager with strict limits for testing."""
    config = QuotaConfig(
        max_keys=5,
        max_value_size=100,
        max_total_size=500
    )
    return QuotaManager(config)

def test_key_quota():
    """Test enforcement of maximum keys quota."""
    qm = strict_quota_manager()
    
    # Should allow up to max_keys
    for i in range(5):
        assert qm.check_key_quota("test-user", i)
        
    # Should reject above max_keys
    assert not qm.check_key_quota("test-user", 5)
    assert not qm.check_key_quota("test-user", 10)

def test_value_size_quota():
    """Test enforcement of value size quota."""
    qm = strict_quota_manager()
    
    # Small value should be allowed
    small_value = {"data": "x" * 50}
    assert qm.check_value_size("test-user", small_value)
    
    # Large value should be rejected
    large_value = {"data": "x" * 150}
    assert not qm.check_value_size("test-user", large_value)

def test_total_size_quota():
    """Test enforcement of total size quota."""
    qm = strict_quota_manager()
    
    # Add values up to near limit
    value = {"data": "x" * 100}
    for _ in range(4):
        assert qm.check_total_quota("test-user", value)
        qm.update_usage("test-user", None, value)
    
    # Next value should be rejected
    assert not qm.check_total_quota("test-user", value)

def test_usage_tracking():
    """Test accurate tracking of memory usage."""
    qm = strict_quota_manager()
    
    # Add initial value
    value1 = {"data": "test1"}
    size1 = len(json.dumps(value1).encode('utf-8'))
    qm.update_usage("test-user", None, value1)
    assert qm._user_sizes["test-user"] == size1
    
    # Update value
    value2 = {"data": "test2"}
    size2 = len(json.dumps(value2).encode('utf-8'))
    qm.update_usage("test-user", value1, value2)
    assert qm._user_sizes["test-user"] == size2
    
    # Delete value
    qm.update_usage("test-user", value2, None)
    assert qm._user_sizes["test-user"] == 0

def test_multi_user_isolation():
    """Test quota tracking isolation between users."""
    qm = strict_quota_manager()
    
    # Add same value for different users
    value = {"data": "test"}
    size = len(json.dumps(value).encode('utf-8'))
    
    qm.update_usage("user1", None, value)
    qm.update_usage("user2", None, value)
    
    assert qm._user_sizes["user1"] == size
    assert qm._user_sizes["user2"] == size
    
    # Clear one user
    qm.clear_usage("user1")
    assert "user1" not in qm._user_sizes
    assert qm._user_sizes["user2"] == size

def test_quota_config():
    """Test quota configuration validation."""
    # Default config should be reasonable
    qm = QuotaManager()
    assert qm.config.max_keys > 0
    assert qm.config.max_value_size > 0
    assert qm.config.max_total_size > 0
    
    # Custom config should be respected
    config = QuotaConfig(max_keys=10, max_value_size=1000, max_total_size=5000)
    qm = QuotaManager(config)
    assert qm.config.max_keys == 10
    assert qm.config.max_value_size == 1000
    assert qm.config.max_total_size == 5000