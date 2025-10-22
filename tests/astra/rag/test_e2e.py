"""
End-to-end tests for Multi-RAG system.
Tests full integration of components including telemetry and memory bridge.
"""
import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime, UTC
import structlog
import tempfile
import json
from pathlib import Path

from astra.rag.initialize import init_multi_rag
from astra.rag.document import Document
from astra.rag.retrievers import BaseRetriever
from astra.rag.telemetry import TelemetryEmitter
from astra.core.memory import MemoryBridgeConnector
from astra.rag.modules.events import EventBus


# ============================================================================
# STUB IMPLEMENTATIONS
# ============================================================================

class StubRetriever(BaseRetriever):
    """Stub retriever for testing."""
    
    def __init__(self, retriever_id: str = "stub"):
        super().__init__(retriever_id)
        self.documents: List[Document] = []
        self.last_query: str = ""
        self.should_fail: bool = False
        
    async def _retrieve(self, query: str, k: int = 10) -> List[Document]:
        """Execute retrieval."""
        self.last_query = query
        if self.should_fail:
            raise RuntimeError("Simulated retrieval failure")
        return self.documents[:k]
        
    async def _add_documents(self, documents: List[Document]) -> bool:
        """Add documents to retriever."""
        self.documents.extend(documents)
        return True


class StubMemoryBridge(MemoryBridgeConnector):
    """Stub memory bridge for testing."""
    
    def __init__(self):
        self.episodic_records: List[Dict[str, Any]] = []
        self.ltm_records: List[Dict[str, Any]] = []
        
    async def get_episodic_context(self, query: str) -> List[Dict[str, Any]]:
        """Get episodic memory context."""
        return self.episodic_records
        
    async def get_ltm_context(self, query: str) -> List[Dict[str, Any]]:
        """Get LTM context."""
        return self.ltm_records
        
    def record_interpretation(self, safe_text: str, meta: Dict[str, Any]):
        """Record interpretation in episodic memory."""
        self.episodic_records.append({
            "text": safe_text,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": meta
        })


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_telemetry_dir():
    """Create temporary directory for telemetry files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def telemetry_emitter(temp_telemetry_dir):
    """Create telemetry emitter with temp directory."""
    emitter = TelemetryEmitter(
        base_path=temp_telemetry_dir,
        max_file_size=1024 * 1024  # 1MB
    )
    return emitter


@pytest.fixture
def event_bus():
    """Create event bus instance."""
    return EventBus()


@pytest.fixture
def stub_retriever():
    """Create stub retriever instance."""
    return StubRetriever()


@pytest.fixture
def stub_memory():
    """Create stub memory bridge instance."""
    return StubMemoryBridge()


@pytest.fixture
def test_documents():
    """Create test document set."""
    return [
        Document(
            doc_id="doc1",
            text="Test document one about AI",
            metadata={"source": "test", "category": "ai"}
        ),
        Document(
            doc_id="doc2", 
            text="Test document two about ML",
            metadata={"source": "test", "category": "ml"}
        ),
        Document(
            doc_id="doc3",
            text="Test document three about NLP",
            metadata={"source": "test", "category": "nlp"}
        )
    ]


@pytest.fixture
def multi_rag_system(
    event_bus,
    stub_retriever,
    stub_memory,
    telemetry_emitter,
    test_documents
):
    """Initialize Multi-RAG system with stub components."""
    # Add test documents to retriever
    asyncio.run(stub_retriever.add_documents(test_documents))
    
    # Create test config
    config = {
        "retriever": {
            "top_k": 5
        },
        "memory": {
            "ltm_threshold": 0.5,
            "episodic_threshold": 0.6
        },
        "pipeline": {
            "fusion_method": "rrf",
            "top_k": 3
        },
        "tool": {
            "default_k": 5,
            "default_policy": "default"
        }
    }
    
    # Initialize system
    system = init_multi_rag(config)
    
    # Override components with stubs
    system["retriever"] = stub_retriever
    system["memory"] = stub_memory
    
    return system


# ============================================================================
# TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_basic_retrieval_flow(multi_rag_system):
    """Test basic retrieval execution flow."""
    # Execute retrieval
    results = await multi_rag_system["pipeline"].retrieve(
        query="test query",
        top_k=2
    )
    
    # Verify results
    assert len(results) == 2
    assert all(isinstance(doc, Document) for doc in results)
    assert multi_rag_system["retriever"].last_query == "test query"


@pytest.mark.asyncio
async def test_memory_bridge_integration(multi_rag_system):
    """Test memory bridge callback integration."""
    # Execute retrieval to trigger callbacks
    await multi_rag_system["pipeline"].retrieve(
        query="test memory integration"
    )
    
    # Verify episodic record
    memory = multi_rag_system["memory"]
    assert len(memory.episodic_records) > 0
    assert "test memory integration" in str(memory.episodic_records[0])


@pytest.mark.asyncio
async def test_telemetry_events(multi_rag_system, temp_telemetry_dir):
    """Test telemetry event emission."""
    # Execute retrieval to generate events
    await multi_rag_system["pipeline"].retrieve(
        query="test telemetry"
    )
    
    # Check telemetry files
    telemetry_files = list(temp_telemetry_dir.glob("*.jsonl"))
    assert len(telemetry_files) > 0
    
    # Verify event contents
    events = []
    with open(telemetry_files[0]) as f:
        for line in f:
            events.append(json.loads(line))
    
    # Should have retrieval and fusion events
    assert len(events) >= 2
    event_types = {e["event_type"] for e in events}
    assert "retrieval_complete" in event_types
    assert "fusion_complete" in event_types


@pytest.mark.asyncio
async def test_orchestrator_actions(multi_rag_system):
    """Test orchestrator action registration and execution."""
    # Get action registry
    registry = multi_rag_system["actions"].registry
    
    # Verify registered actions
    actions = registry.list_services()
    assert any("rag_action_" in action for action in actions)
    
    # Execute action
    results = await registry.execute_service(
        "rag_action_cognitive_search",
        query="test orchestrator action"
    )
    assert results is not None
    assert "documents" in results


@pytest.mark.asyncio
async def test_error_handling(multi_rag_system):
    """Test error handling and telemetry."""
    # Configure retriever to fail
    multi_rag_system["retriever"].should_fail = True
    
    # Attempt retrieval
    with pytest.raises(RuntimeError):
        await multi_rag_system["pipeline"].retrieve(
            query="test error handling"
        )
    
    # Verify error telemetry
    # TODO: Add verification of error events once implemented