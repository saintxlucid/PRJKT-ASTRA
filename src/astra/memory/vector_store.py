"""
Local vector store using ChromaDB with HNSW indexing.
Provides semantic search with <100ms retrieval latency.
"""

from dataclasses import dataclass, field
from typing import Any
import asyncio
import json
import time
from datetime import datetime, timedelta
import logging

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for local embedding model."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    device: str = "cpu"
    cache_folder: str = "./cache/embeddings"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "batch_size": self.batch_size,
            "device": self.device,
        }


@dataclass
class RetrievalResult:
    """Single retrieval result with metadata."""
    document_id: str
    text: str
    similarity_score: float
    metadata: dict[str, Any]
    retrieved_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "text": self.text,
            "similarity_score": float(self.similarity_score),
            "metadata": self.metadata,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


class LocalEmbeddingModel:
    """Lazy-loaded local embedding model using sentence-transformers."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model = None
        self.loaded_at = None
    
    async def load(self) -> None:
        """Lazy load model on first use."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.config.model_name}")
            start = time.time()
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device,
                cache_folder=self.config.cache_folder
            )
            elapsed = time.time() - start
            self.loaded_at = datetime.now()
            logger.info(f"Embedding model loaded in {elapsed:.2f}s")
    
    async def embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts to vectors."""
        await self.load()
        embeddings = self.model.encode(
            texts,
            batch_size=self.config.batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings
    
    async def embed_single(self, text: str) -> np.ndarray:
        """Embed single text."""
        embeddings = await self.embed([text])
        return embeddings[0]


class LocalVectorStore:
    """ChromaDB-based local vector store with TTL and batch processing."""
    
    def __init__(
        self,
        embedding_config: EmbeddingConfig | None = None,
        collection_name: str = "astra_knowledge",
        persist_directory: str = "./data/vector_store",
        ttl_days: int = 90
    ):
        self.embedding_config = embedding_config or EmbeddingConfig()
        self.embedding_model = LocalEmbeddingModel(self.embedding_config)
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.ttl_days = ttl_days
        self.client = None
        self.collection = None
        self.metrics = {
            "documents_added": 0,
            "documents_retrieved": 0,
            "total_retrieval_time_ms": 0.0,
            "avg_retrieval_latency_ms": 0.0,
        }
    
    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        logger.info(f"Initializing vector store: {self.collection_name}")
        
        # Initialize ChromaDB with persistence
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.persist_directory,
            anonymized_telemetry=False,
        )
        self.client = chromadb.Client(settings)
        
        # Get or create collection with HNSW indexing
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": 16,
                "hnsw:ef_construction": 200,
            }
        )
        
        logger.info(f"Vector store initialized: {self.collection_name}")
    
    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
        batch_size: int = 32
    ) -> dict[str, Any]:
        """Add documents with embeddings and metadata."""
        if not self.collection:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")
        
        if ids is None:
            ids = [f"doc_{i}_{int(time.time())}" for i in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{"source": "unknown"} for _ in documents]
        
        # Add TTL to metadata
        for metadata in metadatas:
            metadata["created_at"] = datetime.now().isoformat()
            metadata["expires_at"] = (datetime.now() + timedelta(days=self.ttl_days)).isoformat()
        
        logger.info(f"Adding {len(documents)} documents to vector store (batch_size={batch_size})")
        
        # Batch process for efficiency
        total_batches = (len(documents) + batch_size - 1) // batch_size
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(documents))
            
            batch_docs = documents[start_idx:end_idx]
            batch_ids = ids[start_idx:end_idx]
            batch_metas = metadatas[start_idx:end_idx]
            
            # Embed batch
            embeddings = await self.embedding_model.embed(batch_docs)
            
            # Add to collection
            self.collection.add(
                ids=batch_ids,
                embeddings=embeddings.tolist(),
                documents=batch_docs,
                metadatas=batch_metas
            )
            
            logger.debug(f"Added batch {batch_idx + 1}/{total_batches}")
        
        self.metrics["documents_added"] += len(documents)
        
        return {
            "status": "success",
            "documents_added": len(documents),
            "collection": self.collection_name,
        }
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_metadata: bool = True
    ) -> list[RetrievalResult]:
        """Retrieve top-k similar documents."""
        if not self.collection:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")
        
        start_time = time.time()
        
        # Embed query
        query_embedding = await self.embedding_model.embed_single(query)
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        latency_ms = (time.time() - start_time) * 1000
        self.metrics["documents_retrieved"] += top_k
        self.metrics["total_retrieval_time_ms"] += latency_ms
        self.metrics["avg_retrieval_latency_ms"] = (
            self.metrics["total_retrieval_time_ms"] / 
            max(1, self.metrics["documents_retrieved"])
        )
        
        # Build retrieval results
        retrieval_results = []
        if results and results["documents"] and len(results["documents"]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                # Convert distance to similarity (cosine distance -> similarity)
                similarity = 1 - results["distances"][0][i]
                
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                retrieval_results.append(RetrievalResult(
                    document_id=f"doc_{i}",
                    text=doc,
                    similarity_score=similarity,
                    metadata=metadata
                ))
        
        logger.debug(f"Retrieved {len(retrieval_results)} documents in {latency_ms:.2f}ms")
        
        return retrieval_results
    
    async def purge_expired(self) -> dict[str, Any]:
        """Remove expired documents (TTL-based)."""
        if not self.collection:
            raise RuntimeError("Vector store not initialized. Call initialize() first.")
        
        now = datetime.now()
        
        # Get all documents with metadata
        all_docs = self.collection.get(include=["metadatas"])
        
        expired_ids = []
        for i, metadata in enumerate(all_docs["metadatas"]):
            if "expires_at" in metadata:
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if now > expires_at:
                    expired_ids.append(all_docs["ids"][i])
        
        if expired_ids:
            self.collection.delete(ids=expired_ids)
            logger.info(f"Purged {len(expired_ids)} expired documents")
        
        return {
            "status": "success",
            "expired_documents_removed": len(expired_ids),
        }
    
    async def persist(self) -> dict[str, Any]:
        """Persist vector store to disk."""
        if self.client:
            self.client.persist()
            logger.info(f"Vector store persisted to {self.persist_directory}")
        
        return {
            "status": "success",
            "persist_directory": self.persist_directory,
        }
    
    def get_metrics(self) -> dict[str, Any]:
        """Get vector store metrics."""
        count = 0
        if self.collection:
            count = self.collection.count()
        
        return {
            **self.metrics,
            "total_documents": count,
        }
