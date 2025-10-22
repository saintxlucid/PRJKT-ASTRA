"""Tests for vector-based chunk sliding."""
import pytest
import numpy as np
from typing import List
from unittest.mock import Mock, patch

from astra.parse.pdf import PDFChunk, BoundingBox
from astra.parse.sliding import VectorSlider, SlidingConfig
from astra.embed.base import BaseEmbedder

class MockEmbedder(BaseEmbedder):
    """Mock embedder for testing."""
    def __init__(self):
        self.embed_count = 0
        
    def embed_documents(self, texts: List[str]) -> np.ndarray:
        self.embed_count += 1
        # Return mock embeddings - similar for adjacent texts
        vecs = []
        for i, text in enumerate(texts):
            # Make adjacent chunks have similar vectors
            vec = np.zeros(3)
            vec[i % 3] = 1.0
            vecs.append(vec)
        return np.array(vecs)

    def embed_query(self, text: str) -> np.ndarray:
        return np.zeros(3)

def create_test_chunk(
    text: str,
    y_pos: float,
    page: int = 1,
    is_heading: bool = False
) -> PDFChunk:
    """Helper to create test chunks."""
    return PDFChunk(
        text=text,
        bbox=BoundingBox(0, y_pos, 100, y_pos + 10, page),
        is_heading=is_heading
    )

def test_slider_initialization():
    """Test slider initialization."""
    embedder = MockEmbedder()
    config = SlidingConfig(
        sim_threshold=0.9,
        max_merge_tokens=1000
    )
    slider = VectorSlider(embedder, config)
    assert slider.config == config
    assert slider.embedder == embedder

def test_empty_chunks():
    """Test handling of empty input."""
    slider = VectorSlider(MockEmbedder())
    result = slider.merge_chunks([])
    assert len(result) == 0

def test_single_chunk():
    """Test handling of single chunk."""
    chunk = create_test_chunk("Single chunk", 100)
    slider = VectorSlider(MockEmbedder())
    result = slider.merge_chunks([chunk])
    assert len(result) == 1
    assert result[0] == chunk

def test_merge_adjacent():
    """Test merging of adjacent chunks."""
    chunks = [
        create_test_chunk("First chunk", 100),
        create_test_chunk("Second chunk", 90),  # Adjacent
        create_test_chunk("Third chunk", 50)    # Gap too large
    ]
    
    slider = VectorSlider(MockEmbedder())
    result = slider.merge_chunks(chunks)
    
    # First two should merge, third separate
    assert len(result) == 2

def test_respect_headings():
    """Test that chunks don't merge across headings."""
    chunks = [
        create_test_chunk("First chunk", 100),
        create_test_chunk("Heading", 90, is_heading=True),
        create_test_chunk("After heading", 80)
    ]
    
    slider = VectorSlider(MockEmbedder())
    result = slider.merge_chunks(chunks)
    
    # Should not merge across heading
    assert len(result) == 3

def test_page_boundaries():
    """Test handling of page boundaries."""
    chunks = [
        create_test_chunk("Page 1 end", 10, page=1),
        create_test_chunk("Page 2 start", 100, page=2)
    ]
    
    slider = VectorSlider(MockEmbedder())
    result = slider.merge_chunks(chunks)
    
    # Should not merge across pages
    assert len(result) == 2

def test_similarity_threshold():
    """Test similarity threshold enforcement."""
    chunks = [
        create_test_chunk("Chunk 1", 100),
        create_test_chunk("Chunk 2", 90)
    ]
    
    # Set high similarity threshold
    config = SlidingConfig(sim_threshold=0.99)
    slider = VectorSlider(MockEmbedder(), config)
    result = slider.merge_chunks(chunks)
    
    # Should not merge due to high threshold
    assert len(result) == 2

def test_max_tokens():
    """Test max token limit."""
    chunks = [
        create_test_chunk("A" * 1000, 100),  # Long chunk
        create_test_chunk("B" * 1000, 90)    # Another long chunk
    ]
    
    # Mock tokenizer that returns simple length
    mock_tokenizer = Mock()
    mock_tokenizer.encode = lambda x: [0] * len(x)
    
    slider = VectorSlider(
        MockEmbedder(),
        SlidingConfig(max_merge_tokens=1500)
    )
    result = slider.merge_chunks(chunks, tokenizer=mock_tokenizer)
    
    # Should not merge due to length
    assert len(result) == 2

def test_embedding_called():
    """Test that embedder is called correctly."""
    chunks = [
        create_test_chunk("Chunk 1", 100),
        create_test_chunk("Chunk 2", 90)
    ]
    
    embedder = MockEmbedder()
    slider = VectorSlider(embedder)
    slider.merge_chunks(chunks)
    
    # Should have called embed_documents once
    assert embedder.embed_count == 1