"""
Smoke test script for Qdrant integration.
Ingests sample documents and verifies basic functionality.
"""
import os
import time
from pathlib import Path
import yaml
import structlog

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from astra.embed.bge import BGEM3Embedder
from astra.store.qdrant_store import QdrantStore

from astra.rag.pipeline import MultiRAGPipeline
from astra.rag.document import Document
from astra.telemetry.events import EventLogger

logger = structlog.get_logger()

# Sample test documents
TEST_DOCS = [
    Document(
        id="smoke1",
        text="""
        Artificial Intelligence (AI) is revolutionizing how we live and work.
        Machine learning models can now perform tasks that once required human intelligence.
        Natural language processing enables computers to understand and generate human text.
        """,
        metadata={"source": "ai_overview.txt", "category": "technology"}
    ),
    Document(
        id="smoke2",
        text="""
        Deep learning is a subset of machine learning based on artificial neural networks.
        These networks are inspired by the human brain's structure and function.
        They excel at pattern recognition and feature extraction from complex data.
        """,
        metadata={"source": "deep_learning.txt", "category": "technology"}
    ),
    Document(
        id="smoke3",
        text="""
        Quantum computing leverages quantum mechanics principles for computation.
        Quantum bits or qubits can exist in multiple states simultaneously.
        This enables quantum computers to solve certain problems exponentially faster.
        """,
        metadata={"source": "quantum_computing.txt", "category": "technology"}
    )
]

def main():
    """Run smoke tests for Qdrant integration."""
    try:
        # Initialize logging
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        event_logger = EventLogger(
            log_dir=str(log_dir),
            rotation_bytes=1048576,
            max_files=5
        )
        
        # Load config
        with open("config/rag.yaml") as f:
            config = yaml.safe_load(f)
            
        logger.info("loaded_config", config=config)
        
        # Create embedder with explicit CPU
        embedder = BGEM3Embedder(device="cpu")
        logger.info("created_embedder")
        
        # Set up Qdrant client
        client = QdrantClient(
            url="http://localhost:6333",
            timeout=30.0
        )
        
        # Create collection
        try:
            client.recreate_collection(
                collection_name="astra_documents",
                vectors_config=rest.VectorParams(
                    size=1024,
                    distance=rest.Distance.COSINE
                )
            )
        except Exception as e:
            logger.error("collection_create_failed", error=str(e))
            raise
            
        logger.info("created_collection")
        
        # Create store
        store = QdrantStore(
            embedder=embedder,
            url="http://localhost:6333",
            collection_name="astra_documents"
        )
        logger.info("created_store")
        
        # Create pipeline
        pipeline = MultiRAGPipeline(
            dense_index=store,
            embedder=embedder
        )
        logger.info("created_pipeline")
        
        # Test ingestion
        store.add_documents(TEST_DOCS)
        logger.info("ingested_documents", count=len(TEST_DOCS))
        
        # Verify ingestion events
        time.sleep(1)  # Wait for async events
        
        log_file = Path("data/logs/ingestion.jsonl")
        assert log_file.exists()
        logger.info("verified_ingestion_logs")
        
        # Test retrieval
        results1 = pipeline.retrieve(
            "How does deep learning work?",
            k=2
        )
        assert len(results1) == 2
        assert any("deep learning" in r.text.lower() for r in results1)
        logger.info("retrieval_successful", count=len(results1))
        
        # Test caching
        start = time.time()
        results2 = pipeline.retrieve(
            "How does deep learning work?",
            k=2
        )
        duration = time.time() - start
        
        assert len(results2) == 2
        assert [r.id for r in results1] == [r.id for r in results2]
        assert duration < 0.1  # Cache should be fast
        logger.info("cache_verified", duration=duration)
        
        # Test different query
        results3 = pipeline.retrieve(
            "Explain quantum computing",
            k=2
        )
        assert len(results3) == 2
        assert any("quantum" in r.text.lower() for r in results3)
        logger.info("alternate_query_successful")
        
        logger.info("smoke_test_completed", status="success")
        return 0
        
    except Exception as e:
        logger.error("smoke_test_failed", error=str(e))
        return 1

if __name__ == "__main__":
    exit(main())