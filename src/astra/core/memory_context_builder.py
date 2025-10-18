"""
ASTRA Memory Context Builder

Builds conversation context by retrieving and formatting relevant memories.
Integrates with chat service to inject memory into LLM prompts.

Created: October 12, 2025
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import structlog

from src.astra.core.memory_engine import MemoryEngine, MemoryContext
from src.astra.core.identity_engine import IdentityEngine

logger = structlog.get_logger()


@dataclass
class ConversationContext:
    """Complete context for a conversation including identity and memories"""
    system_prompt: str
    memory_context: Optional[MemoryContext] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    metadata: Optional[Dict[str, Any]] = None


class MemoryContextBuilder:
    """
    Builds conversation context with identity and memories.
    
    This is the bridge between memory storage and conversation generation.
    """
    
    def __init__(
        self,
        identity_engine: Optional[IdentityEngine] = None,
        memory_engine: Optional[MemoryEngine] = None
    ):
        """
        Initialize context builder.
        
        Args:
            identity_engine: Identity engine instance
            memory_engine: Memory engine instance
        """
        self.identity_engine = identity_engine
        self.memory_engine = memory_engine
        
        logger.info("Memory context builder initialized")
    
    async def build_context(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        include_memory: bool = True,
        max_memories: int = 10,
        additional_context: Optional[str] = None
    ) -> ConversationContext:
        """
        Build complete conversation context.
        
        Args:
            user_message: Current user message
            conversation_id: Optional conversation ID for history
            include_memory: Whether to include memory retrieval
            max_memories: Maximum memories to retrieve
            additional_context: Optional additional context
        
        Returns:
            Complete conversation context
        """
        # Retrieve relevant memories
        memory_context = None
        if include_memory and self.memory_engine:
            try:
                memory_context = await self.memory_engine.search_memories(
                    query=user_message,
                    search_semantic=True,
                    search_episodic=True,
                    search_procedural=False,  # Only include if needed
                    max_total=max_memories
                )
                
                logger.debug(
                    "Retrieved memories for context",
                    total=memory_context.total_count,
                    semantic=memory_context.semantic_count,
                    episodic=memory_context.episodic_count
                )
                
            except Exception as e:
                logger.error(f"Failed to retrieve memories: {e}")
                memory_context = None
        
        # Generate system prompt with identity and memories
        memory_text = None
        if memory_context and memory_context.memories:
            memory_text = memory_context.formatted_context
        
        system_prompt = ""
        if self.identity_engine:
            try:
                system_prompt = self.identity_engine.generate_system_prompt(
                    memory_context=memory_text,
                    additional_context=additional_context
                )
            except Exception as e:
                logger.error(f"Failed to generate system prompt: {e}")
                system_prompt = self._default_system_prompt()
        else:
            system_prompt = self._default_system_prompt()
        
        return ConversationContext(
            system_prompt=system_prompt,
            memory_context=memory_context,
            metadata={
                "has_memories": memory_context is not None and len(memory_context.memories) > 0,
                "memory_count": len(memory_context.memories) if memory_context else 0,
                "conversation_id": conversation_id
            }
        )
    
    async def should_store_memory(
        self,
        user_message: str,
        assistant_response: str,
        conversation_id: str
    ) -> Dict[str, bool]:
        """
        Determine if this exchange should be stored in memory.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
            conversation_id: Conversation ID
        
        Returns:
            Dictionary indicating which memory types to store
        """
        # Use identity engine to check memory triggers
        should_store = {
            "semantic": False,
            "episodic": False,
            "procedural": False
        }
        
        if not self.identity_engine:
            return should_store
        
        # Check for semantic memory triggers
        semantic_keywords = [
            "prefer", "like", "remember", "always", "never",
            "my name is", "i am", "i work", "important to me"
        ]
        
        message_lower = user_message.lower()
        
        for keyword in semantic_keywords:
            if keyword in message_lower:
                should_store["semantic"] = True
                break
        
        # Check for episodic memory triggers
        episodic_keywords = [
            "just", "today", "yesterday", "last week",
            "milestone", "achieved", "completed", "finished"
        ]
        
        for keyword in episodic_keywords:
            if keyword in message_lower:
                should_store["episodic"] = True
                break
        
        # Check for procedural memory triggers
        procedural_keywords = [
            "workflow", "process", "steps", "always do",
            "whenever i", "routine", "habit"
        ]
        
        for keyword in procedural_keywords:
            if keyword in message_lower:
                should_store["procedural"] = True
                break
        
        logger.debug(
            "Memory storage decision",
            should_store=should_store,
            message_preview=user_message[:50]
        )
        
        return should_store
    
    async def store_exchange(
        self,
        user_message: str,
        assistant_response: str,
        conversation_id: str,
        force_semantic: bool = False,
        force_episodic: bool = False
    ) -> Dict[str, Optional[str]]:
        """
        Store conversation exchange in appropriate memory types.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
            conversation_id: Conversation ID
            force_semantic: Force semantic storage
            force_episodic: Force episodic storage
        
        Returns:
            Dictionary of stored memory IDs
        """
        stored_ids = {
            "semantic": None,
            "episodic": None
        }
        
        if not self.memory_engine:
            return stored_ids
        
        # Determine what to store
        should_store = await self.should_store_memory(
            user_message, assistant_response, conversation_id
        )
        
        # Store semantic memory (facts, preferences)
        if should_store["semantic"] or force_semantic:
            try:
                # Extract key information from exchange
                content = f"User: {user_message}\nASTRA: {assistant_response}"
                
                memory_id = await self.memory_engine.store_semantic(
                    content=content,
                    tags=["conversation", "preference"],
                    metadata={
                        "conversation_id": conversation_id,
                        "type": "exchange"
                    }
                )
                stored_ids["semantic"] = memory_id
                
                logger.info("Stored semantic memory", id=memory_id)
                
            except Exception as e:
                logger.error(f"Failed to store semantic memory: {e}")
        
        # Store episodic memory (events, moments)
        if should_store["episodic"] or force_episodic:
            try:
                # Create episode title and summary
                title = user_message[:50] + ("..." if len(user_message) > 50 else "")
                summary = f"{user_message}\n\nResponse: {assistant_response[:100]}"
                
                memory_id = await self.memory_engine.store_episodic(
                    title=title,
                    summary=summary,
                    tags=["conversation", conversation_id]
                )
                stored_ids["episodic"] = memory_id
                
                logger.info("Stored episodic memory", id=memory_id)
                
            except Exception as e:
                logger.error(f"Failed to store episodic memory: {e}")
        
        return stored_ids
    
    def _default_system_prompt(self) -> str:
        """Fallback system prompt if identity engine not available"""
        return """You are ASTRA (Advanced Structured Testing and Reasoning Assistant).
