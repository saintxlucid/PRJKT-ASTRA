"""
Test suite for Multi-RAG pipeline components.
"""

import pytest
import asyncio
import shutil
from pathlib import Path
import tempfile
from typing import List
from datetime import datetime, UTC

from astra.rag.document import Document, SearchResults
from astra.rag.fusion import rrf_fusion, interpolation_fusion
from astra.rag.callbacks import CallbackManager, JSONLEventLogger
from astra.rag.retrievers import BaseRetriever

class MockRetriever(BaseRetriever):
    """Mock retriever for testing."""
    
    def __init__(self, retriever_id: str, documents: List[Document]):
        super().__init__(retriever_id)
        self.documents = documents
    
    async def retrieve(self, query: str, k: int = 10, **kwargs) -> SearchResults:
        self._emit_event("retrieval_start", query=query, k=k)
        results = self.documents[:k]
        for i, doc in enumerate(results):
            doc.score = 1.0 - (i * 0.1)  # Descending scores
        self._emit_event("retrieval_complete", n_results=len(results))
        return SearchResults(documents=results, retriever_id=self.retriever_id)
    
    async def add_documents(self, documents: List[Document], **kwargs) -> bool:
        self.documents.extend(documents)
        return True

def test_document_operations():
    """Test document creation and conversion."""
    doc = Document(
        content="test content",
        metadata={"source": "test"}
    )
    
    # Test dictionary conversion
    doc_dict = doc.to_dict()
    assert doc_dict["content"] == "test content"
    assert doc_dict["metadata"]["source"] == "test"
    
    # Test reconstruction
    new_doc = Document.from_dict(doc_dict)
    assert new_doc.content == doc.content
    assert new_doc.metadata == doc.metadata

@pytest.mark.asyncio
async def test_fusion():
    """Test RRF and interpolation fusion."""
    # Create test documents
    docs1 = [
        Document(content=f"doc1_{i}", metadata={"source": "test1"})
        for i in range(5)
    ]
    docs2 = [
        Document(content=f"doc2_{i}", metadata={"source": "test2"})
        for i in range(5)
    ]
    
    # Create mock retrievers
    r1 = MockRetriever("test1", docs1)
    r2 = MockRetriever("test2", docs2)
    
    # Get results
    results1 = await r1.retrieve("test")
    results2 = await r2.retrieve("test")
    
    # Test RRF fusion
    rrf_results = rrf_fusion([results1, results2], k=8)
    assert len(rrf_results) == 8
    assert all(doc.score is not None for doc in rrf_results)
    
    # Test interpolation fusion
    interp_results = interpolation_fusion(
        [results1, results2],
        weights=[0.7, 0.3],
        k=8
    )
    assert len(interp_results) == 8
    assert all(doc.score is not None for doc in interp_results)

@pytest.mark.asyncio
async def test_callbacks():
    """Test callback system."""
    events = []
    
    def collect_events(event):
        events.append(event)
    
    # Set up callback manager
    manager = CallbackManager()
    manager.add_callback(collect_events, ["retrieval_start"])
    manager.add_callback(collect_events)  # Global callback
    
    # Create and use mock retriever
    docs = [Document(content="test", metadata={"source": "test"})]
    retriever = MockRetriever("test", docs)
    retriever._callback = manager
    
    await retriever.retrieve("test query")
    
    # Check events were collected
    assert len(events) == 3  # 1 specific + 2 global
    assert events[0].event_type == "retrieval_start"
    assert events[0].retriever_id == "test"

@pytest.mark.asyncio
async def test_jsonl_logger():
    """Test JSONL event logging."""
    temp_dir = tempfile.mkdtemp()
    log_file = Path(temp_dir) / "events.jsonl"
    
    try:
        # Set up logger
        logger = JSONLEventLogger(str(log_file))
        
        # Create and use mock retriever
        docs = [Document(content="test", metadata={"source": "test"})]
        retriever = MockRetriever("test", docs)
        retriever._callback = logger
        
        await retriever.retrieve("test query")
        
        # Check file contents
        content = log_file.read_text()
        assert "retrieval_start" in content
        assert "retrieval_complete" in content
    finally:
        # Cleanup
        if log_file.exists():
            log_file.unlink()
        Path(temp_dir).rmdir()