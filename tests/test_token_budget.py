import pytest
from src.astra.core.rag.rag_fusion import RAGFusionEngine
from src.astra.core.rag.tokenization import get_token_counter

class MockMemory:
    """Mock memory system for testing"""
    async def retrieve(self, query, top_k=8, filter=None):
        # Return mock document with known token length
        return [{
            "id": "mock1",
            "metadata": {
                "text_preview": "x " * 500,  # Predictable token length
                "nutrition": {"energy_score": 0.9}
            },
            "score": 0.9
        }]

class MockPersona:
    """Mock persona for testing"""
    def get_anchor(self): 
        return "test_anchor"
    
    def system_prelude(self): 
        return "test_prelude"
    
    def anchor_id(self): 
        return "test_id"

@pytest.mark.asyncio
async def test_budget_respected():
    """Test that token budget limits are respected"""
    engine = RAGFusionEngine(
        memory=MockMemory(),
        persona=MockPersona(),
        token_counter=get_token_counter(),
        max_context_tokens=256,
        output_reserve_tokens=64
    )
    
    # Test fusion with budget constraints
    fused = await engine.fuse("test query", k=1)
    assert fused["context_tokens"] <= 256
    
    # Test that output reserve is maintained
    assert (fused["context_tokens"] + 64) <= engine.max_context_tokens
    
    # Verify warning logs when approaching limit
    with pytest.warns(UserWarning):
        await engine.fuse("test query " * 100, k=3)  # Force high token count

@pytest.mark.asyncio
async def test_graceful_truncation():
    """Test graceful truncation when exceeding budget"""
    engine = RAGFusionEngine(
        memory=MockMemory(),
        persona=MockPersona(),
        token_counter=get_token_counter(),
        max_context_tokens=100,  # Small budget to force truncation
        output_reserve_tokens=32
    )
    
    fused = await engine.fuse("test query", k=5)
    
    # Verify truncation
    assert fused["context_tokens"] <= 100
    assert len(fused["truncated_docs"]) > 0  # Should indicate truncation
    assert "truncation_reason" in fused