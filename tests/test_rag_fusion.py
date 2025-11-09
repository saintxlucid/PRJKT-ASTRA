"""
ASTRA RAG Fusion Tests
Created: October 25, 2025

Test suite for ASTRA's RAG Fusion engine, covering:
- Memory retrieval with energy thresholds
- Context planning and budgeting
- Persona integration
- Citation tracking
- Error handling
"""
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

from astra.core.rag_fusion import RAGFusionEngine
from astra.memory_types import Memory, MemoryEnergy

# Test fixtures
@pytest.fixture
def sample_memories() -> List[Memory]:
    """Generate test memory entries"""
    return [
        Memory(
            id="mem1",
            content="The capital of France is Paris.",
            source="geography_facts.txt",
            energy=0.8,
            created_at=datetime.now(),
            metadata={"type": "fact"}
        ),
        Memory(
            id="mem2",
            content="Paris is known as the City of Light.",
            source="city_facts.txt",
            energy=0.7,
            created_at=datetime.now(),
            metadata={"type": "fact"}
        ),
        Memory(
            id="mem3", 
            content="The Eiffel Tower was built in 1889.",
            source="landmarks.txt",
            energy=0.9,
            created_at=datetime.now(),
            metadata={"type": "fact"}
        )
    ]

@pytest.fixture
def sample_persona() -> Dict[str, Any]:
    """Generate test persona"""
    return {
        "name": "History Guide",
        "description": "A knowledgeable guide focused on historical facts",
        "style": "informative and precise"
    }

@pytest.fixture
async def rag_engine(sample_memories: List[Memory]) -> RAGFusionEngine:
    """Create RAG engine with mocked dependencies"""
    # Mock memory engine
    memory_engine = AsyncMock()
    memory_engine.search.return_value = sample_memories
    
    # Mock persona manager
    persona_manager = AsyncMock()
    persona_manager.get_persona.return_value = {
        "name": "History Guide",
        "description": "A knowledgeable guide focused on historical facts"
    }
    
    # Mock inference queue
    inference_queue = AsyncMock()
    inference_queue.enqueue.return_value = {
        "text": "Generated response",
        "generation_time": 0.5,
        "output_tokens": 50
    }
    
    engine = RAGFusionEngine(
        memory_engine=memory_engine,
        persona_manager=persona_manager,
        inference_queue=inference_queue
    )
    
    return engine

# Test memory retrieval
@pytest.mark.asyncio
async def test_memory_retrieval(rag_engine: RAGFusionEngine):
    """Test memory retrieval with energy threshold"""
    memories = await rag_engine._retrieve_memories(
        query="Tell me about Paris",
        k=3,
        trace_id="test-trace"
    )
    
    assert len(memories) == 3
    assert all(m.energy >= rag_engine.min_energy for m in memories)
    assert rag_engine.memory_engine.search.called
    
# Test context planning
def test_context_planning(rag_engine: RAGFusionEngine, sample_memories: List[Memory]):
    """Test context composition and citation tracking"""
    context, citations = rag_engine._plan_context(
        memories=sample_memories,
        max_tokens=1000
    )
    
    # Verify context format
    assert "[src1]" in context
    assert "[src2]" in context
    assert "[src3]" in context
    
    # Verify citations
    assert len(citations) == 3
    assert all(c["id"] for c in citations.values())
    assert all(c["source"] for c in citations.values())
    assert all(c["timestamp"] for c in citations.values())
    
# Test system prompt composition
def test_system_prompt_composition(rag_engine: RAGFusionEngine, sample_persona: Dict[str, Any]):
    """Test persona-anchored prompt generation"""
    context = "[src1] Test context"
    prompt = rag_engine._compose_system_prompt(sample_persona, context)
    
    assert sample_persona["name"] in prompt
    assert sample_persona["description"] in prompt
    assert "[src1]" in prompt
    assert "Test context" in prompt
    
# Test energy statistics
def test_energy_statistics(rag_engine: RAGFusionEngine, sample_memories: List[Memory]):
    """Test energy statistics calculation"""
    stats = rag_engine._calculate_energy_stats(sample_memories)
    
    assert "avg_energy" in stats
    assert "max_energy" in stats
    assert "min_energy" in stats
    assert stats["max_energy"] == 0.9  # From sample data
    assert stats["min_energy"] == 0.7  # From sample data
    
# Test end-to-end answer generation
@pytest.mark.asyncio
async def test_answer_generation(rag_engine: RAGFusionEngine):
    """Test complete answer generation pipeline"""
    response = await rag_engine.answer(
        query="What is the capital of France?",
        session_id="test-session",
        persona_id="history-guide"
    )
    
    # Verify response structure
    assert "text" in response
    assert "memory_ids" in response
    assert "adapter_ids" in response
    assert "citations" in response
    assert "metrics" in response
    assert "trace_id" in response
    
    # Verify metrics
    assert "retrieval_time" in response["metrics"]
    assert "total_time" in response["metrics"]
    assert "context_tokens" in response["metrics"]
    assert "output_tokens" in response["metrics"]
    
# Test error handling
@pytest.mark.asyncio
async def test_memory_retrieval_error(rag_engine: RAGFusionEngine):
    """Test error handling in memory retrieval"""
    rag_engine.memory_engine.search.side_effect = Exception("Search failed")
    
    with pytest.raises(Exception):
        await rag_engine._retrieve_memories(
            query="test query",
            k=3,
            trace_id="test-trace"
        )
        
# Test token budget enforcement
def test_token_budget_enforcement(rag_engine: RAGFusionEngine, sample_memories: List[Memory]):
    """Test context stays within token budget"""
    # Set a very small token budget
    max_tokens = 10
    context, citations = rag_engine._plan_context(sample_memories, max_tokens)
    
    # Rough token count (split by spaces)
    token_count = len(context.split())
    assert token_count <= max_tokens