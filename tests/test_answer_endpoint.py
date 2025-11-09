"""
Integration tests for /answer endpoint.

Tests complete answer generation with citations.
"""
from typing import AsyncGenerator, Any, Dict
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from unittest.mock import AsyncMock, MagicMock

from astra.api.app import create_app
from astra.services.chat_service import ChatService
from astra.services.memory_service import MemoryService
from astra.services.conversation_service import ConversationService

@pytest.fixture
async def app() -> FastAPI:
    """Create test app with mocked services"""
    app = create_app()
    
    # Create mocked services
    chat_service = MagicMock(spec=ChatService)
    memory_service = MagicMock(spec=MemoryService)
    conversation_service = MagicMock(spec=ConversationService)
    
    # Set up mock responses
    chat_service.generate_response = AsyncMock(return_value="Test response")
    memory_service.get_citations = AsyncMock(return_value=[{
        "id": "test1",
        "metadata": {
            "text_preview": "Test citation",
            "source": "test.txt",
            "nutrition": {"energy_score": 0.9}
        },
        "score": 0.95
    }])
    
    # Inject mocked services
    from astra.api.routes import answer
    answer.chat_service = chat_service
    answer.memory_service = memory_service
    
    return app

@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_generate_answer(client: AsyncClient) -> None:
    """Test generating complete answer with citations"""
    # Test request
    response = await client.post("/answer/", json={
        "query": "test question",
        "conversation_id": "test-123",
        "metadata": {"test_key": "test_value"}
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "answer" in data
    assert "citations" in data
    assert "metadata" in data
    
    # Check answer
    assert data["answer"] == "Test response"
    
    # Check citations
    assert len(data["citations"]) == 1
    citation = data["citations"][0]
    assert citation["id"] == "test1"
    assert citation["text"] == "Test citation"
    assert citation["source"] == "test.txt"
    assert citation["score"] == 0.95
    assert citation["nutrition"]["energy_score"] == 0.9
    
    # Check metadata
    assert data["metadata"]["conversation_id"] == "test-123"
    assert data["metadata"]["test_key"] == "test_value"
    assert data["metadata"]["truncated"] is False

@pytest.mark.asyncio
async def test_generate_answer_backpressure(client: AsyncClient) -> None:
    """Test backpressure handling"""
    from astra.api.routes import answer
    answer.backpressure.available_tokens = 0
    
    response = await client.post("/answer/", json={
        "query": "test question"
    })
    
    assert response.status_code == 503
    assert "Service temporarily unavailable" in response.json()["detail"]
    
    # Reset backpressure for other tests
    answer.backpressure.available_tokens = 100

@pytest.mark.asyncio
async def test_generate_answer_circuit_breaker(client: AsyncClient) -> None:
    """Test circuit breaker handling"""
    from astra.api.routes import answer
    answer.circuit_breakers.failure_count = 100
    
    response = await client.post("/answer/", json={
        "query": "test question"
    })
    
    assert response.status_code == 503
    assert "Service temporarily unavailable" in response.json()["detail"]
    
    # Reset circuit breakers for other tests
    answer.circuit_breakers.failure_count = 0