"""
Layout-aware PDF parsing module.

This module provides utilities for extracting text from PDFs while preserving
layout information like page numbers, bounding boxes, and section headings.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, NamedTuple

def parse_pdf(path: str) -> List[PDFChunk]:
    """
    Parse a PDF file into layout-aware chunks.
    
    This is the main entry point for PDF parsing. It creates a PDFLayoutParser
    instance and uses it to extract chunks from the PDF.
    
    Args:
        path: Path to the PDF file to parse
        
    Returns:
        List of PDFChunk objects containing text and layout metadata
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF is encrypted or invalid
    """
    parser = PDFLayoutParser()
    chunks = parser.parse_pdf(path)
    return parser.merge_overlapping(chunks)
import os
from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass
import logging
import structlog

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTPage, LTTextContainer, LTTextBox, LTTextLine, LTChar
from pdfminer.layout import LTRect, LTFigure, LTImage, LTCurve
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

logger = structlog.get_logger()

@dataclass
class BoundingBox:
    """Represents a bounding box in PDF coordinates (bottom-left origin)."""
    x0: float
    y0: float  # Bottom
    x1: float
    y1: float  # Top
    page: int

    def area(self) -> float:
        """Get area of bounding box."""
        return (self.x1 - self.x0) * (self.y1 - self.y0)
    
    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this box overlaps with another on same page."""
        if self.page != other.page:
            return False
        return not (self.x1 < other.x0 or self.x0 > other.x1 or
                   self.y1 < other.y0 or self.y0 > other.y1)

    def merge(self, other: 'BoundingBox') -> 'BoundingBox':
        """Merge two overlapping boxes."""
        if self.page != other.page:
            raise ValueError("Cannot merge boxes from different pages")
        return BoundingBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
            page=self.page
        )

@dataclass
class PDFChunk:
    """A chunk of text from a PDF with layout metadata."""
    text: str
    bbox: BoundingBox
    is_heading: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def merge(self, other: 'PDFChunk') -> 'PDFChunk':
        """Merge this chunk with another, preserving layout."""
        return PDFChunk(
            text=f"{self.text}\n{other.text}",
            bbox=self.bbox.merge(other.bbox),
            is_heading=self.is_heading or other.is_heading,
            metadata={
                **(self.metadata or {}),
                **(other.metadata or {})
            }
        )

class PDFLayoutParser:
    """PDF parser that preserves layout information."""

    def __init__(self, min_heading_height: float = 14.0):
        """Initialize parser with heading detection parameters.
        
        Args:
            min_heading_height: Minimum font size to consider text a heading
        """
        self.min_heading_height = min_heading_height

    def _is_heading(self, text_obj: LTTextBox) -> bool:
        """Detect if a text block is likely a heading."""
        if not text_obj._objs:  # type: ignore
            return False
        
        # Get max font size in text block
        max_height = 0.0
        for line in text_obj._objs:  # type: ignore
            if isinstance(line, LTTextLine):
                for char in line._objs:  # type: ignore
                    if isinstance(char, LTChar):
                        max_height = max(max_height, char.size)
        
        # Check if any font size exceeds heading threshold
        return max_height >= self.min_heading_height

    def _extract_text(self, obj: LTTextContainer) -> str:
        """Extract clean text from a text container."""
        return obj.get_text().strip()

    def parse_pdf(self, path: str) -> List[PDFChunk]:
        """Parse PDF file into layout-aware chunks.
        
        Args:
            path: Path to PDF file
        
        Returns:
            List of PDFChunk objects with text and layout metadata
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF is encrypted or invalid
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF file not found: {path}")

        chunks: List[PDFChunk] = []
        
        try:
            # Extract pages and preserve layout
            for page_num, page in enumerate(extract_pages(path), start=1):
                if not isinstance(page, LTPage):
                    continue

                # Process text elements with layout
                for element in page:
                    if isinstance(element, LTTextBox):
                        text = self._extract_text(element)
                        if not text:
                            continue

                        # Create chunk with bounding box
                        chunk = PDFChunk(
                            text=text,
                            bbox=BoundingBox(
                                x0=element.x0,
                                y0=element.y0,
                                x1=element.x1,
                                y1=element.y1,
                                page=page_num
                            ),
                            is_heading=self._is_heading(element),
                            metadata={
                                "page": page_num,
                                "layout": "text"
                            }
                        )
                        chunks.append(chunk)

                    # Handle figures/images - mark their regions
                    elif isinstance(element, (LTFigure, LTImage)):
                        chunk = PDFChunk(
                            text="[FIGURE]",
                            bbox=BoundingBox(
                                x0=element.x0,
                                y0=element.y0,
                                x1=element.x1,
                                y1=element.y1,
                                page=page_num
                            ),
                            metadata={
                                "page": page_num,
                                "layout": "figure"
                            }
                        )
                        chunks.append(chunk)

            logger.info(
                "pdf_parsed",
                path=path,
                pages=max(c.bbox.page for c in chunks),
                chunks=len(chunks)
            )
            return chunks

        except Exception as e:
            logger.error("pdf_parse_failed", path=path, error=str(e))
            raise ValueError(f"Failed to parse PDF: {e}")

    def merge_overlapping(self, chunks: List[PDFChunk]) -> List[PDFChunk]:
        """Merge chunks with overlapping bounding boxes.
        
        Args:
            chunks: List of PDFChunk objects
            
        Returns:
            New list with overlapping chunks merged
        """
        if not chunks:
            return []

        # Sort by page then vertical position (top to bottom)
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (c.bbox.page, -c.bbox.y1)
        )

        merged: List[PDFChunk] = [sorted_chunks[0]]
        for chunk in sorted_chunks[1:]:
            last = merged[-1]
            if last.bbox.overlaps(chunk.bbox):
                merged[-1] = last.merge(chunk)
            else:
                merged.append(chunk)

        return merged