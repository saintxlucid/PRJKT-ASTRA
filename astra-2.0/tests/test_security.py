"""
ASTRA 2.0 Security Kernel Tests
"""
import pytest
from core.security.permission_kernel import (
    PermissionKernel, 
    PermissionDenied,
    require_permission
)
from core.security.auth_identity import IdentityManager
from core.security.activity_audit import ActivityAuditor

def test_permission_kernel_basic():
    """Test basic permission kernel functionality"""
    kernel = PermissionKernel()
    
    # Register test user
    context = kernel.register_user("test_user", ["monitor"])
    assert "system.process.list" in context.capabilities
    assert "system.process.kill" not in context.capabilities
    
    # Test permission check
    assert kernel.has_permission("test_user", "system.process.list")
    assert not kernel.has_permission("test_user", "system.process.kill")
    
def test_permission_decorator():
    """Test permission decorator behavior"""
    kernel = PermissionKernel()
    kernel.register_user("test_user", ["monitor"])
    
    @require_permission("system.process.list")
    def safe_function(user_id: str = None):
        return True
        
    # Should succeed
    assert safe_function(user_id="test_user")
    
    # Should fail - missing user_id
    with pytest.raises(PermissionDenied):
        safe_function()
        
    # Should fail - wrong permission
    @require_permission("system.process.kill")
    def unsafe_function(user_id: str = None):
        return True
        
    with pytest.raises(PermissionDenied):
        unsafe_function(user_id="test_user")
        
def test_identity_manager(tmp_path):
    """Test identity management"""
    store_path = tmp_path / "identities.json"
    manager = IdentityManager(str(store_path))
    
    # Create identity
    identity = manager.create_identity(
        "test_user",
        {"monitor"},
        name="Test User",
        email="test@example.com"
    )
    
    assert identity.user_id == "test_user"
    assert "monitor" in identity.roles
    assert identity.api_key  # Should have API key
    
    # Validate API key
    found = manager.validate_api_key(identity.api_key)
    assert found and found.user_id == "test_user"
    
    # Update roles
    updated = manager.update_roles("test_user", {"monitor", "backup"})
    assert updated and "backup" in updated.roles
    
    # Rotate API key
    old_key = identity.api_key
    new_key = manager.rotate_api_key("test_user")
    assert new_key and new_key != old_key
    
def test_activity_audit(tmp_path):
    """Test activity auditing"""
    db_path = tmp_path / "audit.db"
    auditor = ActivityAuditor(str(db_path))
    
    # Log test events
    auditor.log_event("test.action", {"value": 123})
    auditor.log_event("test.error", {"error": "failed"}, severity="error")
    
    # Query events
    events = auditor.query_events(action_filter="test")
    assert len(events) == 2
    assert events[0]["action"] == "test.error"
    assert events[1]["action"] == "test.action"
    
    # Get summary
    summary = auditor.get_activity_summary(hours=1)
    assert summary["total_events"] == 2
    assert "test.action" in summary["action_counts"]
    assert "error" in summary["severity_counts"]