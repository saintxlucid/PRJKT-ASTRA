"""Tests for PDF parsing with layout awareness."""
import os
import pytest
from typing import List

from astra.parse.pdf import PDFLayoutParser, PDFChunk, BoundingBox

def test_bounding_box():
    """Test BoundingBox operations."""
    box1 = BoundingBox(x0=0, y0=0, x1=10, y1=10, page=1)
    box2 = BoundingBox(x0=5, y0=5, x1=15, y1=15, page=1)
    box3 = BoundingBox(x0=20, y0=20, x1=30, y1=30, page=1)
    box4 = BoundingBox(x0=0, y0=0, x1=10, y1=10, page=2)

    # Test area calculation
    assert box1.area() == 100

    # Test overlap detection
    assert box1.overlaps(box2)
    assert not box1.overlaps(box3)
    assert not box1.overlaps(box4)  # Different pages

    # Test merging
    merged = box1.merge(box2)
    assert merged.x0 == 0
    assert merged.y0 == 0
    assert merged.x1 == 15
    assert merged.y1 == 15

    # Test merge validation
    with pytest.raises(ValueError):
        box1.merge(box4)  # Can't merge across pages

def test_pdf_chunk():
    """Test PDFChunk operations."""
    bbox1 = BoundingBox(x0=0, y0=0, x1=10, y1=10, page=1)
    bbox2 = BoundingBox(x0=5, y0=5, x1=15, y1=15, page=1)
    
    chunk1 = PDFChunk(
        text="Hello",
        bbox=bbox1,
        is_heading=True,
        metadata={"key1": "value1"}
    )
    chunk2 = PDFChunk(
        text="World",
        bbox=bbox2,
        is_heading=False,
        metadata={"key2": "value2"}
    )

    # Test chunk merging
    merged = chunk1.merge(chunk2)
    assert merged.text == "Hello\nWorld"
    assert merged.is_heading is True  # Preserves heading status
    assert merged.metadata == {"key1": "value1", "key2": "value2"}
    assert merged.bbox.x0 == 0
    assert merged.bbox.x1 == 15

def test_parser_initialization():
    """Test parser initialization and config."""
    parser = PDFLayoutParser(min_heading_height=16.0)
    assert parser.min_heading_height == 16.0

def test_invalid_pdf():
    """Test handling of invalid PDF files."""
    parser = PDFLayoutParser()
    
    # Test nonexistent file
    with pytest.raises(FileNotFoundError):
        parser.parse_pdf("nonexistent.pdf")

# Skip live PDF tests if test file not available
TEST_PDF = os.path.join(
    os.path.dirname(__file__),
    "test_files",
    "sample.pdf"
)

@pytest.mark.skipif(not os.path.exists(TEST_PDF),
                   reason="Test PDF file not available")
def test_pdf_parsing():
    """Test parsing of actual PDF file."""
    parser = PDFLayoutParser()
    chunks = parser.parse_pdf(TEST_PDF)

    assert len(chunks) > 0
    for chunk in chunks:
        # Verify chunk structure
        assert isinstance(chunk, PDFChunk)
        assert chunk.text
        assert chunk.bbox.page > 0
        assert chunk.bbox.x0 <= chunk.bbox.x1
        assert chunk.bbox.y0 <= chunk.bbox.y1
        assert chunk.metadata
        assert "page" in chunk.metadata
        assert "layout" in chunk.metadata

def test_merge_overlapping():
    """Test merging of overlapping chunks."""
    parser = PDFLayoutParser()
    
    # Create test chunks
    chunks = [
        PDFChunk(
            text="Chunk 1",
            bbox=BoundingBox(0, 0, 10, 10, 1)
        ),
        PDFChunk(
            text="Chunk 2",
            bbox=BoundingBox(5, 5, 15, 15, 1)
        ),
        PDFChunk(
            text="Chunk 3",
            bbox=BoundingBox(20, 20, 30, 30, 1)
        )
    ]

    merged = parser.merge_overlapping(chunks)
    assert len(merged) == 2  # First two should merge