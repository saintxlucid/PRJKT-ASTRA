"""
ASTRA Multi-RAG Memory Bridges
Bridges between Multi-RAG and memory systems.
"""
from typing import Dict, Any, List, Optional
import structlog
from dataclasses import dataclass

from astra.core.memory import MemoryLTMAdapter, MemoryEpisodicAdapter
from astra.rag.multi_rag_core import MultiRAGRetriever
from astra.rag.modules.events import EventBus

logger = structlog.get_logger()


@dataclass
class MemoryConfig:
    """Memory bridge configuration."""
    ltm_threshold: float = 0.6
    episodic_threshold: float = 0.7
    max_ltm_entries: int = 1000
    max_episodic_entries: int = 100


class MemoryBridge:
    """Bridge between Multi-RAG and memory systems."""
    
    def __init__(
        self,
        event_bus: EventBus,
        retriever: MultiRAGRetriever,
        config: Optional[MemoryConfig] = None
    ):
        self.event_bus = event_bus
        self.retriever = retriever
        self.config = config or MemoryConfig()
        
        # Initialize memory adapters
        self.ltm = MemoryLTMAdapter()
        self.episodic = MemoryEpisodicAdapter()
        
        # Register event handlers
        self._register_handlers()
        logger.info("memory_bridge_initialized")
    
    def _register_handlers(self) -> None:
        """Register memory-related event handlers."""
        self.event_bus.on("retrieval_complete", self._handle_retrieval)
        self.event_bus.on("answer_generated", self._handle_answer)
        logger.info("memory_handlers_registered")
    
    async def _handle_retrieval(self, event: Dict[str, Any]) -> None:
        """Handle retrieval events for memory integration."""
        query = event["query"]
        candidates = event["candidates"]
        
        # Check LTM threshold
        if candidates and candidates[0].score >= self.config.ltm_threshold:
            await self.ltm.store(
                query=query,
                context=candidates[0].content,
                metadata={
                    "score": candidates[0].score,
                    "doc_id": candidates[0].doc_id,
                    "category": candidates[0].category
                }
            )
            
        # Check episodic threshold
        if candidates and candidates[0].score >= self.config.episodic_threshold:
            await self.episodic.store(
                query=query,
                context=candidates[0].content,
                metadata={
                    "score": candidates[0].score,
                    "doc_id": candidates[0].doc_id,
                    "category": candidates[0].category
                }
            )
    
    async def _handle_answer(self, event: Dict[str, Any]) -> None:
        """Handle answer events for memory integration."""
        query = event["query"]
        answer = event["answer"]
        citations = event["citations"]
        
        # Store answer in episodic memory
        await self.episodic.store(
            query=query,
            context=answer,
            metadata={
                "citations": [c.doc_id for c in citations],
                "categories": list({c.category for c in citations}),
                "type": "answer"
            }
        )
    
    async def get_ltm_context(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant context from LTM."""
        results = await self.ltm.search(
            query=query,
            k=5
        )
        return results
    
    async def get_episodic_context(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant context from episodic memory."""
        results = await self.episodic.search(
            query=query,
            k=3
        )
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "ltm_entries": self.ltm.count(),
            "episodic_entries": self.episodic.count(),
            "ltm_threshold": self.config.ltm_threshold,
            "episodic_threshold": self.config.episodic_threshold
        }