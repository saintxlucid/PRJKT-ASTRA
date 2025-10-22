"""
Text chunking utilities optimized for PDF layout.

This module provides chunking strategies that respect PDF layout elements
like headings, columns, and natural visual boundaries.
"""
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass
import re
import structlog

from transformers import AutoTokenizer

from astra.parse.pdf import PDFChunk, BoundingBox

logger = structlog.get_logger()

@dataclass
class ChunkingConfig:
    """Configuration for layout-aware chunking."""
    target_size: int = 512  # Target chunk size in tokens
    min_size: int = 100     # Min chunk size to emit
    max_size: int = 800     # Max chunk size before forced split
    overlap: int = 50       # Overlap between chunks in tokens
    respect_headings: bool = True  # Don't split across headings
    tokenizer_name: str = "intfloat/multilingual-e5-small"  # Model for tokenization

class LayoutChunker:
    """Chunks text while preserving PDF layout information."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker with config."""
        self.config = config or ChunkingConfig()
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.tokenizer_name
        )

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using model tokenizer."""
        return len(self.tokenizer.encode(text))

    def _should_break_at(self, chunk: PDFChunk, next_chunk: PDFChunk) -> bool:
        """Determine if we should break between chunks."""
        # Always break at headings if configured
        if self.config.respect_headings and next_chunk.is_heading:
            return True
            
        # Break between non-overlapping chunks 
        if not chunk.bbox.overlaps(next_chunk.bbox):
            # Break if on different pages
            if chunk.bbox.page != next_chunk.bbox.page:
                return True
                
            # Break if significant vertical gap (new column/section)
            if (chunk.bbox.y0 - next_chunk.bbox.y1) > 20:
                return True

        return False

    def _merge_safely(self, chunks: List[PDFChunk]) -> PDFChunk:
        """Merge chunks while preserving layout ordering."""
        if not chunks:
            raise ValueError("No chunks to merge")
            
        # Sort by page then top-to-bottom
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (c.bbox.page, -c.bbox.y1)
        )
        
        # Merge bboxes and text
        result = sorted_chunks[0]
        for chunk in sorted_chunks[1:]:
            result = result.merge(chunk)
            
        return result

    def chunk_by_layout(
        self,
        chunks: List[PDFChunk],
        add_metadata: Optional[Dict[str, Any]] = None
    ) -> Iterator[PDFChunk]:
        """Chunk text respecting layout and size constraints.
        
        Args:
            chunks: List of PDFChunk objects
            add_metadata: Additional metadata to add to each chunk
            
        Yields:
            PDFChunk objects with size-optimized content
        """
        if not chunks:
            return

        # Sort by page and position
        chunks = sorted(chunks, key=lambda c: (c.bbox.page, -c.bbox.y1))
        
        current_chunks: List[PDFChunk] = []
        current_token_count = 0
        
        for i, chunk in enumerate(chunks):
            chunk_tokens = self._count_tokens(chunk.text)
            
            # Handle chunks larger than max_size
            if chunk_tokens > self.config.max_size:
                # First yield any accumulated chunks
                if current_chunks:
                    merged = self._merge_safely(current_chunks)
                    if add_metadata:
                        merged.metadata = {
                            **(merged.metadata or {}),
                            **add_metadata
                        }
                    yield merged
                    current_chunks = []
                    current_token_count = 0
                
                # Then split and yield large chunk
                # TODO: Implement smarter splitting of large chunks
                # For now just truncate
                text = chunk.text
                encoded = self.tokenizer.encode(text)
                decoded = self.tokenizer.decode(
                    encoded[:self.config.max_size]
                )
                yield PDFChunk(
                    text=decoded,
                    bbox=chunk.bbox,
                    is_heading=chunk.is_heading,
                    metadata={
                        **(chunk.metadata or {}),
                        **(add_metadata or {}),
                        "truncated": True
                    }
                )
                continue
            
            # Check if adding this chunk would exceed max_size
            if (current_token_count + chunk_tokens > self.config.max_size or
                (i < len(chunks)-1 and self._should_break_at(chunk, chunks[i+1]))):
                # Yield current chunks if we have enough tokens
                if current_token_count >= self.config.min_size:
                    merged = self._merge_safely(current_chunks)
                    if add_metadata:
                        merged.metadata = {
                            **(merged.metadata or {}),
                            **add_metadata
                        }
                    yield merged
                    current_chunks = []
                    current_token_count = 0
            
            # Add chunk to current group
            current_chunks.append(chunk)
            current_token_count += chunk_tokens
            
            # If we're at target size and next chunk would cause a break,
            # yield current group
            if (current_token_count >= self.config.target_size and
                i < len(chunks)-1 and 
                self._should_break_at(chunk, chunks[i+1])):
                merged = self._merge_safely(current_chunks)
                if add_metadata:
                    merged.metadata = {
                        **(merged.metadata or {}),
                        **add_metadata
                    }
                yield merged
                current_chunks = []
                current_token_count = 0

        # Yield any remaining chunks
        if current_chunks and current_token_count >= self.config.min_size:
            merged = self._merge_safely(current_chunks)
            if add_metadata:
                merged.metadata = {
                    **(merged.metadata or {}),
                    **add_metadata
                }
            yield merged