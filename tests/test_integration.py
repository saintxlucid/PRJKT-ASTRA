"""
Integration tests for ASTRA server core functionality
"""
import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, AsyncGenerator
from datetime import datetime

# Test configuration
TEST_HOST = "http://localhost:8001"
TEST_TIMEOUT = 30
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

@pytest.fixture
async def http_client():
    """Create aiohttp client session"""
    async with aiohttp.ClientSession() as session:
        yield session

async def wait_for_server(client: aiohttp.ClientSession, timeout: int = 30) -> bool:
    """Wait for server to become ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with client.get(f"{TEST_HOST}/live") as response:
                if response.status == 200:
                    return True
        except aiohttp.ClientError:
            pass
        await asyncio.sleep(1)
    return False

@pytest.mark.asyncio
async def test_readiness_gates(http_client):
    """Test readiness gate endpoints"""
    # Wait for server
    assert await wait_for_server(http_client), "Server failed to start"
    
    # Test /live endpoint
    async with http_client.get(f"{TEST_HOST}/live") as response:
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "live"
        assert "timestamp" in data
        
    # Test /ready endpoint
    async with http_client.get(f"{TEST_HOST}/ready") as response:
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "ready"
        assert "draining" in data
        assert data["draining"] is False
        
    # Test /health endpoint
    async with http_client.get(f"{TEST_HOST}/health") as response:
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert all(data["components"].values())

    # Test drain sequence
    async with http_client.post(f"{TEST_HOST}/drain") as response:
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "draining"
        
    # Verify ready endpoint reflects drain state
    async with http_client.get(f"{TEST_HOST}/ready") as response:
        assert response.status == 503  # Service Unavailable during drain
        data = await response.json()
        assert data["draining"] is True

@pytest.mark.asyncio
async def test_answer_endpoint(http_client):
    """Test /answer endpoint with backpressure and circuit breakers"""
    # Basic answer request
    async with http_client.post(
        f"{TEST_HOST}/answer",
        json={"query": "Test question"},
        headers=REQUEST_HEADERS
    ) as response:
        assert response.status == 200
        data = await response.json()
        assert "answer" in data
        assert "citations" in data
        assert "metadata" in data
        assert len(data["citations"]) > 0
        assert data["metadata"]["model"] == "test-model"
        assert data["metadata"]["version"] == "0.1.0"
        
    # Test backpressure with concurrent requests
    async def make_request():
        async with http_client.post(
            f"{TEST_HOST}/answer",
            json={"query": "Load test"},
            headers=REQUEST_HEADERS
        ) as response:
            return response.status
            
    # Create many concurrent requests
    tasks = [make_request() for _ in range(150)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify some requests were throttled
    success_count = len([r for r in results if r == 200])
    throttled_count = len([r for r in results if r in (429, 503)])
    assert throttled_count > 0, "No requests were throttled under load"
    
    # Test metrics endpoint
    async with http_client.get(f"{TEST_HOST}/metrics") as response:
        assert response.status == 200
        data = await response.json()
        assert "backpressure" in data
        assert "circuit_breakers" in data
        assert data["backpressure"]["queue_depth"] >= 0
        assert "memory" in data["circuit_breakers"]
        assert "inference" in data["circuit_breakers"]

@pytest.mark.asyncio
async def test_streaming_endpoint(http_client):
    """Test /answer/stream endpoint"""
    # Test streaming response
    async with http_client.post(
        f"{TEST_HOST}/answer/stream",
        json={"query": "Test streaming"},
        headers={"Accept": "text/event-stream", "Content-Type": "application/json"}
    ) as response:
        assert response.status == 200
        chunks = []
        
        # Read SSE stream
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                chunk = json.loads(line[6:])  # Skip 'data: ' prefix
                chunks.append(chunk)
                
        # Verify stream content
        assert len(chunks) > 0
        assert all("chunk" in c for c in chunks)
        assert any(c.get("is_final", False) for c in chunks)
        
        # Check final chunk has citations
        final_chunk = next(c for c in chunks if c.get("is_final", False))
        assert "citations" in final_chunk
        assert len(final_chunk["citations"]) > 0

@pytest.mark.asyncio
async def test_graceful_shutdown(http_client):
    """Test graceful shutdown sequence"""
    # Start with health check
    async with http_client.get(f"{TEST_HOST}/health") as response:
        assert response.status == 200
        
    # Initiate drain
    async with http_client.post(f"{TEST_HOST}/drain") as response:
        assert response.status == 200
        start_time = time.time()
        
    # Monitor readiness during drain
    while time.time() - start_time < 10:  # Check drain completes within 10s
        async with http_client.get(f"{TEST_HOST}/ready") as response:
            data = await response.json()
            if response.status == 503 and data["draining"]:
                break
        await asyncio.sleep(0.1)
    
    assert time.time() - start_time < 10, "Drain sequence took too long"

@pytest.mark.asyncio
async def test_error_handling(http_client):
    """Test error handling and circuit breakers"""
    # Invalid request
    async with http_client.post(
        f"{TEST_HOST}/answer",
        json={},  # Missing query field
        headers=REQUEST_HEADERS
    ) as response:
        assert response.status == 422  # Validation error
        
    # Trigger circuit breaker
    errors = 0
    for _ in range(10):
        async with http_client.post(
            f"{TEST_HOST}/answer",
            json={"query": "error"},  # This should trigger simulated errors
            headers=REQUEST_HEADERS
        ) as response:
            if response.status != 200:
                errors += 1
                
    assert errors > 0, "Circuit breaker never triggered"
    
    # Verify circuit breaker state
    async with http_client.get(f"{TEST_HOST}/metrics") as response:
        data = await response.json()
        assert any(
            breaker["state"] == "open" 
            for breaker in data["circuit_breakers"].values()
        )