# tests_response/test_response_template.py
"""
ASTRA Response Template Tests
Created: October 31, 2025
"""
from datetime import datetime
import pytest
from astra.core.response_template import ResponseTemplate

def test_format_answer():
    """Test formatting complete answer response"""
    template = ResponseTemplate()
    
    response = "This is a test answer"
    citations = [{
        "id": "test1",
        "metadata": {
            "text_preview": "Test citation",
            "source": "test.txt",
            "nutrition": {"energy_score": 0.9}
        },
        "score": 0.95
    }]
    
    formatted = template.format_answer(
        response=response,
        citations=citations,
        conversation_id="test-123",
        metadata={"test_key": "test_value"}
    )
    
    # Check structure
    assert formatted["answer"] == response
    assert len(formatted["citations"]) == 1
    assert "metadata" in formatted
    
    # Check citation formatting
    citation = formatted["citations"][0]
    assert citation["id"] == "test1"
    assert citation["text"] == "Test citation"
    assert citation["source"] == "test.txt"
    assert citation["score"] == 0.95
    assert citation["nutrition"]["energy_score"] == 0.9
    
    # Check metadata
    assert formatted["metadata"]["conversation_id"] == "test-123"
    assert formatted["metadata"]["test_key"] == "test_value"
    assert formatted["metadata"]["truncated"] is False
    
def test_format_answer_truncated():
    """Test formatting truncated answer"""
    template = ResponseTemplate()
    
    formatted = template.format_answer(
        response="Truncated response",
        citations=[],
        truncated=True,
        truncation_reason="max_tokens_exceeded"
    )
    
    assert formatted["metadata"]["truncated"] is True
    assert formatted["metadata"]["truncation_reason"] == "max_tokens_exceeded"

def test_format_stream_chunk():
    """Test formatting stream chunks"""
    template = ResponseTemplate()
    
    # Test regular chunk
    chunk = template.format_stream_chunk(
        chunk="test chunk",
        chunk_id=1
    )
    assert chunk["chunk"] == "test chunk"
    assert chunk["chunk_id"] == 1
    assert chunk["is_final"] is False
    assert "citations" not in chunk
    
    # Test final chunk with citations
    final = template.format_stream_chunk(
        chunk="final chunk",
        chunk_id=2,
        is_final=True,
        citations=[{
            "id": "test1",
            "metadata": {"text_preview": "citation"},
            "score": 0.9
        }]
    )
    assert final["is_final"] is True
    assert len(final["citations"]) == 1
    assert final["citations"][0]["id"] == "test1"

def test_error_handling():
    """Test error handling in formatting"""
    template = ResponseTemplate()
    
    with pytest.raises(Exception):
        # Invalid citation format
        template.format_answer(
            response="test",
            citations=[{"invalid": "format"}]
        )