"""
Pytest Smoke Tests — ASTRA Live System Validation
Run: pytest tests/smoke/test_live.py -v
Status: ✅ if all pass
"""

import os
import requests
import pytest
from typing import Optional

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SIGIL_URL = os.getenv("SIGIL_URL", "http://localhost:7701/issue")
TIMEOUT = 5


def get_token() -> str:
    """Mint or retrieve auth token."""
    # Check if token provided as env var
    token = os.environ.get("TOKEN")
    if token:
        return token
    
    # Request from SigilGate
    try:
        resp = requests.post(
            SIGIL_URL,
            json={
                "identity": "saint",
                "scopes": ["*"],
                "ttl": 3600
            },
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()["token"]
    except Exception as e:
        pytest.skip(f"SigilGate unavailable: {e}")


class TestHealthAndReady:
    """Verify system health and readiness."""
    
    def test_master_health(self):
        """GET /v1/system/health returns 200 + status in (ok, healthy, degraded)."""
        resp = requests.get(
            f"{BASE_URL}/v1/system/health",
            timeout=TIMEOUT
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        assert "status" in data, "Missing 'status' field"
        assert data["status"] in ("ok", "healthy", "degraded"), \
            f"Invalid status: {data['status']}"
    
    def test_has_services_info(self):
        """Health response includes service statuses."""
        resp = requests.get(f"{BASE_URL}/v1/system/health", timeout=TIMEOUT)
        data = resp.json()
        
        # At least one of these fields should exist
        fields = ["services", "timestamp", "version"]
        assert any(f in data for f in fields), \
            f"Missing any of {fields}"


class TestAuthentication:
    """Verify auth pipeline."""
    
    def test_chat_requires_auth(self):
        """POST /v1/chat without Authorization returns 401."""
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
            timeout=TIMEOUT
        )
        assert resp.status_code == 401, \
            f"Expected 401 Unauthorized, got {resp.status_code}"
    
    def test_valid_token_accepted(self):
        """POST /v1/chat with valid token returns 200 or other (not 401)."""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            headers=headers,
            json={"messages": [{"role": "user", "content": "ping"}]},
            timeout=10
        )
        
        # Should not be 401 (may be 200, 503 if model down, etc.)
        assert resp.status_code != 401, \
            f"Valid token rejected: {resp.status_code}"


class TestChatRoundtrip:
    """Verify chat inference pipeline."""
    
    def test_chat_roundtrip_complete(self):
        """POST /v1/chat returns response + usage metadata."""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": "ASTRA, confirm you are online with one line."
                }
            ]
        }
        
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            headers=headers,
            json=body,
            timeout=10
        )
        
        # If model is down (503), we still pass (infra is OK)
        if resp.status_code == 503:
            pytest.skip("Model endpoint unavailable (expected in test env)")
        
        assert resp.status_code == 200, \
            f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Check response structure
        assert "choices" in data, "Missing 'choices' in response"
        assert len(data["choices"]) > 0, "Empty choices array"
        
        # Check message in first choice
        choice = data["choices"][0]
        assert "message" in choice, "Missing 'message' in choice"
        assert "content" in choice["message"], "Missing 'content' in message"
        
        # Check usage tracking
        assert "usage" in data, "Missing 'usage' (cost tracking)"
        assert "prompt_tokens" in data["usage"], "Missing prompt_tokens"
        assert "completion_tokens" in data["usage"], "Missing completion_tokens"
    
    def test_chat_with_multiple_messages(self):
        """POST /v1/chat accepts multi-turn conversation."""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        body = {
            "messages": [
                {"role": "user", "content": "What is your name?"},
                {"role": "assistant", "content": "I am ASTRA."},
                {"role": "user", "content": "Good. Confirm online."}
            ]
        }
        
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            headers=headers,
            json=body,
            timeout=10
        )
        
        if resp.status_code == 503:
            pytest.skip("Model endpoint unavailable")
        
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert len(data["choices"][0]["message"]["content"]) > 0


class TestDiagnosticsEndpoint:
    """Verify diagnostics endpoint (if implemented)."""
    
    def test_diag_endpoint_exists(self):
        """GET /v1/system/diag returns system metadata."""
        resp = requests.get(
            f"{BASE_URL}/v1/system/diag",
            timeout=TIMEOUT
        )
        
        # Endpoint may not exist (404 is OK for now)
        if resp.status_code == 404:
            pytest.skip("Diag endpoint not yet implemented")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Should have version, leader info, or similar
        assert any(k in data for k in ["version", "leader", "queues"]), \
            "Diag missing expected fields"


class TestErrorHandling:
    """Verify error responses."""
    
    def test_malformed_json(self):
        """POST /v1/chat with malformed JSON returns 4xx."""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            headers=headers,
            data="{bad json}",
            timeout=TIMEOUT
        )
        
        assert 400 <= resp.status_code < 500, \
            f"Expected 4xx, got {resp.status_code}"
    
    def test_missing_messages_field(self):
        """POST /v1/chat without 'messages' returns 4xx."""
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        body = {"prompt": "test"}  # Wrong field name
        
        resp = requests.post(
            f"{BASE_URL}/v1/chat",
            headers=headers,
            json=body,
            timeout=TIMEOUT
        )
        
        assert 400 <= resp.status_code < 500, \
            f"Expected 4xx, got {resp.status_code}"


class TestPerformance:
    """Verify performance characteristics."""
    
    def test_chat_latency(self):
        """Chat request completes within timeout (indicates responsiveness)."""
        import time
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        body = {"messages": [{"role": "user", "content": "short"}]}
        
        start = time.time()
        try:
            resp = requests.post(
                f"{BASE_URL}/v1/chat",
                headers=headers,
                json=body,
                timeout=10
            )
            elapsed = time.time() - start
            
            if resp.status_code == 503:
                pytest.skip("Model unavailable")
            
            # Expect < 15 seconds (generous for model warmup)
            assert elapsed < 15, f"Chat took {elapsed:.1f}s (timeout)"
            
        except requests.Timeout:
            pytest.fail("Chat request timed out (>10s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
