"""
ASTRA Answer API Tests
Created: October 31, 2025
"""
import pytest
from fastapi.testclient import TestClient
from src.astra.core.app import app
from src.astra.core.answer_api import AnswerRequest

def test_answer_endpoint_success():
    """Test successful answer generation"""
    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={
                "query": "test query",
                "conversation_id": "test-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "metadata" in data

def test_answer_backpressure():
    """Test backpressure rejection"""
    with TestClient(app) as client:
        # Fill up queue
        for _ in range(101):  # Max depth + 1
            response = client.post(
                "/answer",
                json={"query": "test"}
            )
            
        assert response.status_code == 429
        data = response.json()
        assert "retry_after" in data["detail"]

def test_answer_circuit_breaker():
    """Test circuit breaker activation"""
    with TestClient(app) as client:
        # Force memory failures
        for _ in range(6):  # Threshold + 1
            response = client.post(
                "/answer",
                json={"query": "force_memory_fail"}
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "error_id" in data["detail"]
        assert "request_id" in data["detail"]