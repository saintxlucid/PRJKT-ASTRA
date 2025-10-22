"""Test suite for Memory Bridge integration."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import json
import tempfile

from astra.bridge.memory_bridge import (
    MemoryBridge, MemoryBridgeService, MemoryType,
    Document, QueryResult, RetrievalResult
)

@pytest.fixture
def mock_ltm():
    """Mock long-term memory store."""
    return Mock()

@pytest.fixture
def mock_episodic():
    """Mock episodic memory store."""
    return Mock()

@pytest.fixture
def test_doc():
    """Sample document for testing."""
    return Document(
        id="test1",
        content="Test document content",
        metadata={"source": "test", "type": "document"}
    )

@pytest.fixture
def memory_bridge(mock_ltm, mock_episodic):
    """Create memory bridge with mock stores."""
    bridge = MemoryBridge()
    bridge.ltm = mock_ltm
    bridge.episodic = mock_episodic
    return bridge

def test_pre_retrieve_hook(memory_bridge, test_doc):
    """Test pre-retrieval hook."""
    # Setup mock response
    memory_bridge.ltm.get_relevant.return_value = [test_doc]
    memory_bridge.episodic.get_relevant.return_value = []
    
    # Call hook
    query = "test query"
    context = {"session_id": "test123"}
    result = memory_bridge.pre_retrieve(query, context)
    
    # Verify LTM and episodic were queried
    memory_bridge.ltm.get_relevant.assert_called_once_with(query)
    memory_bridge.episodic.get_relevant.assert_called_once_with(query, context)
    
    # Verify result contains merged docs
    assert len(result.documents) == 1
    assert result.documents[0].id == test_doc.id

def test_post_retrieve_hook(memory_bridge, test_doc):
    """Test post-retrieval processing."""
    # Setup mock response
    memory_bridge.ltm.update.return_value = None
    
    # Call hook
    query = "test query"
    context = {"session_id": "test123"}
    result = RetrievalResult(
        query=query,
        documents=[test_doc],
        metadata={"source": "test"}
    )
    
    processed = memory_bridge.post_retrieve(result, context)
    
    # Verify document was stored in LTM
    memory_bridge.ltm.update.assert_called_once_with([test_doc])
    
    # Verify result wasn't modified
    assert processed == result

def test_post_answer_hook(memory_bridge):
    """Test post-answer processing."""
    # Setup
    query = "test query"
    answer = "test answer"
    context = {"session_id": "test123"}
    
    # Call hook
    memory_bridge.post_answer(query, answer, context)
    
    # Verify stored in episodic memory
    memory_bridge.episodic.store.assert_called_once()
    call_args = memory_bridge.episodic.store.call_args[0]
    assert call_args[0] == query
    assert call_args[1] == answer
    assert call_args[2] == context

def test_memory_persistence(tmp_path):
    """Test saving and loading memory state."""
    # Create temp files
    ltm_path = tmp_path / "ltm.json"
    episodic_path = tmp_path / "episodic.json"
    
    # Create bridge with persistence
    bridge = MemoryBridge(
        ltm_path=ltm_path,
        episodic_path=episodic_path
    )
    
    # Add test data
    test_doc = Document(
        id="test1", 
        content="test content",
        metadata={"source": "test"}
    )
    bridge.ltm.update([test_doc])
    bridge.episodic.store("test query", "test answer", {})
    
    # Save state
    bridge.save_state()
    
    # Verify files exist
    assert ltm_path.exists()
    assert episodic_path.exists()
    
    # Create new bridge and load state
    new_bridge = MemoryBridge(
        ltm_path=ltm_path,
        episodic_path=episodic_path
    )
    
    # Verify state was restored
    restored_docs = new_bridge.ltm.get_relevant("test")
    assert len(restored_docs) == 1
    assert restored_docs[0].id == test_doc.id

def test_error_handling(memory_bridge):
    """Test error handling in hooks."""
    # Setup mocks
    memory_bridge.ltm.get_relevant.side_effect = Exception("Test error")
    memory_bridge.episodic.get_relevant.return_value = []
    
    # Call hook - should not propagate error
    query = "test query"
    context = {"session_id": "test123"}
    result = memory_bridge.pre_retrieve(query, context)
    
    # Verify empty results returned
    assert len(result.documents) == 0

def test_memory_type_validation():
    """Test memory type validation."""
    # Invalid memory type
    with pytest.raises(ValueError):
        MemoryBridge(memory_type="invalid")
    
    # Valid memory types
    bridge = MemoryBridge(memory_type=MemoryType.SEMANTIC)
    assert bridge.memory_type == MemoryType.SEMANTIC

# ============================================================================
# Memory Bridge Service Tests
# ============================================================================

@pytest.fixture
def memory_service(mock_ltm, mock_episodic):
    """Create memory bridge service with mock stores."""
    service = MemoryBridgeService()
    service.bridge.ltm = mock_ltm
    service.bridge.episodic = mock_episodic
    return service

@pytest.mark.asyncio
async def test_service_get_relevant(memory_service, test_doc):
    """Test async get_relevant in service."""
    # Setup mock response
    memory_service.bridge.ltm.get_relevant.return_value = [test_doc]
    memory_service.bridge.episodic.get_relevant.return_value = []
    
    # Call service
    query = "test query"
    context = {"session_id": "test123"}
    result = await memory_service.get_relevant(query, context)
    
    # Verify LTM and episodic were queried
    memory_service.bridge.ltm.get_relevant.assert_called_once_with(query)
    memory_service.bridge.episodic.get_relevant.assert_called_once_with(query, context)
    
    # Verify result contains docs
    assert len(result.documents) == 1
    assert result.documents[0].id == test_doc.id

@pytest.mark.asyncio
async def test_service_store_interaction(memory_service):
    """Test async store_interaction in service."""
    # Setup test data
    query = "test query"
    answer = "test answer"
    context = {"session_id": "test123"}
    
    # Call service
    await memory_service.store_interaction(query, answer, context)
    
    # Verify episodic storage
    memory_service.bridge.episodic.store.assert_called_once_with(query, answer, context)

@pytest.mark.asyncio
async def test_service_update_documents(memory_service, test_doc):
    """Test async update_documents in service."""
    # Setup test data
    query = "test query"
    result = RetrievalResult(
        query=query,
        documents=[test_doc],
        metadata={"source": "test"}
    )
    
    # Call service
    processed = await memory_service.update_documents(result)
    
    # Verify LTM update
    memory_service.bridge.ltm.update.assert_called_once_with([test_doc])
    
    # Verify result wasn't modified
    assert processed == result

def test_service_save(memory_service):
    """Test service save state."""
    memory_service.save()
    # Could verify internal calls if needed