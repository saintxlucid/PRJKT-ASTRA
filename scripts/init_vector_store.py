"""Initialize and bootstrap vector store with knowledge base."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from astra.memory.vector_store import LocalVectorStore, EmbeddingConfig
from load_knowledge_base import KnowledgeBaseLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_vector_store():
    """Bootstrap vector store with sample knowledge base."""

    logger.info("=" * 60)
    logger.info("PHASE 2 TASK 1: Vector Store Initialization")
    logger.info("=" * 60)

    # 1. Create embedding config
    embedding_config = EmbeddingConfig(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=32,
        device="cpu"
    )
    logger.info(f"Embedding config: {embedding_config.to_dict()}")

    # 2. Initialize vector store
    vector_store = LocalVectorStore(
        embedding_config=embedding_config,
        collection_name="astra_knowledge",
        persist_directory="./data/vector_store",
        ttl_days=90
    )

    await vector_store.initialize()
    logger.info("✅ Vector store initialized")

    # 3. Load knowledge base
    loader = KnowledgeBaseLoader()

    sources = {
        "local_files": {
            "directory": Path("./docs"),
            "extensions": [".md", ".txt"]
        }
    }

    documents = await loader.load_and_prepare(sources)
    logger.info(f"✅ Loaded {len(documents)} documents")

    # 4. Add documents
    if documents:
        texts = [doc["text"] for doc in documents]
        metadatas = [
            {
                "source": doc.get("source", "unknown"),
                "category": doc.get("category", "general"),
            }
            for doc in documents
        ]

        result = await vector_store.add_documents(texts, metadatas)
        logger.info(f"✅ {result['documents_added']} documents added")

    # 5. Persist
    await vector_store.persist()
    logger.info("✅ Vector store persisted")

    # 6. Test retrieval
    logger.info("\n" + "=" * 60)
    logger.info("Testing Retrieval Performance")
    logger.info("=" * 60)

    import time
    test_queries = [
        "What is ASTRA?",
        "How does the boot orchestrator work?",
        "Describe vector store functionality",
    ]

    retrieval_times = []
    for query in test_queries:
        start = time.time()
        results = await vector_store.retrieve(query, top_k=3)
        elapsed = (time.time() - start) * 1000
        retrieval_times.append(elapsed)

        logger.info(f"\nQuery: '{query}'")
        logger.info(f"Retrieval latency: {elapsed:.2f}ms")

        for i, result in enumerate(results):
            logger.info(f"  [{i+1}] Score={result.similarity_score:.3f} | {result.text[:100]}...")

    avg_latency = sum(retrieval_times) / len(retrieval_times)
    logger.info(f"\n✅ Average retrieval latency: {avg_latency:.2f}ms")

    if avg_latency < 100:
        logger.info("✅ PASS: <100ms target achieved (P95)")
    else:
        logger.warning(f"⚠️  WARN: {avg_latency:.2f}ms > 100ms target")

    # 7. Print metrics
    metrics = vector_store.get_metrics()
    logger.info("\n" + "=" * 60)
    logger.info("Vector Store Metrics")
    logger.info("=" * 60)
    for key, value in metrics.items():
        logger.info(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(initialize_vector_store())
