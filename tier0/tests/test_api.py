"""Tests for ASTRA Tier-0 API

Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.core.security.capabilities import Capability, CapabilityGuard


client = TestClient(app)


class TestHealth:
    """Health check tests"""
    
    def test_health_returns_ok(self):
        """Health endpoint returns OK status"""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "voice_running" in data
        assert "capabilities_enabled" in data
    
    def test_health_capabilities(self):
        """Health includes all capability flags"""
        resp = client.get("/health")
        data = resp.json()
        expected_caps = {
            "focus", "launch", "tile", "type", 
            "hotkey", "screenshot", "close"
        }
        assert set(data["capabilities_enabled"].keys()) == expected_caps


class TestDesktopControl:
    """Desktop control endpoint tests"""
    
    @patch("src.api._desktop.focus")
    def test_focus_success(self, mock_focus):
        """Focus window succeeds"""
        mock_focus.return_value = "Focused window"
        
        resp = client.post("/desktop/focus", json={"title_contains": "notepad"})
        assert resp.status_code == 200
        assert resp.json()["result"] == "Focused window"
        mock_focus.assert_called_once_with("notepad")
    
    @patch("src.api._desktop.focus")
    def test_focus_error(self, mock_focus):
        """Focus window not found"""
        mock_focus.side_effect = RuntimeError("Window not found")
        
        resp = client.post("/desktop/focus", json={"title_contains": "nonexistent"})
        assert resp.status_code == 400
    
    @patch("src.api._desktop.launch")
    def test_launch_success(self, mock_launch):
        """Launch application succeeds"""
        mock_launch.return_value = "Launched"
        
        resp = client.post("/desktop/launch", json={
            "exe_path": "C:\\Windows\\notepad.exe",
            "args": ""
        })
        assert resp.status_code == 200
        mock_launch.assert_called_once()
    
    @patch("src.api._desktop.launch")
    def test_launch_permission_denied(self, mock_launch):
        """Launch outside safe directory denied"""
        mock_launch.side_effect = PermissionError("Outside SAFE_APPS_DIR")
        
        resp = client.post("/desktop/launch", json={
            "exe_path": "/tmp/malware.exe"
        })
        assert resp.status_code == 400
    
    @patch("src.api._desktop.tile")
    def test_tile_success(self, mock_tile):
        """Tile window succeeds"""
        mock_tile.return_value = "Tiled left"
        
        resp = client.post("/desktop/tile", json={"side": "left"})
        assert resp.status_code == 200
        mock_tile.assert_called_once_with("left")
    
    @patch("src.api._desktop.type_text")
    def test_type_success(self, mock_type):
        """Type text succeeds"""
        mock_type.return_value = "Typed"
        
        resp = client.post("/desktop/type", json={"text": "hello"})
        assert resp.status_code == 200
        mock_type.assert_called_once_with("hello")
    
    @patch("src.api._desktop.hotkey")
    def test_hotkey_success(self, mock_hotkey):
        """Send hotkey succeeds"""
        mock_hotkey.return_value = "Hotkey sent"
        
        resp = client.post("/desktop/hotkey", json={"keys": ["alt", "tab"]})
        assert resp.status_code == 200
        mock_hotkey.assert_called_once_with("alt", "tab")
    
    @patch("src.api._desktop.screenshot")
    def test_screenshot_success(self, mock_screenshot):
        """Screenshot succeeds"""
        mock_screenshot.return_value = "/tmp/shot_123.png"
        
        resp = client.get("/desktop/screenshot")
        assert resp.status_code == 200
        assert "path" in resp.json()
    
    @patch("src.api._desktop.close")
    def test_close_success(self, mock_close):
        """Close window succeeds"""
        mock_close.return_value = "Closed"
        
        resp = client.post("/desktop/close", json={"title_contains": "notepad"})
        assert resp.status_code == 200


class TestVoiceControl:
    """Voice control endpoint tests"""
    
    def test_voice_status_not_initialized(self):
        """Voice status when not initialized"""
        resp = client.get("/voice/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] == False or data["running"] == True
        assert "model_size" in data
        assert "wake_words" in data
    
    @patch("src.api.WakeService")
    def test_voice_start_success(self, mock_wake_service_class):
        """Start voice service succeeds"""
        mock_service = MagicMock()
        mock_service.running = False
        mock_wake_service_class.return_value = mock_service
        
        resp = client.post("/voice/start")
        assert resp.status_code == 200
        assert "status" in resp.json()
    
    def test_voice_stop_not_running(self):
        """Stop voice when not running"""
        resp = client.post("/voice/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["not_running", "stopped"]


class TestCapabilityGuard:
    """Capability guard integration tests"""
    
    def test_guard_initialized(self):
        """CapabilityGuard is initialized"""
        from src.api import _guard
        assert isinstance(_guard, CapabilityGuard)
        
        # At least focus should be allowed by default
        assert _guard.is_allowed(Capability.FOCUS)


class TestErrorHandling:
    """Error handling tests"""
    
    def test_missing_required_field(self):
        """Missing required field returns 422"""
        resp = client.post("/desktop/focus", json={})
        assert resp.status_code == 422
    
    def test_invalid_json(self):
        """Invalid JSON returns error"""
        resp = client.post(
            "/desktop/focus",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        assert resp.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
