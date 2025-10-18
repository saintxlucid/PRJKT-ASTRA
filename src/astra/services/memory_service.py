"""
Memory service.

Manages semantic memory storage and retrieval using vector store.
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from astra.infrastructure.storage.vector_store import VectorStore
from astra.utils.logging import LoggerMixin


class MemoryService(LoggerMixin):
    """
    Service for managing semantic memory.

    Stores conversation context in vector store for retrieval.
    """

    def __init__(self, vector_store: VectorStore):
        """
        Initialize memory service.

        Args:
            vector_store: Vector store instance
        """
        self.vector_store = vector_store

    def store_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        message_id: Optional[int] = None,
    ) -> str:
        """
        Store a message in semantic memory.

        Args:
            conversation_id: UUID of the conversation
            role: Message role (system, user, assistant)
            content: Message content
            message_id: Optional database message ID

        Returns:
            memory_id: UUID of the stored memory

        Raises:
            MemoryQueryError: If storage fails
        """
        memory_id = str(uuid4())

        metadata = {
            "conversation_id": conversation_id,
            "role": role,
        }

        if message_id is not None:
            metadata["message_id"] = str(message_id)

        self.vector_store.add_memory(
            text=content,
            memory_id=memory_id,
            metadata=metadata,
        )

        self.logger.debug(
            "message_stored_in_memory",
            memory_id=memory_id,
            conversation_id=conversation_id,
            role=role,
        )

        return memory_id

    def search_relevant_context(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Search for relevant context from memory.

        Args:
            query: Search query text
            conversation_id: Optional filter to search within specific conversation
            top_k: Number of results to return
            similarity_threshold: Optional threshold to filter results (0-1, lower is more similar)

        Returns:
            List of relevant memory chunks with text and metadata

        Raises:
            MemoryQueryError: If search fails
        """
        # Build filter
        filter_metadata = None
        if conversation_id:
            filter_metadata = {"conversation_id": conversation_id}

        # Search memories
        memories = self.vector_store.search_memories(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )

        # Apply similarity threshold if provided
        if similarity_threshold is not None:
            memories = [m for m in memories if m.get("distance", 1.0) <= similarity_threshold]

        self.logger.debug(
            "context_search_completed",
            query_length=len(query),
            results=len(memories),
            conversation_id=conversation_id,
        )

        return memories

    def delete_conversation_memory(self, conversation_id: str):
        """
        Delete all memories for a conversation.

        Args:
            conversation_id: UUID of the conversation

        Raises:
            MemoryQueryError: If deletion fails
        """
        self.vector_store.delete_by_metadata({"conversation_id": conversation_id})

        self.logger.info(
            "conversation_memory_deleted",
            conversation_id=conversation_id,
        )

    def get_memory_stats(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory stats
        """
        count = self.vector_store.get_memory_count()

        return {
            "total_memories": count,
            "collection_name": self.vector_store.collection_name,
            "embedding_model": self.vector_store.embedding_model.get_sentence_embedding_dimension(),
        }
