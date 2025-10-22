"""
Test suite for Tool Bus API routes.

Tests the functionality of tool preview, execution, and consent management.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from astra.api.app import app


@pytest.fixture
def test_client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_policy_engine():
    """Mock policy engine."""
    with patch("astra.security.policy_engine.get_policy_engine") as mock:
        policy = MagicMock()
        policy.check_tool_execution.return_value = MagicMock(
            allowed=True,
            requires_consent=False,
            impact_assessment="LOW"
        )
        mock.return_value = policy
        yield policy


@pytest.fixture
def mock_tool_registry():
    """Mock tool registry."""
    with patch("astra.core.tool_bus.get_registry") as mock:
        registry = MagicMock()
        registry.tools = {"test_tool": MagicMock()}
        mock.return_value = registry
        yield registry


def test_preview_tool_success(test_client, mock_policy_engine, mock_tool_registry):
    """Test successful tool preview."""
    response = test_client.post("/v1/tools/preview", json={
        "tool_name": "test_tool",
        "args": {"param": "value"}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] == True
    assert data["result"]["can_execute"] == True
    assert data["result"]["requires_consent"] == False


def test_preview_nonexistent_tool(test_client, mock_policy_engine, mock_tool_registry):
    """Test preview of nonexistent tool."""
    response = test_client.post("/v1/tools/preview", json={
        "tool_name": "nonexistent_tool",
        "args": {}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] == False
    assert "Tool not found" in data["error"]


def test_execute_tool_without_token(test_client):
    """Test tool execution without token."""
    response = test_client.post("/v1/tools/execute", json={
        "tool_name": "test_tool",
        "args": {}
    })
    
    assert response.status_code == 422  # Validation error - missing token


@pytest.mark.asyncio
async def test_consent_flow(test_client, mock_policy_engine):
    """Test complete consent request flow."""
    # Configure mock to require consent
    mock_policy_engine.check_tool_execution.return_value = MagicMock(
        allowed=True,
        requires_consent=True,
        impact_assessment="HIGH"
    )
    
    # Create consent request
    response = test_client.post("/v1/consent/request", json={
        "tool_name": "risky_tool",
        "args": {"param": "value"},
        "request_id": "test-request"
    })
    
    assert response.status_code == 200
    assert response.json()["ok"] == True

    # Check status
    mock_policy_engine.get_consent_status.return_value = MagicMock(
        status="pending",
        reason=None
    )
    
    response = test_client.get("/v1/consent/status/test-request")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Approve consent
    mock_policy_engine.get_consent_request.return_value = MagicMock(
        tool_name="risky_tool",
        args={"param": "value"}
    )
    
    response = test_client.post(
        "/v1/consent/approve/test-request",
        params={"reason": "Approved for testing"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] == True
    assert "token" in data  # Should get execution token