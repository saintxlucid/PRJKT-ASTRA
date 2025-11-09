"""
Vector sliding implementation for chunk merging.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass

from astra.parse.pdf import LayoutChunk
from astra.embed.bge import BGEM3Embedder

@dataclass
class MergeCandidate:
    """A candidate pair of chunks for merging."""
    chunk1_idx: int
    chunk2_idx: int
    similarity: float

class VectorSlidingMerger:
    """Merge adjacent chunks based on vector similarity."""
    
    def __init__(
        self,
        embedder: BGEM3Embedder,
        similarity_threshold: float = 0.85,
        max_merge_size: int = 1500,
        context_window: int = 2
    ):
        """Initialize merger."""
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.max_merge_size = max_merge_size
        self.context_window = context_window
        
    def _compute_embeddings(
        self,
        chunks: List[LayoutChunk]
    ) -> np.ndarray:
        """Compute embeddings for chunks."""
        texts = [chunk.text for chunk in chunks]
        return self.embedder.embed_batch(texts)
        
    def _compute_similarities(
        self,
        embeddings: np.ndarray
    ) -> List[MergeCandidate]:
        """Find similar adjacent chunks."""
        candidates = []
        
        for i in range(len(embeddings) - 1):
            # Check next few chunks within context window
            for j in range(i + 1, min(i + 1 + self.context_window, len(embeddings))):
                # Compute cosine similarity
                similarity = np.dot(embeddings[i], embeddings[j])
                
                if similarity >= self.similarity_threshold:
                    candidates.append(MergeCandidate(
                        chunk1_idx=i,
                        chunk2_idx=j,
                        similarity=similarity
                    ))
                    
        return candidates
        
    def _merge_chunks(
        self,
        chunk1: LayoutChunk,
        chunk2: LayoutChunk
    ) -> LayoutChunk:
        """Merge two chunks."""
        # Combine text
        merged_text = chunk1.text + " " + chunk2.text
        
        # Update metadata
        merged_metadata = chunk1.metadata
        if chunk1.metadata.page == chunk2.metadata.page:
            # Update bbox to cover both chunks
            merged_metadata.bbox = (
                min(chunk1.metadata.bbox[0], chunk2.metadata.bbox[0]),
                min(chunk1.metadata.bbox[1], chunk2.metadata.bbox[1]),
                max(chunk1.metadata.bbox[2], chunk2.metadata.bbox[2]),
                max(chunk1.metadata.bbox[3], chunk2.metadata.bbox[3])
            )
            
        return LayoutChunk(
            text=merged_text,
            metadata=merged_metadata
        )
        
    def merge_chunks(
        self,
        chunks: List[LayoutChunk]
    ) -> List[LayoutChunk]:
        """Merge similar adjacent chunks."""
        if not chunks:
            return []
            
        # Compute embeddings
        embeddings = self._compute_embeddings(chunks)
        
        # Find merge candidates
        candidates = self._compute_similarities(embeddings)
        
        # Sort by similarity
        candidates.sort(key=lambda x: x.similarity, reverse=True)
        
        # Track merged chunks
        merged = set()
        result = chunks.copy()
        
        # Process candidates
        for candidate in candidates:
            # Skip if either chunk already merged
            if (candidate.chunk1_idx in merged or 
                candidate.chunk2_idx in merged):
                continue
                
            # Get chunks
            chunk1 = result[candidate.chunk1_idx]
            chunk2 = result[candidate.chunk2_idx]
            
            # Skip if merged would be too large
            if (len(chunk1.text) + len(chunk2.text) > 
                self.max_merge_size):
                continue
                
            # Skip if not on same/adjacent pages
            if abs(chunk1.metadata.page - chunk2.metadata.page) > 1:
                continue
                
            # Merge chunks
            merged_chunk = self._merge_chunks(chunk1, chunk2)
            
            # Update result
            result[candidate.chunk1_idx] = merged_chunk
            result[candidate.chunk2_idx] = None  # Mark as merged
            
            # Track merged chunks
            merged.add(candidate.chunk1_idx)
            merged.add(candidate.chunk2_idx)
            
        # Remove merged chunks
        return [chunk for chunk in result if chunk is not None]