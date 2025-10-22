"""
Layout-aware text parsing with section graphs and context stitching.

This module provides functionality for:
1. Layout-aware text chunking with bounding boxes
2. Section graph building and navigation
3. Smart chunk stitching based on layout
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import re
from pathlib import Path
import json
import numpy as np
import structlog
from networkx import DiGraph, shortest_path

logger = structlog.get_logger(__name__)

@dataclass
class BoundingBox:
    """2D bounding box with page coordinates."""
    page: int
    x1: float  # Left
    y1: float  # Top
    x2: float  # Right
    y2: float  # Bottom
    
    def intersection(self, other: 'BoundingBox') -> float:
        """Calculate intersection area with another bbox."""
        if self.page != other.page:
            return 0.0
            
        x_left = max(self.x1, other.x1)
        y_top = max(self.y1, other.y1)
        x_right = min(self.x2, other.x2)
        y_bottom = min(self.y2, other.y2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
            
        return (x_right - x_left) * (y_bottom - y_top)
        
    def union(self, other: 'BoundingBox') -> float:
        """Calculate union area with another bbox."""
        if self.page != other.page:
            return self.area + other.area
            
        area1 = self.area
        area2 = other.area
        return area1 + area2 - self.intersection(other)
        
    @property
    def area(self) -> float:
        """Calculate bbox area."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)
        
    def iou(self, other: 'BoundingBox') -> float:
        """Calculate Intersection over Union with another bbox."""
        union = self.union(other)
        if union == 0:
            return 0.0
        return self.intersection(other) / union
        
    @staticmethod
    def from_dict(data: Dict) -> 'BoundingBox':
        """Create BoundingBox from dict."""
        return BoundingBox(
            page=data["page"],
            x1=data["x1"],
            y1=data["y1"], 
            x2=data["x2"],
            y2=data["y2"]
        )
        
