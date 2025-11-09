"""
ASTRA OS - Phase 3: Memory System (Stub for Integration)

Minimal memory system implementation for Phase 10 integration testing.
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class MemoryType(Enum):
    """Types of memories"""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


@dataclass
class Memory:
    """A stored memory"""
    memory_id: str
    content: str
    memory_type: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0


class MemorySystem:
    """Simple memory system for integration"""
    
    def __init__(self):
        self.memories: dict[str, Memory] = {}
        self._id_counter = 0
    
    def store(self, content: str, memory_type: str, metadata: dict) -> str:
        """Store a memory"""
        self._id_counter += 1
        memory_id = f"mem_{self._id_counter}"
        
        # Simple embedding (hash-based for testing)
        embedding = [hash(content) % 100 / 100.0 for _ in range(128)]
        
        memory = Memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            metadata=metadata
        )
        
        self.memories[memory_id] = memory
        return memory_id
    
    def retrieve_similar(self, query_embedding: list[float], top_k: int = 5) -> list[Memory]:
        """Retrieve similar memories"""
        # Simple retrieval - just return recent memories
        memories = list(self.memories.values())
        return memories[-top_k:]
    
    def memory_count(self) -> int:
        """Get total memory count"""
        return len(self.memories)


# Global singleton
_memory_system: MemorySystem | None = None


def get_memory_system() -> MemorySystem:
    """Get global memory system"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system
