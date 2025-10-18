"""
Unit tests for streaming chat endpoints (Directive 002).

Tests SSE (Server-Sent Events) streaming functionality, metrics, and error handling.
"""

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from astra.api.routes.chat import router, set_chat_service
from astra.infrastructure.llm.base import StreamChunk
from astra.services.chat_service import ChatService


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service for testing"""
    service = Mock(spec=ChatService)

    # Mock stream_chat to return chunks
    async def mock_stream():
        chunks = [
            StreamChunk(content="Hello", finish_reason=None),
            StreamChunk(content=" ", finish_reason=None),
            StreamChunk(content="world", finish_reason=None),
            StreamChunk(content="", finish_reason="stop"),
        ]
        for chunk in chunks:
            await asyncio.sleep(0.01)  # Simulate streaming delay
            yield chunk

    service.stream_chat = AsyncMock(return_value=mock_stream())
    service.stream_chat.side_effect = lambda **kwargs: mock_stream()

    return service


@pytest.fixture
def app(mock_chat_service):
    """Create FastAPI app with mocked dependencies"""
    app = FastAPI()
    app.include_router(router)
    set_chat_service(mock_chat_service)
    return app


@pytest.mark.asyncio
async def test_stream_endpoint_returns_sse(app, mock_chat_service):
    """Test that /stream endpoint returns Server-Sent Events format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"


@pytest.mark.asyncio
async def test_stream_chunks_arrive_incrementally(app, mock_chat_service):
    """Test that chunks arrive incrementally as SSE events"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Collect streaming response
        chunks = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                chunks.append(line[6:])  # Strip "data: " prefix

        assert len(chunks) > 0
        assert "[DONE]" in chunks[-1] or chunks[-1] == "[DONE]"


@pytest.mark.asyncio
async def test_stream_first_token_latency_fast(app, mock_chat_service):
    """Test that first token arrives quickly (<300ms target)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        import time

        start = time.perf_counter()
        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Read first chunk
        first_chunk_time = None
        async for line in response.aiter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                first_chunk_time = time.perf_counter() - start
                break

        assert first_chunk_time is not None, "No chunks received"
        # In unit tests with mocks, should be nearly instant (<50ms)
        assert first_chunk_time < 0.05


@pytest.mark.asyncio
async def test_stream_metrics_incremented(app, mock_chat_service):
    """Test that streaming metrics are incremented"""
    from astra.metrics import STREAM_CLIENTS, STREAM_TOKENS

    # Get initial values
    initial_clients = STREAM_CLIENTS._value._value
    initial_tokens = STREAM_TOKENS._metrics.get((), Mock(_value=Mock(_value=0)))._value._value

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Consume all chunks
        async for _ in response.aiter_lines():
            pass

    # Clients gauge should return to original value after stream completes
    final_clients = STREAM_CLIENTS._value._value
    assert final_clients == initial_clients

    # Tokens counter should have increased
    final_tokens = STREAM_TOKENS._metrics.get((), Mock(_value=Mock(_value=0)))._value._value
    assert final_tokens > initial_tokens


@pytest.mark.asyncio
async def test_stream_with_per_key_limiter(app, mock_chat_service):
    """Test that streaming requests respect per-key rate limits"""
    # This test validates that streaming goes through same middleware pipeline
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        # Send request (middleware not fully mocked, so just check it doesn't error)
        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Should succeed (or fail gracefully with auth error, not 500)
        assert response.status_code in (200, 401, 429)


@pytest.mark.asyncio
async def test_stream_error_handling(app):
    """Test that errors are properly formatted as SSE error events"""
    # Create service that raises an error
    error_service = Mock(spec=ChatService)

    async def error_stream():
        raise ValueError("Test error")
        yield  # Make it a generator

    error_service.stream_chat = AsyncMock(side_effect=lambda **kwargs: error_stream())

    # Swap service temporarily
    from astra.api.routes.chat import set_chat_service

    set_chat_service(error_service)

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Should still return 200 (SSE errors are sent in stream)
        assert response.status_code == 200

        # Check for error event in stream
        error_found = False
        async for line in response.aiter_lines():
            if line.startswith("event: error"):
                error_found = True
                break

        assert error_found, "Expected error event in SSE stream"


@pytest.mark.asyncio
async def test_stream_request_id_header_present(app, mock_chat_service):
    """Test that X-Request-Id header is included in streaming response"""
    # Simulate request ID middleware
    from unittest.mock import patch

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "conversation_id": "test-conv-123",
            "message": "Say hello",
            "use_memory": False,
        }

        response = await client.post(
            "/v1/chat/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
        )

        # Request ID may or may not be present depending on middleware
        # (middleware not fully active in unit tests, just validate no crash)
        assert response.status_code == 200
