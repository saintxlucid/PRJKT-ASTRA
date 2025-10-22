"""Tests for layout-aware text chunking."""
import pytest
from typing import List, Iterator

from astra.parse.pdf import PDFChunk, BoundingBox
from astra.parse.chunking import LayoutChunker, ChunkingConfig

def create_test_chunk(text: str, y_pos: float, page: int = 1, 
                     is_heading: bool = False) -> PDFChunk:
    """Helper to create test chunks."""
    return PDFChunk(
        text=text,
        bbox=BoundingBox(0, y_pos, 100, y_pos + 10, page),
        is_heading=is_heading
    )

def test_chunking_config():
    """Test chunking configuration."""
    config = ChunkingConfig(
        target_size=256,
        min_size=50,
        max_size=400,
        overlap=25
    )
    assert config.target_size == 256
    assert config.min_size == 50
    assert config.max_size == 400
    assert config.overlap == 25

def test_chunker_initialization():
    """Test chunker initialization."""
    config = ChunkingConfig()
    chunker = LayoutChunker(config)
    assert chunker.config == config
    assert chunker.tokenizer is not None

def test_empty_chunks():
    """Test handling of empty input."""
    chunker = LayoutChunker()
    result = list(chunker.chunk_by_layout([]))
    assert len(result) == 0

def test_basic_chunking():
    """Test basic chunking functionality."""
    chunks = [
        create_test_chunk("First chunk", 100),
        create_test_chunk("Second chunk", 80),
        create_test_chunk("Third chunk", 60)
    ]

    chunker = LayoutChunker(ChunkingConfig(
        target_size=100,
        min_size=10,
        max_size=200
    ))

    result = list(chunker.chunk_by_layout(chunks))
    assert len(result) > 0
    for chunk in result:
        assert isinstance(chunk, PDFChunk)
        assert chunk.text

def test_heading_breaks():
    """Test that chunks break at headings when configured."""
    chunks = [
        create_test_chunk("Regular text", 100),
        create_test_chunk("Heading text", 80, is_heading=True),
        create_test_chunk("More regular text", 60)
    ]

    # Test with heading respect enabled
    config = ChunkingConfig(
        target_size=1000,  # Large enough to fit all in one chunk
        respect_headings=True
    )
    chunker = LayoutChunker(config)
    result = list(chunker.chunk_by_layout(chunks))
    assert len(result) >= 2  # Should break at heading

    # Test with heading respect disabled
    config.respect_headings = False
    chunker = LayoutChunker(config)
    result = list(chunker.chunk_by_layout(chunks))
    assert len(result) == 1  # Should combine all chunks

def test_page_breaks():
    """Test that chunks break between pages."""
    chunks = [
        create_test_chunk("Page 1 text", 100, page=1),
        create_test_chunk("Page 2 text", 100, page=2)
    ]

    chunker = LayoutChunker(ChunkingConfig(
        target_size=1000  # Large enough to fit all in one chunk
    ))
    result = list(chunker.chunk_by_layout(chunks))
    assert len(result) == 2  # Should break between pages

def test_size_constraints():
    """Test chunk size constraints are respected."""
    # Create a chunk larger than max_size
    large_chunk = create_test_chunk("A" * 2000, 100)  # Very large text
    
    config = ChunkingConfig(
        target_size=100,
        min_size=50,
        max_size=200
    )
    chunker = LayoutChunker(config)
    
    result = list(chunker.chunk_by_layout([large_chunk]))
    for chunk in result:
        # Verify no chunk exceeds max_size in tokens
        token_count = len(chunker.tokenizer.encode(chunk.text))
        assert token_count <= config.max_size

def test_metadata_preservation():
    """Test that metadata is preserved and merged correctly."""
    chunks = [
        create_test_chunk("Text with metadata", 100)
    ]
    chunks[0].metadata = {"key": "value"}

    chunker = LayoutChunker()
    additional_metadata = {"source": "test"}
    result = list(chunker.chunk_by_layout(
        chunks, 
        add_metadata=additional_metadata
    ))

    assert len(result) > 0
    for chunk in result:
        assert chunk.metadata
        assert chunk.metadata["key"] == "value"
        assert chunk.metadata["source"] == "test"