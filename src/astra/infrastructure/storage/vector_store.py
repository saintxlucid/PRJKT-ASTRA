"""
Vector store implementation using ChromaDB.

This module provides semantic memory storage and retrieval.
"""

from __future__ import annotations

from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from astra.utils.errors import MemoryConnectionError, MemoryQueryError
from astra.utils.logging import LoggerMixin


class VectorStore(LoggerMixin):
    """
    Vector store for semantic memory using ChromaDB.

    Stores text embeddings and enables semantic search.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "astra_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        distance_metric: str = "cosine",
    ):
        """
        Initialize vector store.

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_model: Sentence-transformers model name
            distance_metric: Distance metric (cosine, l2, ip)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.distance_metric = distance_metric
        self.embedding_model_name = embedding_model  # Store for potential rebuild

        try:
            # Initialize embedding model
            self.logger.info("loading_embedding_model", model=embedding_model)
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
            except PermissionError as perm_err:
                # ONNX cache permission error - fallback to CPU-only mode
                self.logger.warning(
                    "onnx_permission_error_fallback_to_cpu",
                    error=str(perm_err),
                    model=embedding_model,
                )
                # Force pure PyTorch mode without ONNX optimization
                self.embedding_model = SentenceTransformer(
                    embedding_model, device="cpu", model_kwargs={"use_auth_token": False}
                )

            # Initialize ChromaDB
            self.logger.info("initializing_chromadb", path=persist_directory)
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": distance_metric},
            )

            self.logger.info(
                "vector_store_initialized",
                collection=collection_name,
                count=self.collection.count(),
            )

        except Exception as e:
            self.logger.error("vector_store_initialization_failed", error=str(e))
            raise MemoryConnectionError(f"Failed to initialize vector store: {e}") from e

    def add_memory(
        self,
        text: str,
        memory_id: str,
        metadata: Optional[dict] = None,
    ):
        """
        Add a memory to the vector store.

        Args:
            text: Text content to store
            memory_id: Unique identifier for this memory
            metadata: Optional metadata (conversation_id, role, timestamp, etc.)

        Raises:
            MemoryQueryError: If adding memory fails
        """
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(text, convert_to_numpy=True).tolist()

            # Add to collection
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )

            self.logger.debug(
                "memory_added",
                memory_id=memory_id,
                text_length=len(text),
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error("add_memory_failed", memory_id=memory_id, error=str(e))
            raise MemoryQueryError(f"Failed to add memory: {e}") from e

    def search_memories(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search for relevant memories.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"conversation_id": "123"})

        Returns:
            List of memory dictionaries with keys: id, text, distance, metadata

        Raises:
            MemoryQueryError: If search fails
        """
        try:
            # Generate query embedding
            try:
                query_embedding = self.embedding_model.encode(query, convert_to_numpy=True).tolist()
            except PermissionError as perm_err:
                # ONNX cache permission error during search - rebuild model without ONNX
                self.logger.warning(
                    "onnx_permission_error_during_search_rebuilding_model",
                    error=str(perm_err),
                )
                # Reinitialize embedding model in CPU-only mode
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(self.embedding_model_name, device="cpu")
                # Retry embed
                query_embedding = self.embedding_model.encode(query, convert_to_numpy=True).tolist()

            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
            )

            # Format results
            memories = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    memory = {
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }
                    memories.append(memory)

            self.logger.debug(
                "memory_search_completed",
                query_length=len(query),
                results_count=len(memories),
                top_k=top_k,
            )

            return memories

        except Exception as e:
            self.logger.error("search_memories_failed", query=query, error=str(e))
            raise MemoryQueryError(f"Failed to search memories: {e}") from e

    def delete_memory(self, memory_id: str):
        """
        Delete a memory from the vector store.

        Args:
            memory_id: ID of the memory to delete

        Raises:
            MemoryQueryError: If deletion fails
        """
        try:
            self.collection.delete(ids=[memory_id])
            self.logger.debug("memory_deleted", memory_id=memory_id)

        except Exception as e:
            self.logger.error("delete_memory_failed", memory_id=memory_id, error=str(e))
            raise MemoryQueryError(f"Failed to delete memory: {e}") from e

    def delete_by_metadata(self, filter_metadata: dict):
        """
        Delete memories by metadata filter.

        Args:
            filter_metadata: Metadata filter (e.g., {"conversation_id": "123"})

        Raises:
            MemoryQueryError: If deletion fails
        """
        try:
            # Query to get IDs matching filter
            results = self.collection.get(where=filter_metadata)

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                self.logger.info(
                    "memories_deleted_by_metadata",
                    count=len(results["ids"]),
                    filter=filter_metadata,
                )

        except Exception as e:
            self.logger.error(
                "delete_by_metadata_failed",
                filter=filter_metadata,
                error=str(e),
            )
            raise MemoryQueryError(f"Failed to delete by metadata: {e}") from e

    def get_memory_count(self) -> int:
        """
        Get total number of memories.

        Returns:
            Number of memories in the store
        """
        return self.collection.count()

    def clear_all(self):
        """
        Clear all memories from the collection.

        Warning: This deletes all data!
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self.distance_metric},
            )
            self.logger.warning("vector_store_cleared")

        except Exception as e:
            self.logger.error("clear_all_failed", error=str(e))
            raise MemoryQueryError(f"Failed to clear vector store: {e}") from e
