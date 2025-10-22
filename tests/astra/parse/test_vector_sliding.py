"""
Tests for vector sliding chunk merger.
"""
import pytest
import numpy as np
from unittest.mock import Mock

from astra.parse.pdf import PDFChunk, BoundingBox
from astra.parse.sliding import VectorSlider, SlidingConfig
from astra.embed.bge import BGEM3Embedder

def create_test_chunks():
    """Create test chunks for merging."""
    return [
        PDFChunk(
            text="First chunk with some content.",
            bbox=BoundingBox(
                page=1,
                                    x0=10, y0=10, x1=50, y1=30
            ),
            is_heading=True
        ),
        PDFChunk(
            text="Second chunk with related content.",
            bbox=BoundingBox(
                page=1,
                                    x0=10, y0=45, x1=50, y1=65
            ),
            is_heading=False
        ),
        PDFChunk(
            text="Third chunk on a different topic.",
            bbox=BoundingBox(
                page=1,
                                    x0=10, y0=90, x1=50, y1=110
            ),
            is_heading=True
        )
    ]

def test_vector_sliding_merge():
    """Test basic merge functionality."""
    # Create mock embedder
    embedder = Mock(spec=BGEM3Embedder)
    
    # Configure mock to return similar vectors for first two chunks
    embedder.embed_documents.return_value = np.array([
        [1.0, 0.0],  # First chunk
        [0.9, 0.1],  # Second chunk (similar to first)
        [0.0, 1.0]   # Third chunk (different)
    ])
    
    # Create merger
    merger = VectorSlider(
        embedder=embedder,
        config=SlidingConfig(
            sim_threshold=0.8,
            max_merge_tokens=1000
        )
    )
    
    # Get test chunks
    chunks = create_test_chunks()
    
    # Merge chunks
    merged = merger.merge_chunks(chunks)
    
    # Verify results
    assert len(merged) == 2  # First two chunks should merge
    
    # Check merged chunk
    assert "First chunk" in merged[0].text
    assert "Second chunk" in merged[0].text
    
    # Check bbox merging
    # Check bbox merging - should span from top of first to bottom of second chunk
    assert merged[0].bbox.x0 == 10
    assert merged[0].bbox.y0 == 10
    assert merged[0].bbox.x1 == 50
    assert merged[0].bbox.y1 == 65
    
    # Check unmerged chunk
    assert merged[1].text == chunks[2].text

def test_similarity_threshold():
    """Test similarity threshold behavior."""
    embedder = Mock(spec=BGEM3Embedder)
    chunks = create_test_chunks()
    
    # Test with high threshold
    merger_high = VectorSlider(
        embedder=embedder,
        config=SlidingConfig(
            sim_threshold=0.99  # Very high
        )
    )
    
    embedder.embed_documents.return_value = np.array([
        [1.0, 0.0],
        [0.98, np.sqrt(1 - 0.98**2)],  # Similarity is 0.98
        [0.0, 1.0]
    ])
    
    merged_high = merger_high.merge_chunks(chunks)
    assert len(merged_high) == 3  # No merging
    
    # Test with low threshold
    merger_low = VectorSlider(
        embedder=embedder,
        config=SlidingConfig(
            sim_threshold=0.5  # Very low
        )
    )
    
    merged_low = merger_low.merge_chunks(chunks)
    assert len(merged_low) < 3  # Should merge some chunks

def test_max_merge_size():
    """Test maximum merge size limit."""
    embedder = Mock(spec=BGEM3Embedder)
    
    # Create chunks with long text
    long_chunks = [
        PDFChunk(
            text="a" * 800,  # Long text
            bbox=BoundingBox(
                page=1,
                                    x0=0, y0=0, x1=10, y1=10
            ),
            is_heading=False
        ),
        PDFChunk(
            text="a" * 800,  # Long text
            bbox=BoundingBox(
                page=1,
                                    x0=0, y0=15, x1=10, y1=25
            ),
            is_heading=False
        )
    ]
    
    # Configure embedder to return similar vectors
    embedder.embed_documents.return_value = np.array([
        [1.0, 0.0],
        [0.9, 0.1]  # Similar to first
    ])

    # Create mock tokenizer that returns 1000 tokens for each chunk
    tokenizer = Mock()
    def encode_mock(text):
        # Return number of 'a' chars, simulating the token count
        return [1] * len(text)  # Each 'a' is one token
    tokenizer.encode = encode_mock
    
    # Create merger with small max size
    merger = VectorSlider(
        embedder=embedder,
        config=SlidingConfig(
            sim_threshold=0.8,
            max_merge_tokens=1000  # Smaller than combined chunks
        )
    )
    
    # Attempt merge
    merged = merger.merge_chunks(long_chunks, tokenizer=tokenizer)
    assert len(merged) == 2  # Should not merge due to size

def test_context_window():
    """Test context window behavior."""
    embedder = Mock(spec=BGEM3Embedder)
    
    # Create 4 chunks
    chunks = create_test_chunks() + [
        PDFChunk(
            text="Fourth chunk.",
            bbox=BoundingBox(
                page=1,
                                    x0=10, y0=85, x1=50, y1=95
            ),
            is_heading=True
        )
    ]
    
    # Make all chunks similar
    embedder.embed_documents.return_value = np.array([
        [1.0, 0.0],
        [0.9, 0.1],
        [0.9, 0.1],
        [0.9, 0.1]
    ])
    
    # Test with small context window
    merger = VectorSlider(
        embedder=embedder,
        config=SlidingConfig(
            sim_threshold=0.8,
            merge_stride=0.3,  # Only merge if there's sufficient overlap
            require_adjacent=True  # Only look at adjacent chunks
        )
    )
    
    merged = merger.merge_chunks(chunks)
    
    # Should only merge adjacent pairs
    assert len(merged) < len(chunks)
    assert len(merged) > 1  # But not all chunks