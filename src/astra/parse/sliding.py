"""
Vector-based sliding window merging for retrieved chunks.

This module provides utilities for merging semantically similar and 
adjacent chunks based on vector similarity and layout information.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import structlog

from astra.parse.pdf import PDFChunk, BoundingBox
from astra.embed.base import BaseEmbedder

logger = structlog.get_logger()

@dataclass
class SlidingConfig:
    """Configuration for vector-based chunk sliding."""
    sim_threshold: float = 0.85  # Cosine similarity threshold
    max_merge_tokens: int = 1200  # Max tokens after merging
    merge_stride: float = 0.3    # Required stride overlap (0-1)
    require_adjacent: bool = True # Only merge adjacent chunks

class VectorSlider:
    """Merges retrieved chunks based on vector similarity."""

    def __init__(
        self,
        embedder: BaseEmbedder,
        config: Optional[SlidingConfig] = None
    ):
        """Initialize slider with embedder and config.
        
        Args:
            embedder: Embedder for computing chunk vectors
            config: Optional sliding configuration
        """
        self.embedder = embedder
        self.config = config or SlidingConfig()
        
    def _compute_similarities(
        self, 
        chunks: List[PDFChunk]
    ) -> np.ndarray:
        """Compute pairwise similarities between chunks."""
        # Get embeddings for all chunks
        texts = [c.text for c in chunks]
        vectors = self.embedder.embed_documents(texts)
        
        # Compute pairwise cosine similarities
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normed = vectors / norms
        sims = np.dot(normed, normed.T)
        
        return sims

    def _can_merge(
        self,
        chunk1: PDFChunk,
        chunk2: PDFChunk,
        similarity: float
    ) -> bool:
        """Check if two chunks can be merged based on criteria."""
        # Check similarity threshold
        if similarity < self.config.sim_threshold:
            return False
            
        # Check if chunks are adjacent if required
        if self.config.require_adjacent:
            if chunk1.bbox.page != chunk2.bbox.page:
                return False
                
            # Allow merging if bboxes overlap or are very close
            bbox_gap = min(
                abs(chunk1.bbox.y0 - chunk2.bbox.y1),
                abs(chunk2.bbox.y0 - chunk1.bbox.y1)
            )
            if bbox_gap > 20:  # Max 20pt gap
                return False

        # Don't merge across headings
        if chunk2.is_heading:
            return False
            
        return True

    def merge_chunks(
        self,
        chunks: List[PDFChunk],
        tokenizer=None  # Optional tokenizer for length check
    ) -> List[PDFChunk]:
        """Merge similar and adjacent chunks.
        
        Args:
            chunks: List of chunks to potentially merge
            tokenizer: Optional tokenizer to check merged length
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return []
            
        if len(chunks) == 1:
            return chunks.copy()

        # Compute similarity matrix
        sims = self._compute_similarities(chunks)
        
        # Track which chunks have been merged
        merged = set()
        result: List[PDFChunk] = []
        
        for i in range(len(chunks)):
            if i in merged:
                continue
                
            current = chunks[i]
            to_merge = [current]
            
            # Look for chunks to merge with current
            for j in range(i + 1, len(chunks)):
                if j in merged:
                    continue
                    
                if self._can_merge(current, chunks[j], sims[i, j]):
                    candidate = chunks[j]
                    
                    # Check merged length if tokenizer provided
                    if tokenizer:
                        merged_text = "\n".join(c.text for c in to_merge + [candidate])
                        if len(tokenizer.encode(merged_text)) > self.config.max_merge_tokens:
                            continue
                    
                    to_merge.append(candidate)
                    merged.add(j)
            
            if len(to_merge) > 1:
                # Merge the chunks
                merged_chunk = to_merge[0]
                for other in to_merge[1:]:
                    merged_chunk = merged_chunk.merge(other)
                result.append(merged_chunk)
            else:
                # Keep chunk as-is
                result.append(current)
            
            merged.add(i)
        
        logger.info(
            "chunks_merged",
            input_chunks=len(chunks),
            output_chunks=len(result),
            merge_ratio=len(result)/len(chunks)
        )
        return result