You are thoughtful, precise, and helpful. You run entirely locally with no cloud dependencies.

Respond directly and clearly, breaking down complex topics into digestible steps."""


# Global context builder instance
_context_builder: Optional[MemoryContextBuilder] = None


def get_context_builder(
    identity_engine: Optional[IdentityEngine] = None,
    memory_engine: Optional[MemoryEngine] = None
) -> MemoryContextBuilder:
    """
    Get global context builder instance.
    
    Returns:
        Global context builder
    """
    global _context_builder
    
    if _context_builder is None:
        _context_builder = MemoryContextBuilder(
            identity_engine=identity_engine,
            memory_engine=memory_engine
        )
    
    return _context_builder


# Integration example for chat service
async def example_chat_integration():
    """
    Example showing how to integrate with chat service.
    
    This demonstrates the typical flow:
    1. Build context with memories
    2. Send to LLM
    3. Store important exchanges
    """
    from src.astra.core.identity_engine import get_identity_engine
    from src.astra.core.memory_engine import get_memory_engine
    
    # Initialize engines
    identity_engine = get_identity_engine()
    memory_engine = get_memory_engine()
    
    # Create context builder
    builder = MemoryContextBuilder(identity_engine, memory_engine)
    
    # User sends message
    user_message = "What's my preferred communication style?"
    conversation_id = "conv_123"
    
    # Build context with memories
    context = await builder.build_context(
        user_message=user_message,
        conversation_id=conversation_id,
        include_memory=True
    )
    
    print(f"System Prompt (first 200 chars):\n{context.system_prompt[:200]}...\n")
    print(f"Memories Retrieved: {context.metadata['memory_count']}")
    
    if context.memory_context:
        print(f"\nMemory Context:\n{context.memory_context.formatted_context}\n")
    
    # Simulate LLM response
    assistant_response = "You prefer direct, concise answers with stepwise clarity."
    
    # Store if important
    stored = await builder.store_exchange(
        user_message=user_message,
        assistant_response=assistant_response,
        conversation_id=conversation_id,
        force_semantic=True  # Force because this is about preferences
    )
    
    print(f"Stored Memory IDs: {stored}")


if __name__ == "__main__":
    import asyncio
    
    print("\n" + "="*80)
    print("ASTRA MEMORY CONTEXT BUILDER - EXAMPLE")
    print("="*80 + "\n")
    
    asyncio.run(example_chat_integration())
    
    print("\n" + "="*80)