@dataclass
class TextChunk:
    """Layout-aware text chunk with metadata."""
    # Core content
    text: str
    bbox: BoundingBox
    
    # Layout metadata
    page: int = field(init=False)
    heading: bool = False
    is_table: bool = False
    section_id: Optional[str] = None
    section_path: List[str] = field(default_factory=list)
    
    # Source tracking
    doc_id: Optional[str] = None
    source_file: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    
    # Layout relationships
    next_id: Optional[str] = None
    prev_id: Optional[str] = None
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set page from bbox."""
        self.page = self.bbox.page
        
    @property
    def id(self) -> str:
        """Generate unique chunk ID."""
        if self.doc_id and self.char_start is not None:
            return f"{self.doc_id}_{self.char_start}"
        return f"chunk_{id(self)}"
        
    def to_dict(self) -> Dict:
        """Convert to dict for serialization."""
        return {
            "text": self.text,
            "bbox": {
                "page": self.bbox.page,
                "x1": self.bbox.x1,
                "y1": self.bbox.y1,
                "x2": self.bbox.x2,
                "y2": self.bbox.y2
            },
            "heading": self.heading,
            "is_table": self.is_table,
            "section_id": self.section_id,
            "section_path": self.section_path,
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "next_id": self.next_id,
            "prev_id": self.prev_id,
            "parent_id": self.parent_id,
            "children": self.children
        }
        
    @staticmethod
    def from_dict(data: Dict) -> 'TextChunk':
        """Create TextChunk from dict."""
        bbox = BoundingBox.from_dict(data["bbox"])
        return TextChunk(
            text=data["text"],
            bbox=bbox,
            heading=data.get("heading", False),
            is_table=data.get("is_table", False),
            section_id=data.get("section_id"),
            section_path=data.get("section_path", []),
            doc_id=data.get("doc_id"),
            source_file=data.get("source_file"),
            char_start=data.get("char_start"),
            char_end=data.get("char_end"),
            next_id=data.get("next_id"),
            prev_id=data.get("prev_id"),
            parent_id=data.get("parent_id"),
            children=data.get("children", [])
        )

class LayoutParser:
    """Parser for layout-aware text chunking and section analysis."""
    
    def __init__(
        self,
        heading_patterns: Optional[List[str]] = None,
        min_chunk_len: int = 20,
        max_chunk_len: int = 2000,
        overlap: int = 100
    ):
        """Initialize parser.
        
        Args:
            heading_patterns: Regex patterns for heading detection
            min_chunk_len: Minimum chunk length in chars
            max_chunk_len: Maximum chunk length in chars
            overlap: Overlap between chunks in chars
        """
        self.logger = logger.bind(component="layout_parser")
        
        # Default heading patterns
        if heading_patterns is None:
            heading_patterns = [
                r"^#+\s+.*$",  # Markdown headings
                r"^[A-Z][^.!?]*(?:[.!?]|$)",  # Capitalized sentence
                r"^\d+(?:\.\d+)*\s+[A-Z].*$",  # Numbered sections
            ]
        self.heading_patterns = [
            re.compile(p) for p in heading_patterns
        ]
        
        self.min_chunk_len = min_chunk_len
        self.max_chunk_len = max_chunk_len
        self.overlap = overlap
        
        # Section tracking
        self.section_graph = DiGraph()
        self.current_section = None
        self.section_stack = []
        
    def is_heading(self, text: str) -> bool:
        """Check if text matches heading patterns."""
        text = text.strip()
        if not text:
            return False
            
        return any(
            p.match(text) is not None
            for p in self.heading_patterns
        )
        
    def get_section_id(self, heading: str) -> str:
        """Generate section ID from heading text."""
        # Clean and normalize heading
        heading = re.sub(r'[^\w\s-]', '', heading.lower())
        heading = re.sub(r'[-\s]+', '-', heading).strip('-')
        
        # Add numeric prefix for uniqueness
        count = sum(1 for n in self.section_graph.nodes
                   if n.startswith(heading))
        if count > 0:
            heading = f"{heading}-{count}"
            
        return heading
        
    def update_section_graph(
        self,
        section_id: str,
        heading: str
    ) -> None:
        """Update section hierarchy graph."""
        if not self.section_graph.has_node(section_id):
            self.section_graph.add_node(
                section_id,
                heading=heading
            )
            
        # Connect to parent section
        if self.current_section:
            self.section_graph.add_edge(
                self.current_section,
                section_id
            )
            
    def split_text(
        self,
        text: str,
        bbox: BoundingBox
    ) -> List[TextChunk]:
        """Split text into chunks with layout metadata."""
        chunks = []
        
        # Split into lines
        lines = text.split('\n')
        current_chunk = []
        current_len = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for heading
            is_heading = self.is_heading(line)
            if is_heading:
                # Create new section
                section_id = self.get_section_id(line)
                self.update_section_graph(section_id, line)
                
                # Emit current chunk if any
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(
                        TextChunk(
                            text=chunk_text,
                            bbox=bbox,
                            heading=False,
                            section_id=self.current_section,
                            section_path=self.section_stack.copy()
                        )
                    )
                    current_chunk = []
                    current_len = 0
                    
                # Add heading chunk
                chunks.append(
                    TextChunk(
                        text=line,
                        bbox=bbox,
                        heading=True,
                        section_id=section_id,
                        section_path=self.section_stack.copy()
                    )
                )
                
                # Update section state
                self.current_section = section_id
                self.section_stack.append(section_id)
                continue
                
            # Add line to current chunk
            line_len = len(line)
            if current_len + line_len > self.max_chunk_len:
                # Emit current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        bbox=bbox,
                        heading=False,
                        section_id=self.current_section,
                        section_path=self.section_stack.copy()
                    )
                )
                
                # Start new chunk with overlap
                overlap_tokens = current_chunk[-3:]
                current_chunk = overlap_tokens + [line]
                current_len = sum(len(t) for t in current_chunk)
            else:
                current_chunk.append(line)
                current_len += line_len
                
        # Emit final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    bbox=bbox,
                    heading=False,
                    section_id=self.current_section,
                    section_path=self.section_stack.copy()
                )
            )
            
        return chunks
        
    def are_adjacent(
        self,
        chunk1: TextChunk,
        chunk2: TextChunk,
        iou_threshold: float = 0.3,
        y_gap_threshold: float = 20
    ) -> bool:
        """Check if two chunks are adjacent in layout."""
        # Must be same page
        if chunk1.page != chunk2.page:
            return False
            
        # Check vertical adjacency
        y_gap = abs(chunk2.bbox.y1 - chunk1.bbox.y2)
        if y_gap > y_gap_threshold:
            return False
            
        # Check horizontal overlap
        bbox1 = BoundingBox(
            page=chunk1.page,
            x1=chunk1.bbox.x1,
            y1=0,
            x2=chunk1.bbox.x2,
            y2=1
        )
        bbox2 = BoundingBox(
            page=chunk2.page,
            x1=chunk2.bbox.x1,
            y1=0,
            x2=chunk2.bbox.x2, 
            y2=1
        )
        
        iou = bbox1.iou(bbox2)
        return iou >= iou_threshold
        
    def merge_chunks(
        self,
        chunk1: TextChunk,
        chunk2: TextChunk
    ) -> TextChunk:
        """Merge two adjacent chunks."""
        # Combine text with space
        merged_text = chunk1.text + ' ' + chunk2.text
        
        # Merge bounding boxes
        merged_bbox = BoundingBox(
            page=chunk1.page,
            x1=min(chunk1.bbox.x1, chunk2.bbox.x1),
            y1=min(chunk1.bbox.y1, chunk2.bbox.y1),
            x2=max(chunk1.bbox.x2, chunk2.bbox.x2),
            y2=max(chunk1.bbox.y2, chunk2.bbox.y2)
        )
        
        # Create merged chunk
        return TextChunk(
            text=merged_text,
            bbox=merged_bbox,
            heading=chunk1.heading or chunk2.heading,
            section_id=chunk1.section_id,
            section_path=chunk1.section_path,
            doc_id=chunk1.doc_id,
            source_file=chunk1.source_file,
            char_start=chunk1.char_start,
            char_end=chunk2.char_end,
            prev_id=chunk1.prev_id,
            next_id=chunk2.next_id
        )
        
    def get_section_path(
        self,
        section_id: str
    ) -> List[str]:
        """Get full path from root to section."""
        if not section_id or not self.section_graph.has_node(section_id):
            return []
            
        # Find root node
        roots = [n for n in self.section_graph.nodes
                if not list(self.section_graph.predecessors(n))]
        if not roots:
            return [section_id]
            
        # Get path from root
        try:
            path = shortest_path(
                self.section_graph,
                roots[0],
                section_id
            )
            return path
        except:
            return [section_id]
            
    def reset(self):
        """Reset parser state."""
        self.section_graph.clear()
        self.current_section = None
        self.section_stack = []