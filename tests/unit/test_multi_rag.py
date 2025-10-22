"""
Tests for the Multi-RAG pipeline and Query Router
"""
import pytest
import json
import tempfile
from pathlib import Path

from astra.rag.routing.router import QueryRouter, Route
from astra.rag.pipelines.multi_rag import MultiRAGPipeline, MultiRAGConfig

@pytest.fixture
def sample_config():
    return {
        "multi_rag": {
            "dense_batch_size": 32,
            "max_concurrent": 4,
            "rerank_cutoff": 50,
            "max_results": 10,
            "cache_ttl": 3600,
            "consent_required": True
        },
        "fusion": {
            "interpolation": {
                "keyword": {"bm25": 0.8, "dense": 0.2},
                "semantic": {"bm25": 0.2, "dense": 0.8},
                "code": {"bm25": 0.4, "dense": 0.6}
            },
            "mmr_lambda": 0.7,
            "min_score": 0.3
        }
    }

@pytest.fixture
def config_path(sample_config, tmp_path):
    config_file = tmp_path / "config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config, f)
    return str(config_file)

@pytest.fixture
def query_router():
    return QueryRouter()

@pytest.mark.asyncio
async def test_query_router_intents(query_router):
    """Test query intent classification"""
    
    # Test keyword queries
    keyword_queries = [
        "what is RAG",
        "define embeddings",
        "show config settings",
        "list all functions",
        "where is the data stored"
    ]
    for query in keyword_queries:
        route = query_router.route(query)
        assert route.intent == "keyword"
        assert route.use_bm25
        assert route.alpha < 0.5  # Favor BM25 for keywords
        
    # Test code queries
    code_queries = [
        "python asyncio.gather example",
        "how to use TaskPlanner.create_plan()",
        "fix ValueError in process_chunks",
        "TypeError: object not callable",
        "implement IRetriever interface"
    ]
    for query in code_queries:
        route = query_router.route(query)
        assert route.intent == "code"
        assert route.use_bm25 and route.use_dense
        assert 0.4 <= route.alpha <= 0.6  # Balanced for code
        
    # Test semantic queries
    semantic_queries = [
        "explain the benefits of hybrid search retrieval",
        "how does the fusion algorithm combine results",
        "what are the best practices for RAG implementation",
        "compare different reranking strategies"
    ]
    for query in semantic_queries:
        route = query_router.route(query)
        assert route.intent == "semantic"
        assert route.use_dense
        assert route.alpha > 0.7  # Favor dense for semantic

@pytest.mark.asyncio
async def test_empty_queries(query_router):
    """Test handling of empty queries"""
    empty_queries = ["", "   ", "\n", "\t"]
    for query in empty_queries:
        route = query_router.route(query)
        assert route.intent == "semantic"  # Default intent
        assert route.use_dense  # Default to dense retrieval

@pytest.mark.asyncio
async def test_router_analytics(query_router):
    """Test analytics tracking"""
    # Run some test queries
    test_queries = [
        "what is RAG",  # keyword
        "implement interface",  # code
        "explain fusion methods",  # semantic
        "show config",  # keyword
        "debug TypeError"  # code
    ]
    
    for query in test_queries:
        query_router.route(query)
    
    # Check analytics
    analytics = query_router.get_analytics()
    assert "intents" in analytics
    assert "intent_dist" in analytics
    
    # Verify counts
    intents = analytics["intents"]
    assert intents["keyword"] >= 2
    assert intents["code"] >= 2
    assert intents["semantic"] >= 1
    
    # Verify distribution sums to ~1
    dist = analytics["intent_dist"]
    assert abs(sum(dist.values()) - 1.0) < 0.0001

@pytest.mark.asyncio
async def test_pipeline_initialization(config_path):
    """Test pipeline initialization"""
    try:
        pipeline = MultiRAGPipeline(
            config_path=config_path,
            telemetry_dir=None  # Disable telemetry for tests
        )
        assert pipeline.router is not None
        assert pipeline.fusion is not None
        assert pipeline.config is not None
    except Exception as e:
        pytest.fail(f"Pipeline initialization failed: {e}")

@pytest.mark.asyncio
async def test_pipeline_empty_query(config_path):
    """Test pipeline handling of empty queries"""
    pipeline = MultiRAGPipeline(config_path=config_path)
    results = await pipeline.retrieve("")
    assert len(results) == 0
    
    results = await pipeline.retrieve("   ")
    assert len(results) == 0

@pytest.mark.asyncio
async def test_pipeline_consent_filtering(config_path):
    """Test consent-aware filtering"""
    pipeline = MultiRAGPipeline(config_path=config_path)
    
    # Mock some results with consent metadata
    pipeline.fusion.interpolate = lambda **kwargs: [
        {"id": "1", "metadata": {"consent": True}},
        {"id": "2", "metadata": {"consent": False}},
        {"id": "3", "metadata": {"consent": True}}
    ]
    
    results = await pipeline.retrieve("test query")
    assert len(results) == 2  # Only consent=True results
    assert all(r["metadata"]["consent"] for r in results)