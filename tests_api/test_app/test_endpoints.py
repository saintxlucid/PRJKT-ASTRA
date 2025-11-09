"""
Integration tests for ASTRA FastAPI application endpoints
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import json
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "circuit_breaker" in data
    assert "backpressure" in data

@pytest.mark.asyncio
async def test_answer_endpoint(client):
    """Test answer endpoint"""
    with patch("astra.app.answer_api") as mock:
        instance = mock.return_value
        instance.get_answer = AsyncMock(return_value=(
            "Test answer",
            [{"text": "Citation 1", "score": 0.9}],
            {"tokens": 50, "time": 0.5}
        ))
        
        response = client.post(
            "/answer",
            params={"query": "test question", "conversation_id": "test-123"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "answer" in data
        assert "citations" in data
        assert "metadata" in data
        assert "conversation_id" in data
        
        # Validate content
        assert data["answer"] == "Test answer"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["text"] == "Citation 1"
        assert data["conversation_id"] == "test-123"
        assert data["metadata"]["tokens"] == 50

@pytest.mark.asyncio
async def test_stream_endpoint(client):
    """Test streaming endpoint"""
    with patch("astra.app.answer_api") as mock:
        instance = mock.return_value
        async def stream_generator():
            yield "Chunk 1", False, [], {}
            yield "Chunk 2", True, [{"text": "Citation", "score": 0.9}], {"tokens": 20}
        instance.stream_answer = AsyncMock(return_value=stream_generator())
        
        with client.stream(
            "POST",
            "/answer/stream",
            params={"query": "test stream", "conversation_id": "test-456"}
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            
            # Process SSE stream
            chunks = []
            for line in response.iter_lines():
                if line.startswith(b"data:"):
                    data = json.loads(line.split(b"data: ")[1])
                    chunks.append(data)
            
            # Validate chunks
            assert len(chunks) == 2
            assert chunks[0]["chunk"] == "Chunk 1"
            assert not chunks[0]["is_final"]
            assert chunks[1]["chunk"] == "Chunk 2"
            assert chunks[1]["is_final"]
            assert len(chunks[1]["citations"]) == 1

@pytest.mark.asyncio
async def test_circuit_breaker(client):
    """Test circuit breaker protection"""
    with patch("astra.core.circuit_breakers.CircuitBreaker.__call__") as mock_cb:
        mock_cb.side_effect = HTTPException(503, "Service temporarily unavailable")
        response = client.post(
            "/answer",
            params={"query": "test"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Service temporarily unavailable"

@pytest.mark.asyncio
async def test_backpressure(client):
    """Test backpressure protection"""
    with patch("astra.core.backpressure.Backpressure.acquire") as mock_bp:
        mock_bp.side_effect = HTTPException(429, "Server is at capacity")
        response = client.post(
            "/answer",
            params={"query": "test"}
        )
        assert response.status_code == 429
        assert response.json()["detail"] == "Server is at capacity"

@pytest.mark.asyncio
async def test_error_handling(client):
    """Test error handling"""
    with patch("astra.app.answer_api") as mock:
        instance = mock.return_value
        instance.get_answer = AsyncMock(side_effect=Exception("Test error"))
        response = client.post(
            "/answer",
            params={"query": "test"}
        )
        assert response.status_code == 500
        assert response.json()["detail"] == "Error generating answer"