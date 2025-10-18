# tests/bridge/test_tool_bridge_service.py
"""Unit tests for Tool Bridge Service"""
import os
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Import the bridge service
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from astra.bridge import tool_bridge_service as bridge

client = TestClient(bridge.app)
API_KEY = bridge.API_KEY


class TestBridgeHealth:
    """Health and basic endpoint tests"""
    
    def test_health_endpoint(self):
        """Health check should work without auth"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert "version" in resp.json()
    
    def test_metrics_endpoint(self):
        """Metrics endpoint should return Prometheus format"""
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "bridge_calls_total" in resp.text


class TestAuthentication:
    """Authentication and authorization tests"""
    
    def test_tools_list_requires_auth(self):
        """Tools endpoint should require API key"""
        resp = client.get("/tools")
        assert resp.status_code == 403 or resp.status_code == 422
    
    def test_tools_list_with_valid_key(self):
        """Valid API key should grant access"""
        resp = client.get("/tools", headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
        assert "tools" in resp.json()
        assert len(resp.json()["tools"]) > 0
    
    def test_call_requires_auth(self):
        """Tool calls should require API key"""
        payload = {"tool_name": "shell", "args": {"cmd": "echo test"}}
        resp = client.post("/call", json=payload)
        assert resp.status_code == 403 or resp.status_code == 422
    
    def test_invalid_api_key(self):
        """Invalid API key should be rejected"""
        resp = client.get("/tools", headers={"x-api-key": "invalid-key"})
        assert resp.status_code == 403


class TestShellTool:
    """Shell tool adapter tests"""
    
    def test_shell_allowed_command(self):
        """Allowed shell command should execute"""
        payload = {"tool_name": "shell", "args": {"cmd": "echo hello"}}
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
        result = resp.json()
        assert result["ok"] is True
        assert "hello" in result["result"]["stdout"]
    
    def test_shell_disallowed_command(self):
        """Disallowed shell command should be rejected"""
        payload = {"tool_name": "shell", "args": {"cmd": "rm -rf /"}}
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 500
        assert "not allowed" in resp.json()["detail"].lower()
    
    def test_shell_missing_cmd(self):
        """Missing cmd argument should fail"""
        payload = {"tool_name": "shell", "args": {}}
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 500


class TestFileReadTool:
    """File read tool adapter tests"""
    
    def test_file_read_success(self, tmp_path, monkeypatch):
        """Reading file from safe directory should succeed"""
        safe_root = tmp_path / "safe"
        safe_root.mkdir()
        test_file = safe_root / "test.txt"
        test_file.write_text("test content")
        
        monkeypatch.setenv("BRIDGE_SAFE_ROOT", str(safe_root))
        
        payload = {
            "tool_name": "file_read",
            "args": {"path": str(test_file)}
        }
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
        result = resp.json()
        assert result["ok"] is True
        assert result["result"]["content"] == "test content"
    
    def test_file_read_outside_safe_root(self, tmp_path, monkeypatch):
        """Reading file outside safe root should fail"""
        safe_root = tmp_path / "safe"
        safe_root.mkdir()
        unsafe_file = tmp_path / "unsafe.txt"
        unsafe_file.write_text("unsafe")
        
        monkeypatch.setenv("BRIDGE_SAFE_ROOT", str(safe_root))
        
        payload = {
            "tool_name": "file_read",
            "args": {"path": str(unsafe_file)}
        }
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 500
        assert "not in allowed root" in resp.json()["detail"].lower()
    
    def test_file_read_nonexistent(self, tmp_path, monkeypatch):
        """Reading nonexistent file should fail"""
        safe_root = tmp_path / "safe"
        safe_root.mkdir()
        
        monkeypatch.setenv("BRIDGE_SAFE_ROOT", str(safe_root))
        
        payload = {
            "tool_name": "file_read",
            "args": {"path": str(safe_root / "nonexistent.txt")}
        }
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 500


class TestToolRegistry:
    """Tool registration and discovery tests"""
    
    def test_tool_not_found(self):
        """Calling nonexistent tool should return 404"""
        payload = {"tool_name": "nonexistent_tool", "args": {}}
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 404
    
    def test_list_registered_tools(self):
        """List endpoint should show all registered tools"""
        resp = client.get("/tools", headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
        tools = resp.json()["tools"]
        tool_names = [t["name"] for t in tools]
        assert "shell" in tool_names
        assert "file_read" in tool_names
        assert "llama" in tool_names


class TestAuditLog:
    """Audit logging tests"""
    
    def test_audit_recent_endpoint(self):
        """Recent audit endpoint should require auth"""
        resp = client.get("/audit/recent", headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
        assert "entries" in resp.json()
    
    def test_audit_log_created(self, tmp_path, monkeypatch):
        """Tool calls should write to audit log"""
        audit_path = tmp_path / "test_audit.log"
        monkeypatch.setenv("BRIDGE_AUDIT_LOG", str(audit_path))
        
        # Make a call
        payload = {"tool_name": "shell", "args": {"cmd": "echo test"}}
        client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        
        # Check audit log exists and has entries
        assert audit_path.exists()
        with open(audit_path, "r") as f:
            lines = f.readlines()
        assert len(lines) > 0


class TestRequestID:
    """Request ID tracking tests"""
    
    def test_custom_request_id(self):
        """Custom request_id should be used"""
        payload = {
            "tool_name": "shell",
            "args": {"cmd": "echo test"},
            "request_id": "custom-123"
        }
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 200
    
    def test_auto_generated_request_id(self):
        """Request ID should be auto-generated if not provided"""
        payload = {"tool_name": "shell", "args": {"cmd": "echo test"}}
        resp = client.post("/call", json=payload, headers={"x-api-key": API_KEY})
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
