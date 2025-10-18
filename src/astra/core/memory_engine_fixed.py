"""
ASTRA Memory Engine

Unified orchestration of all memory types:
- Semantic: Facts, preferences, knowledge (ChromaDB)
- Episodic: Timeline of events and experiences (SQLite)
- Procedural: Learned workflows and patterns (SQLite)

Provides intelligent memory retrieval and context building.

Created: October 12, 2025
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)
"""

from __future__ import annotations

import os
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class MemoryResult:
    """A single memory retrieval result"""
    memory_type: str  # "semantic", "episodic", "procedural"
    content: str
    relevance_score: float
    timestamp: Optional[float] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MemoryContext:
    """Assembled memory context for a conversation"""
    memories: List[MemoryResult]
    total_count: int
    formatted_context: str
    
    @property
    def semantic_count(self) -> int:
        return sum(1 for m in self.memories if m.memory_type == "semantic")
    
    @property
    def episodic_count(self) -> int:
        return sum(1 for m in self.memories if m.memory_type == "episodic")
    
    @property
    def procedural_count(self) -> int:
        return sum(1 for m in self.memories if m.memory_type == "procedural")


class MemoryEngine:
    """
    Unified memory orchestrator for ASTRA.
    
    Coordinates semantic, episodic, and procedural memory systems
    to provide intelligent context for conversations.
    """
    
    def __init__(
        self,
        vector_store=None,
        database_path: Optional[Path] = None,
        memory_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize memory engine.
        
        Args:
            vector_store: VectorStore instance for semantic memory
            database_path: Path to SQLite database for episodic/procedural
            memory_config: Memory retrieval configuration
        """
        self.vector_store = vector_store
        self.database_path = database_path or Path("data/astra.db")
        self.memory_config = memory_config or self._default_config()
        
        # Initialize LTM if available
        self.ltm = None
        try:
            # Try to import and use the existing LTM system
            from astra_local.backend.astra.cognition.ltm import LTM
            if self.database_path:
                os.environ["SQLITE_PATH"] = str(self.database_path)
            self.ltm = LTM()
            logger.info("LTM system initialized", database=str(self.database_path))
        except ImportError:
            logger.warning("LTM module not available, using basic memory")
        
        logger.info("Memory engine initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default memory configuration"""
        return {
            "semantic_search": {
                "top_k": 6,
                "similarity_threshold": 0.75,
                "boost_recent": 0.2
            },
            "episodic_recall": {
                "max_episodes": 3,
                "time_decay": 0.1
            },
            "procedural_match": {
                "pattern_threshold": 0.80,
                "max_workflows": 2
            }
        }
    
    async def search_memories(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        max_semantic: int = 6,
        max_episodic: int = 3,
        max_procedural: int = 2
    ) -> MemoryContext:
        """
        Search across all memory types and assemble context.
        
        Args:
            query: Search query
            conversation_id: Optional conversation ID for context
            max_semantic: Maximum semantic memories to return
            max_episodic: Maximum episodic memories to return
            max_procedural: Maximum procedural memories to return
        
        Returns:
            Assembled memory context
        """
        all_memories: List[MemoryResult] = []
        
        # Search semantic memory (facts, preferences, knowledge)
        if self.ltm:
            semantic_results = await self._search_semantic(query, max_semantic)
            all_memories.extend(semantic_results)
        elif self.vector_store:
            # Fall back to vector store if LTM not available
            semantic_results = await self._search_vector_store(query, max_semantic)
            all_memories.extend(semantic_results)
        
        # Search episodic memory (events, experiences)
        if self.ltm:
            episodic_results = await self._search_episodic(query, max_episodic)
            all_memories.extend(episodic_results)
        
        # Search procedural memory (workflows, patterns)
        if self.ltm:
            procedural_results = await self._search_procedural(query, max_procedural)
            all_memories.extend(procedural_results)
        
        # Sort by relevance and limit
        all_memories.sort(key=lambda m: m.relevance_score, reverse=True)
        max_total = max_semantic + max_episodic + max_procedural
        top_memories = all_memories[:max_total]
        
        # Format context
        formatted = self._format_memory_context(top_memories)
        
        return MemoryContext(
            memories=top_memories,
            total_count=len(all_memories),
            formatted_context=formatted
        )
    
    def retrieve_memories(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        max_semantic: int = 6,
        max_episodic: int = 3,
        max_procedural: int = 2
    ) -> MemoryContext:
        """
        Synchronous wrapper for search_memories.
        Allows MemoryBridge to query without async/await.
        
        Args:
            query: Search query
            conversation_id: Optional conversation ID for context
            max_semantic: Maximum semantic memories to return
            max_episodic: Maximum episodic memories to return
            max_procedural: Maximum procedural memories to return
        
        Returns:
            Assembled memory context
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, create new loop in thread
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.search_memories(
                query=query,
                conversation_id=conversation_id,
                max_semantic=max_semantic,
                max_episodic=max_episodic,
                max_procedural=max_procedural
            )
        )
    
    async def _search_semantic(self, query: str, top_k: int = 6) -> List[MemoryResult]:
        """Search semantic memory using LTM"""
        if not self.ltm:
            return []
        
        config = self.memory_config.get("semantic_search", {})
        threshold = config.get("similarity_threshold", 0.75)
        
        try:
            results = self.ltm.search_semantic(query, topk=top_k)
            
            memories = []
            for result in results:
                # Filter by threshold
                score = result.get("score")
                if score is not None and score < threshold:
                    continue
                
                memories.append(MemoryResult(
                    memory_type="semantic",
                    content=result.get("text", ""),
                    relevance_score=score or 0.0,
                    tags=[],
                    metadata=result.get("meta", {})
                ))
            
            logger.debug(f"Found {len(memories)} semantic memories for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching semantic memory: {e}")
            return []
    
    async def _search_vector_store(self, query: str, top_k: int = 6) -> List[MemoryResult]:
        """Search vector store directly (fallback)"""
        if not self.vector_store:
            return []
        
        config = self.memory_config.get("semantic_search", {})
        threshold = config.get("similarity_threshold", 0.75)
        
        try:
            # Use synchronous search_memories method
            results = self.vector_store.search_memories(
                query=query,
                top_k=top_k
            )
            
            memories = []
            for result in results:
                # Extract data from result dict
                content = result.get("document", result.get("text", ""))
                distance = result.get("distance", 1.0)
                score = 1.0 - distance  # Convert distance to similarity
                
                if score < threshold:
                    continue
                
                memories.append(MemoryResult(
                    memory_type="semantic",
                    content=content,
                    relevance_score=score,
                    tags=[],
                    metadata=result.get("metadata", {})
                ))
            
            logger.debug(f"Found {len(memories)} vector store memories")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    async def _search_episodic(self, query: str, max_episodes: int = 3) -> List[MemoryResult]:
        """Search episodic memory using LTM"""
        if not self.ltm:
            return []
        
        config = self.memory_config.get("episodic_recall", {})
        
        try:
            # Get recent timeline entries
            results = self.ltm.timeline(limit=max_episodes * 2)
            
            # Filter and score by keywords
            keywords = set(query.lower().split()[:5])
            memories = []
            
            for result in results:
                title = result.get("title", "").lower()
                summary = result.get("summary", "").lower()
                content_text = f"{title} {summary}"
                
                # Calculate keyword overlap
                content_words = set(content_text.split())
                overlap = len(keywords & content_words)
                
                if overlap == 0:
                    continue
                
                # Calculate relevance based on recency and match
                timestamp = result.get("ts", 0)
                age_hours = (time.time() - timestamp) / 3600
                recency_score = max(0, 1.0 - (age_hours * config.get("time_decay", 0.1)))
                match_score = overlap / len(keywords) if keywords else 0.0
                final_score = (recency_score * 0.4) + (match_score * 0.6)
                
                memories.append(MemoryResult(
                    memory_type="episodic",
                    content=f"{result.get('title', 'Memory')}: {result.get('summary', '')}",
                    relevance_score=final_score,
                    timestamp=float(timestamp),
                    tags=result.get("tags", [])
                ))
            
            # Sort and limit
            memories.sort(key=lambda m: m.relevance_score, reverse=True)
            memories = memories[:max_episodes]
            
            logger.debug(f"Found {len(memories)} episodic memories")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching episodic memory: {e}")
            return []
    
    async def _search_procedural(self, query: str, max_workflows: int = 2) -> List[MemoryResult]:
        """Search procedural memory using LTM"""
        if not self.ltm:
            return []
        
        try:
            # Try to get specific procedure by name
            result = self.ltm.get_procedure(query)
            memories = []
            
            if result:
                memories.append(MemoryResult(
                    memory_type="procedural",
                    content=f"Workflow: {query}",
                    relevance_score=0.9,
                    tags=["procedure"],
                    metadata={"script": result}
                ))
            
            logger.debug(f"Found {len(memories)} procedural memories")
            return memories
            
        except Exception as e:
            logger.error(f"Error searching procedural memory: {e}")
            return []
    
    def _format_memory_context(self, memories: List[MemoryResult]) -> str:
        """Format memories into context string for LLM"""
        if not memories:
            return "No relevant memories found."
        
        sections = {
            "semantic": [],
            "episodic": [],
            "procedural": []
        }
        
        # Group by type
        for memory in memories:
            sections[memory.memory_type].append(memory)
        
        # Build formatted context
        parts = []
        
        if sections["semantic"]:
            parts.append("SEMANTIC MEMORY (Facts & Knowledge):")
            for i, mem in enumerate(sections["semantic"], 1):
                parts.append(f"  {i}. {mem.content}")
        
        if sections["episodic"]:
            parts.append("\nEPISODIC MEMORY (Past Experiences):")
            for i, mem in enumerate(sections["episodic"], 1):
                time_str = ""
                if mem.timestamp:
                    dt = datetime.fromtimestamp(mem.timestamp)
                    time_str = f" ({dt.strftime('%Y-%m-%d')})"
                parts.append(f"  {i}. {mem.content}{time_str}")
        
        if sections["procedural"]:
            parts.append("\nPROCEDURAL MEMORY (Known Workflows):")
            for i, mem in enumerate(sections["procedural"], 1):
                parts.append(f"  {i}. {mem.content}")
        
        return "\n".join(parts)
    
    async def store_semantic(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store a semantic memory (fact, preference, knowledge).
        
        Args:
            content: Memory content
            tags: Optional tags for categorization
            metadata: Optional additional metadata
        
        Returns:
            Memory ID if successful
        """
        if self.ltm:
            try:
                memory_id = self.ltm.save_semantic(
                    text=content,
                    tags=tags or [],
                    meta=metadata or {}
                )
                logger.info("Semantic memory stored", id=memory_id, tags=tags)
                return memory_id
            except Exception as e:
                logger.error(f"Error storing semantic memory: {e}")
                return None
        
        # Fall back to vector store
        if self.vector_store:
            try:
                memory_id = self.vector_store.add_memory(
                    text=content,
                    memory_id=None,
                    metadata={
                        "tags": tags or [],
                        **(metadata or {})
                    }
                )
                logger.info("Semantic memory stored in vector store", id=memory_id)
                return memory_id
            except Exception as e:
                logger.error(f"Error storing in vector store: {e}")
                return None
        
        return None
    
    async def store_episodic(
        self,
        title: str,
        summary: str,
        tags: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        Store an episodic memory (event, experience).
        
        Args:
            title: Event title
            summary: Event summary
            tags: Optional tags
        
        Returns:
            Memory ID if successful
        """
        if not self.ltm:
            return None
        
        try:
            memory_id = self.ltm.save_episode(
                title=title,
                summary=summary,
                tags=tags or []
            )
            logger.info("Episodic memory stored", id=memory_id, title=title)
            return memory_id
        except Exception as e:
            logger.error(f"Error storing episodic memory: {e}")
            return None
    
    def get_memory_stats(self) -> Dict[str, int]:
        """
        Get memory statistics.

        Returns:
            Dictionary with counts of each memory type
        """
        counts = {"semantic": 0, "episodic": 0, "procedural": 0}

        if not self.ltm:
            if self.vector_store:
                try:
                    counts["semantic"] = int(self.vector_store.get_memory_count())
                except Exception as exc:
                    logger.error(f"Error getting vector store stats: {exc}")
            return counts

        try:
            count_memories = getattr(self.ltm, "count_memories", None)
            if callable(count_memories):
                raw_counts = count_memories()
                if isinstance(raw_counts, dict):
                    for key in counts:
                        value = raw_counts.get(key)
                        counts[key] = int(value) if isinstance(value, int) else counts[key]
                    return counts

            # Manual fallback for legacy LTM implementations
            if getattr(self.ltm, "semantic", None) is not None:
                try:
                    counts["semantic"] = int(self.ltm.semantic.count())
                except Exception as chroma_exc:
                    logger.debug(f"Error counting semantic memories: {chroma_exc}")

            sqlite_conn = getattr(self.ltm, "cx", None)
            if sqlite_conn is not None:
                try:
                    cursor = sqlite_conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM episodic")
                    episodic_count = cursor.fetchone()
                    counts["episodic"] = int(episodic_count[0]) if episodic_count else 0
                    cursor.execute("SELECT COUNT(*) FROM procedural")
                    procedural_count = cursor.fetchone()
                    counts["procedural"] = int(procedural_count[0]) if procedural_count else 0
                except Exception as sqlite_exc:
                    logger.debug(f"Error counting sqlite memories: {sqlite_exc}")

            return counts
        except Exception as exc:
            logger.error(f"Error getting memory stats: {exc}")
            return counts


# Global memory engine instance
_memory_engine: Optional[MemoryEngine] = None


def get_memory_engine(
    vector_store=None,
    database_path: Optional[Path] = None,
    memory_config: Optional[Dict[str, Any]] = None
) -> MemoryEngine:
    """
    Get global memory engine instance (singleton pattern).
    
    Returns:
        Global memory engine
    """
    global _memory_engine
    
    if _memory_engine is None:
        _memory_engine = MemoryEngine(
            vector_store=vector_store,
            database_path=database_path,
            memory_config=memory_config
        )
    
    return _memory_engine
