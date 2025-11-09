"""
Tests for ASTRA memory and ingest components
"""
import pytest
from ..src.astra.ingest import chunk_text, nutrition_score, Embedder, Ingestor
from ..src.astra.vector_stores import SimpleVecDB

def test_chunking():
    text = "This is a test. Of the chunking system. For ASTRA's memory."
    chunks = chunk_text(text, max_chars=20)
    assert len(chunks) > 1
    assert all(len(c) <= 20 for c in chunks)

def test_nutrition():
    text = "I love the sacred fire that burns in my heart when I cry tears of joy."
    meta = {"credibility": 0.8, "relevance": 0.7, "freshness": 0.9}
    score = nutrition_score(text, meta)
    assert 0 <= score["energy_score"] <= 1
    assert score["emotional_density"] > 0.3  # emotional words present
    assert score["novelty"] > 0  # has unique words

def test_embedder():
    emb = Embedder()
    texts = ["test one", "test two"]
    embeddings = emb.embed(texts)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == emb.dim

def test_ingestor():
    store = SimpleVecDB()
    ingestor = Ingestor(store=store)
    text = "This is a test of ASTRA's memory system. It should work well."
    meta = {
        "author": "test",
        "source": "test",
        "credibility": 0.8,
        "relevance": 0.7,
        "freshness": 0.9
    }
    result = ingestor.ingest_text(text, metadata=meta)
    assert "session_id" in result
    assert len(result["chunks"]) > 0
    first_id = result["chunks"][0]["id"]
    # test retrieval
    similar = ingestor.retrieve_by_text("test memory system")
    assert len(similar) > 0
    # test get
    stored = ingestor.get(first_id)
    assert stored is not None
    meta = stored["metadata"]
    assert "nutrition" in meta
    assert "provenance" in meta
    assert meta["embedding_model"] == ingestor.embedder.model_name