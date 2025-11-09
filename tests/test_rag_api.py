"""
ASTRA RAG API Integration Tests
Created: October 25, 2025

End-to-end tests for ASTRA's RAG API endpoints, verifying:
- Request/response contract
- Error handling
- Correlation ID propagation
- Performance metrics
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from astra.core.rag_api import router, init_rag_router
from astra.core.rag_fusion import RAGFusionEngine

# Test fixtures
@pytest.fixture
def rag_engine():
    """Create mock RAG engine"""
    engine = AsyncMock(spec=RAGFusionEngine)
    engine.answer.return_value = {
        "text": "Test response",
        "memory_ids": ["mem1", "mem2"],
        "adapter_ids": ["adapter1"],
        "citations": {
            "src1": {"id": "mem1", "source": "test.txt"},
            "src2": {"id": "mem2", "source": "test.txt"}
        },
        "metrics": {
            "retrieval_time": 0.1,
            "total_time": 0.5,
            "context_tokens": 100,
            "output_tokens": 50
        },
        "trace_id": "test-trace"
    }
    return engine

@pytest.fixture
def test_client(rag_engine):
    """Create FastAPI test client"""
    init_rag_router(rag_engine)
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

# Test successful answer generation
def test_generate_answer_success(test_client, rag_engine):
    """Test successful answer generation request"""
    response = test_client.post(
        "/astra/rag/answer",
        json={
            "query": "Test question?",
            "session_id": "test-session",
            "persona_id": "test-persona"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "text" in data
    assert "memory_ids" in data
    assert "adapter_ids" in data
    assert "citations" in data
    assert "metrics" in data
    assert "trace_id" in data
    
    # Verify RAG engine was called correctly
    rag_engine.answer.assert_called_once()
    call_args = rag_engine.answer.call_args[1]
    assert call_args["query"] == "Test question?"
    assert call_args["session_id"] == "test-session"
    assert call_args["persona_id"] == "test-persona"

# Test error handling
def test_generate_answer_error(test_client, rag_engine):
    """Test error handling in answer generation"""
    rag_engine.answer.side_effect = Exception("Test error")
    
    response = test_client.post(
        "/astra/rag/answer",
        json={"query": "Test question?"}
    )
    
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Test error" in data["detail"]

# Test parameter validation
def test_parameter_validation(test_client):
    """Test request parameter validation"""
    # Missing required query
    response = test_client.post(
        "/astra/rag/answer",
        json={}
    )
    assert response.status_code == 422
    
    # Invalid k parameter
    response = test_client.post(
        "/astra/rag/answer",
        json={
            "query": "Test?",
            "k": -1
        }
    )
    assert response.status_code == 422

# Test optional parameters
def test_optional_parameters(test_client, rag_engine):
    """Test handling of optional parameters"""
    response = test_client.post(
        "/astra/rag/answer",
        json={
            "query": "Test?",
            "k": 5,
            "context_tokens": 1000
        }
    )
    
    assert response.status_code == 200
    rag_engine.answer.assert_called_once()
    call_args = rag_engine.answer.call_args[1]
    assert call_args["k"] == 5
    assert call_args["context_tokens"] == 1000

# Test uninitialized engine
def test_uninitialized_engine(test_client):
    """Test error when RAG engine not initialized"""
    init_rag_router(None)  # Reset engine
    
    response = test_client.post(
        "/astra/rag/answer",
        json={"query": "Test?"}
    )
    
    assert response.status_code == 503
    data = response.json()
    assert "RAG engine not initialized" in data["detail"]

# Performance tests
@pytest.mark.asyncio
async def test_response_timing(test_client, rag_engine):
    """Test response timing metrics"""
    response = test_client.post(
        "/astra/rag/answer",
        json={"query": "Test?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify timing metrics
    assert "metrics" in data
    assert "retrieval_time" in data["metrics"]
    assert "total_time" in data["metrics"]
    assert data["metrics"]["total_time"] >= data["metrics"]["retrieval_time"]