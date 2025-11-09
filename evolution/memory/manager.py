"""Memory-aware planning system with retrieval and citation validation.

Provides:
- Memory-augmented planning
- Citation validation
- Retrieval-enhanced prompting
- Memory coherence checks
- Source verification
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
import numpy as np
import torch
from ..core.schema import PlanSchema, CitationSchema
from ..core.validation import ValidationResult


class MemorySource(Enum):
    """Sources of memory entries."""
    CONVERSATION = "conversation"  # Chat history
    TOOL_USE = "tool_use"         # Tool usage records
    DOCUMENT = "document"         # External documents
    CODE = "code"                 # Code snippets
    PLAN = "plan"                # Previous plans


@dataclass
class MemoryEntry:
    """Individual memory entry with metadata."""
    content: str
    source: MemorySource
    timestamp: datetime
    embedding: np.ndarray
    metadata: Dict[str, str]
    citation_key: str  # Unique identifier for citations


@dataclass
class Citation:
    """Citation linking memory to plan."""
    key: str  # Citation key
    context: str  # Relevant excerpt
    confidence: float  # Match confidence
    verified: bool  # Whether citation is verified


@dataclass
class PlanMetadata:
    """Metadata for memory-aware plans."""
    citations: List[Citation]
    memory_keys: List[str]
    coherence_score: float
    verification_status: Dict[str, bool]


class MemoryManager:
    """Manages memory storage and retrieval."""
    
    def __init__(
        self,
        embedding_dim: int = 768,
        max_memories: int = 10000,
        min_confidence: float = 0.7
    ):
        """Initialize memory manager.
        
        Args:
            embedding_dim: Dimension of memory embeddings
            max_memories: Maximum number of memories to store
            min_confidence: Minimum confidence for matches
        """
        self.embedding_dim = embedding_dim
        self.max_memories = max_memories
        self.min_confidence = min_confidence
        
        # Memory storage
        self.memories: Dict[str, MemoryEntry] = {}
        self.memory_embeddings = np.zeros((0, embedding_dim))
        
    def add_memory(
        self,
        content: str,
        source: MemorySource,
        metadata: Optional[Dict[str, str]] = None,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """Add a new memory entry.
        
        Args:
            content: Memory content
            source: Source type
            metadata: Optional metadata
            embedding: Optional pre-computed embedding
            
        Returns:
            Citation key for the memory
        """
        # Generate embedding if not provided
        if embedding is None:
            embedding = self._embed_text(content)
            
        # Create memory entry
        entry = MemoryEntry(
            content=content,
            source=source,
            timestamp=datetime.now(),
            embedding=embedding,
            metadata=metadata or {},
            citation_key=self._generate_citation_key(content)
        )
        
        # Store memory
        self.memories[entry.citation_key] = entry
        self.memory_embeddings = np.vstack([
            self.memory_embeddings,
            embedding[np.newaxis, :]
        ])
        
        # Prune if needed
        if len(self.memories) > self.max_memories:
            self._prune_memories()
            
        return entry.citation_key
        
    def retrieve_relevant(
        self,
        query: str,
        k: int = 5,
        source_filter: Optional[Set[MemorySource]] = None
    ) -> List[Tuple[MemoryEntry, float]]:
        """Retrieve relevant memories for a query.
        
        Args:
            query: Search query
            k: Number of results to return
            source_filter: Optional filter for memory sources
            
        Returns:
            List of (memory, similarity) tuples
        """
        # Get query embedding
        query_embedding = self._embed_text(query)
        
        # Calculate similarities
        similarities = self.memory_embeddings @ query_embedding
        
        # Get top matches
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        # Filter by source if needed
        results = []
        for idx in top_indices:
            memory = list(self.memories.values())[idx]
            if source_filter and memory.source not in source_filter:
                continue
                
            similarity = similarities[idx]
            if similarity >= self.min_confidence:
                results.append((memory, float(similarity)))
                
        return results
        
    def verify_citations(
        self,
        citations: List[Citation]
    ) -> Dict[str, ValidationResult]:
        """Verify citations against stored memories.
        
        Args:
            citations: List of citations to verify
            
        Returns:
            Dict mapping citation keys to validation results
        """
        results = {}
        for citation in citations:
            # Get original memory
            memory = self.memories.get(citation.key)
            if not memory:
                results[citation.key] = ValidationResult(
                    valid=False,
                    message="Citation not found in memory"
                )
                continue
                
            # Verify context matches
            similarity = self._compute_similarity(
                citation.context,
                memory.content
            )
            
            if similarity >= self.min_confidence:
                results[citation.key] = ValidationResult(
                    valid=True,
                    message="Citation verified"
                )
            else:
                results[citation.key] = ValidationResult(
                    valid=False,
                    message=f"Context mismatch (similarity: {similarity:.2f})"
                )
                
        return results
        
    def _embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text.
        
        Override this in subclasses to use specific embedding model.
        Default uses random projection as placeholder.
        """
        # Simple random projection (replace with actual embedding model)
        rng = np.random.RandomState(hash(text) % 2**32)
        embedding = rng.randn(self.embedding_dim)
        return embedding / np.linalg.norm(embedding)
        
    def _generate_citation_key(self, content: str) -> str:
        """Generate unique citation key for content."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]
        
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity between two texts."""
        emb1 = self._embed_text(text1)
        emb2 = self._embed_text(text2)
        return float(emb1 @ emb2)
        
    def _prune_memories(self) -> None:
        """Remove oldest memories when over capacity."""
        # Sort by timestamp
        sorted_memories = sorted(
            self.memories.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Keep only most recent
        to_keep = sorted_memories[-self.max_memories:]
        self.memories = dict(to_keep)
        
        # Update embeddings
        self.memory_embeddings = np.stack([
            m.embedding for m in self.memories.values()
        ])