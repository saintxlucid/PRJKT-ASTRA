"""
Integration tests for plugin sandbox functionality.
Tests sandbox initialization, permissions, resource limits, and cleanup.
"""
import asyncio
import json
import os
from pathlib import Path
import pytest
import time

from astra.core.plugins.sandbox import PluginSandbox, PluginAction
from astra.core.plugins.exceptions import (
    PluginLoadError,
    PluginPermissionError,
    PluginRuntimeError,
    PluginValidationError
)

# Test plugin manifest template
VALID_MANIFEST = {
    "id": "test-plugin",
    "version": "1.0.0",
    "name": "Test Plugin",
    "description": "Plugin for testing sandbox",
    "capabilities": {
        "minAbiVersion": "1.0",
        "maxAbiVersion": "1.0",
        "actions": [
            {
                "name": "test_action",
                "description": "Test action",
                "permissions": ["memory.read"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"}
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            }
        ],
        "storage": {
            "persistent": True,
            "quota": 1024
        }
    }
}

# Test plugin implementation template
TEST_PLUGIN = """
import asyncio

class Plugin:
    async def initialize(self, context):
        self.context = context
        
    async def test_action(self, params):
        value = params.get("value", "")
        return {"result": f"Processed: {value}"}
        
    async def cleanup(self):
        pass
"""

@pytest.fixture
async def plugin_dir(tmp_path):
    """Create a temporary plugin directory with manifest"""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()
    
    # Write manifest
    manifest_path = plugin_dir / "manifest.json"
    manifest_path.write_text(json.dumps(VALID_MANIFEST))
    
    # Write plugin implementation
    plugin_path = plugin_dir / "plugin.py"
    plugin_path.write_text(TEST_PLUGIN)
    
    return plugin_dir

@pytest.fixture
async def sandbox(plugin_dir):
    """Create plugin sandbox instance"""
    sandbox = PluginSandbox(plugin_dir)
    await sandbox.load()
    yield sandbox
    await sandbox.unload()

async def test_plugin_load_unload(plugin_dir):
    """Test basic plugin loading and unloading"""
    sandbox = PluginSandbox(plugin_dir)
    
    # Test loading
    await sandbox.load()
    assert sandbox.instance is not None
    assert sandbox.context is not None
    assert sandbox.metadata.id == "test-plugin"
    
    # Test unloading
    await sandbox.unload()
    assert sandbox.instance is None
    assert sandbox.context is None
    
async def test_invalid_manifest(tmp_path):
    """Test loading plugin with invalid manifest"""
    plugin_dir = tmp_path / "invalid-plugin"
    plugin_dir.mkdir()
    
    # Write invalid manifest
    manifest_path = plugin_dir / "manifest.json"
    manifest_path.write_text("{}")
    
    with pytest.raises(PluginValidationError):
        sandbox = PluginSandbox(plugin_dir)
        
async def test_missing_plugin_file(plugin_dir):
    """Test loading plugin with missing implementation file"""
    os.remove(plugin_dir / "plugin.py")
    
    with pytest.raises(PluginLoadError):
        sandbox = PluginSandbox(plugin_dir)
        await sandbox.load()
        
async def test_action_permissions(sandbox):
    """Test action permission checks"""
    # Action requires memory.read permission
    with pytest.raises(PluginPermissionError):
        await sandbox.call_action("test_action", {"value": "test"})
        
    # Grant permission and retry
    sandbox.context.grant_permission("memory.read")
    result = await sandbox.call_action("test_action", {"value": "test"})
    assert result["result"] == "Processed: test"
    
async def test_resource_limits(plugin_dir):
    """Test resource limit enforcement"""
    # Modify plugin to exceed memory limit
    bad_plugin = TEST_PLUGIN + """
        async def memory_hog(self, params):
            x = [0] * (1024 * 1024 * 1024)  # 1GB array
            return {"result": "success"}
    """
    
    # Add memory intensive action
    manifest = VALID_MANIFEST.copy()
    manifest["capabilities"]["actions"].append({
        "name": "memory_hog",
        "description": "Memory intensive action",
        "permissions": [],
        "parameters": {"type": "object"},
        "returnType": {"type": "object"}
    })
    
    # Write modified plugin
    (plugin_dir / "plugin.py").write_text(bad_plugin)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    
    # Test memory limit
    sandbox = PluginSandbox(plugin_dir)
    await sandbox.load()
    
    with pytest.raises(PluginRuntimeError) as exc:
        await sandbox.call_action("memory_hog", {})
    assert "memory limit" in str(exc.value)
    
async def test_action_timeout(plugin_dir):
    """Test action timeout enforcement"""
    # Modify plugin to add slow action
    slow_plugin = TEST_PLUGIN + """
        async def slow_action(self, params):
            await asyncio.sleep(10)
            return {"result": "success"}
    """
    
    # Add slow action to manifest
    manifest = VALID_MANIFEST.copy()
    manifest["capabilities"]["actions"].append({
        "name": "slow_action",
        "description": "Slow action",
        "permissions": [],
        "parameters": {"type": "object"},
        "returnType": {"type": "object"}
    })
    
    # Write modified plugin
    (plugin_dir / "plugin.py").write_text(slow_plugin)
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest))
    
    # Test timeout
    sandbox = PluginSandbox(plugin_dir)
    await sandbox.load()
    
    with pytest.raises(asyncio.TimeoutError):
        await sandbox.call_action("slow_action", {})
        
async def test_audit_logging(sandbox, tmp_path):
    """Test audit logging functionality"""
    # Set up audit directory
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    sandbox.audit_logger.log_dir = audit_dir
    
    # Grant required permission
    sandbox.context.grant_permission("memory.read")
    
    # Execute action
    await sandbox.call_action("test_action", {"value": "audit_test"})
    
    # Verify audit log
    log_path = audit_dir / "test-plugin.jsonl"
    assert log_path.exists()
    
    log_entry = json.loads(log_path.read_text())
    assert log_entry["plugin_id"] == "test-plugin"
    assert log_entry["action"] == "test_action"
    assert log_entry["success"] is True
    assert "duration_ms" in log_entry["result"]["_metrics"]
    
async def test_cleanup_on_error(plugin_dir):
    """Test cleanup when plugin errors during load"""
    # Modify plugin to error during initialization
    bad_init = TEST_PLUGIN.replace(
        "async def initialize(self, context):",
        "async def initialize(self, context):\n        raise RuntimeError('Init failed')"
    )
    
    (plugin_dir / "plugin.py").write_text(bad_init)
    
    sandbox = PluginSandbox(plugin_dir)
    with pytest.raises(PluginLoadError):
        await sandbox.load()
        
    # Verify cleanup occurred
    assert sandbox.instance is None
    assert sandbox.context is None
    assert sandbox.module is None
    
async def test_concurrent_actions(sandbox):
    """Test concurrent action execution"""
    sandbox.context.grant_permission("memory.read")
    
    # Execute multiple actions concurrently
    actions = [
        sandbox.call_action("test_action", {"value": f"test_{i}"})
        for i in range(5)
    ]
    
    results = await asyncio.gather(*actions)
    assert len(results) == 5
    assert all("Processed: test_" in r["result"] for r in results)