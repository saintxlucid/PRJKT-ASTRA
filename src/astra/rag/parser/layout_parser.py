"""
Layout-aware document parser with hierarchical chunking and section tracking.

Provides intelligent parsing of documents with support for:
- Layout analysis (headings, sections, tables)
- Hierarchical chunking (section→para→sentence)
- Context stitching for adjacent chunks
- Metadata extraction and section graphs
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import re
from pathlib import Path
import hashlib
import structlog
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTPage, LTText, LTTextBoxHorizontal
import networkx as nx

logger = structlog.get_logger(__name__)

@dataclass
class BoundingBox:
    """Represents a bounding box in a document."""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    
    def overlaps(self, other: 'BoundingBox', threshold: float = 0.5) -> bool:
        """Check if this box overlaps with another."""
        if self.page != other.page:
            return False
            
        # Calculate intersection area
        x_left = max(self.x0, other.x0)
        y_bottom = max(self.y0, other.y0)
        x_right = min(self.x1, other.x1)
        y_top = min(self.y1, other.y1)
        
        if x_right < x_left or y_top < y_bottom:
            return False
            
        intersection = (x_right - x_left) * (y_top - y_bottom)
        self_area = (self.x1 - self.x0) * (self.y1 - self.y0)
        other_area = (other.x1 - other.x0) * (other.y1 - other.y0)
        
        overlap = intersection / min(self_area, other_area)
        return overlap >= threshold
        
    def distance_to(self, other: 'BoundingBox') -> float:
        """Calculate distance to another box."""
        if self.page != other.page:
            return float('inf')
            
        # Calculate center points
        self_center = ((self.x0 + self.x1)/2, (self.y0 + self.y1)/2)
        other_center = ((other.x0 + other.x1)/2, (other.y0 + other.y1)/2)
        
        # Euclidean distance between centers
        return ((self_center[0] - other_center[0])**2 + 
                (self_center[1] - other_center[1])**2)**0.5

@dataclass
class Chunk:
    """Represents a chunk of text with layout information."""
    text: str
    bbox: BoundingBox
    heading: Optional[str] = None
    section_id: Optional[str] = None
    chunk_type: str = "text"  # text, heading, table, etc.
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            
    def merge(self, other: 'Chunk') -> 'Chunk':
        """Merge this chunk with another."""
        return Chunk(
            text=f"{self.text}\n{other.text}",
            bbox=BoundingBox(
                min(self.bbox.x0, other.bbox.x0),
                min(self.bbox.y0, other.bbox.y0),
                max(self.bbox.x1, other.bbox.x1),
                max(self.bbox.y1, other.bbox.y1),
                self.bbox.page
            ),
            heading=self.heading or other.heading,
            section_id=self.section_id or other.section_id,
            chunk_type=self.chunk_type,
            metadata={**self.metadata, **other.metadata}
        )
        
    def get_fingerprint(self) -> str:
        """Generate a fingerprint for deduplication."""
        content = f"{self.text}{self.bbox.page}"
        return hashlib.sha256(content.encode()).hexdigest()

class LayoutParser:
    """Parser for extracting layout-aware chunks from documents."""
    
    def __init__(
        self,
        min_chunk_chars: int = 200,
        max_chunk_chars: int = 1000,
        overlap_chars: int = 50,
        heading_patterns: Optional[List[str]] = None
    ):
        """Initialize parser with config."""
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars
        self.heading_patterns = heading_patterns or [
            r"^#+\s+.*$",  # Markdown
            r"^.*:\s*$",   # Colon headers
            r"^[A-Z][^.!?]*$"  # Capitalized lines
        ]
        self.logger = logger.bind(component="layout_parser")
        
    def _is_heading(self, text: str) -> bool:
        """Check if text matches heading patterns."""
        text = text.strip()
        if not text:
            return False
            
        return any(
            re.match(pattern, text)
            for pattern in self.heading_patterns
        )
        
    def _get_section_id(
        self,
        heading: Optional[str],
        page: int,
        counter: Dict[str, int]
    ) -> str:
        """Generate unique section ID."""
        if not heading:
            counter["_default"] = counter.get("_default", 0) + 1
            return f"s{page}_{counter['_default']}"
            
        # Normalize heading
        section_key = re.sub(r'\W+', '_', heading.lower())
        counter[section_key] = counter.get(section_key, 0) + 1
        return f"{section_key}_{counter[section_key]}"
        
    def _detect_tables(
        self,
        elements: List[LTTextBoxHorizontal]
    ) -> List[BoundingBox]:
        """Detect table regions based on layout analysis."""
        table_regions = []
        
        # Group elements by vertical alignment
        y_sorted = sorted(elements, key=lambda e: -e.y0)
        current_row = []
        current_y = None
        rows = []
        
        for elem in y_sorted:
            if current_y is None:
                current_y = elem.y0
                current_row.append(elem)
            elif abs(elem.y0 - current_y) < 5:  # Same row
                current_row.append(elem)
            else:
                rows.append(current_row)
                current_row = [elem]
                current_y = elem.y0
                
        if current_row:
            rows.append(current_row)
            
        # Detect grid patterns
        for i in range(len(rows)-2):  # Need at least 3 rows
            row1, row2, row3 = rows[i:i+3]
            
            # Check for aligned columns
            if (len(row1) > 2 and
                len(row1) == len(row2) and
                all(abs(e1.x0 - e2.x0) < 5
                    for e1, e2 in zip(row1, row2))):
                    
                # Found table pattern
                table_regions.append(BoundingBox(
                    min(e.x0 for r in rows[i:i+3] for e in r),
                    min(e.y0 for r in rows[i:i+3] for e in r),
                    max(e.x1 for r in rows[i:i+3] for e in r),
                    max(e.y1 for r in rows[i:i+3] for e in r),
                    row1[0].pageid
                ))
                
        return table_regions
        
    def _should_merge_chunks(
        self,
        chunk1: Chunk,
        chunk2: Chunk,
        distance_threshold: float = 50
    ) -> bool:
        """Determine if chunks should be merged."""
        # Same section and close together
        if (chunk1.section_id == chunk2.section_id and
            chunk1.bbox.distance_to(chunk2.bbox) <= distance_threshold):
            return True
            
        # Overlapping boxes
        if chunk1.bbox.overlaps(chunk2.bbox):
            return True
            
        # Same heading and on same page
        if (chunk1.heading == chunk2.heading and
            chunk1.bbox.page == chunk2.bbox.page):
            return True
            
        return False
        
    def parse_document(
        self,
        file_path: str
    ) -> tuple[List[Chunk], nx.DiGraph]:
        """
        Parse document into chunks with section graph.
        
        Args:
            file_path: Path to document
            
        Returns:
            Tuple of (chunks, section_graph)
        """
        try:
            # Track sections and build graph
            section_graph = nx.DiGraph()
            current_section = None
            section_counter = {}
            
            chunks = []
            current_chunk = []
            current_bbox = None
            
            # Extract pages
            pages = list(extract_pages(file_path))
            
            for page_num, page in enumerate(pages):
                # Reset chunk at page boundary
                if current_chunk:
                    chunks.append(Chunk(
                        text="".join(current_chunk),
                        bbox=current_bbox,
                        heading=current_section,
                        section_id=self._get_section_id(
                            current_section, page_num,
                            section_counter
                        )
                    ))
                    current_chunk = []
                    current_bbox = None
                    
                # Get text elements
                elements = [
                    e for e in page._objs
                    if isinstance(e, LTTextBoxHorizontal)
                ]
                
                # Detect tables
                table_regions = self._detect_tables(elements)
                
                for element in elements:
                    text = element.get_text().strip()
                    if not text:
                        continue
                        
                    # Create bounding box
                    bbox = BoundingBox(
                        element.x0, element.y0,
                        element.x1, element.y1,
                        page_num
                    )
                    
                    # Check if in table
                    in_table = any(
                        r.overlaps(bbox)
                        for r in table_regions
                    )
                    
                    if in_table:
                        # Create table chunk
                        if current_chunk:
                            chunks.append(Chunk(
                                text="".join(current_chunk),
                                bbox=current_bbox,
                                heading=current_section,
                                section_id=self._get_section_id(
                                    current_section,
                                    page_num,
                                    section_counter
                                )
                            ))
                            current_chunk = []
                            current_bbox = None
                            
                        chunks.append(Chunk(
                            text=text,
                            bbox=bbox,
                            heading=current_section,
                            section_id=self._get_section_id(
                                current_section,
                                page_num,
                                section_counter
                            ),
                            chunk_type="table"
                        ))
                        continue
                        
                    # Check for heading
                    if self._is_heading(text):
                        # Create chunk from current content
                        if current_chunk:
                            chunks.append(Chunk(
                                text="".join(current_chunk),
                                bbox=current_bbox,
                                heading=current_section,
                                section_id=self._get_section_id(
                                    current_section,
                                    page_num,
                                    section_counter
                                )
                            ))
                            current_chunk = []
                            current_bbox = None
                            
                        # Update section tracking
                        prev_section = current_section
                        current_section = text
                        
                        if prev_section:
                            section_graph.add_edge(prev_section, current_section)
                            
                        # Create heading chunk
                        chunks.append(Chunk(
                            text=text,
                            bbox=bbox,
                            heading=current_section,
                            section_id=self._get_section_id(
                                current_section,
                                page_num,
                                section_counter
                            ),
                            chunk_type="heading"
                        ))
                        continue
                        
                    # Add to current chunk
                    current_chunk.append(text)
                    if current_bbox is None:
                        current_bbox = bbox
                    else:
                        current_bbox = BoundingBox(
                            min(current_bbox.x0, bbox.x0),
                            min(current_bbox.y0, bbox.y0),
                            max(current_bbox.x1, bbox.x1),
                            max(current_bbox.y1, bbox.y1),
                            page_num
                        )
                        
                    # Check chunk size
                    if len("".join(current_chunk)) >= self.max_chunk_chars:
                        chunks.append(Chunk(
                            text="".join(current_chunk),
                            bbox=current_bbox,
                            heading=current_section,
                            section_id=self._get_section_id(
                                current_section,
                                page_num,
                                section_counter
                            )
                        ))
                        
                        # Start new chunk with overlap
                        overlap_text = current_chunk[-1][-self.overlap_chars:]
                        current_chunk = [overlap_text]
                        current_bbox = bbox
                        
            # Add final chunk
            if current_chunk:
                chunks.append(Chunk(
                    text="".join(current_chunk),
                    bbox=current_bbox,
                    heading=current_section,
                    section_id=self._get_section_id(
                        current_section,
                        len(pages)-1,
                        section_counter
                    )
                ))
                
            # Merge adjacent chunks
            merged_chunks = []
            skip_indices = set()
            
            for i, chunk in enumerate(chunks):
                if i in skip_indices:
                    continue
                    
                current = chunk
                j = i + 1
                
                while j < len(chunks):
                    if j in skip_indices:
                        j += 1
                        continue
                        
                    if self._should_merge_chunks(current, chunks[j]):
                        current = current.merge(chunks[j])
                        skip_indices.add(j)
                        j += 1
                    else:
                        break
                        
                merged_chunks.append(current)
                
            return merged_chunks, section_graph
            
        except Exception as e:
            self.logger.error("parsing_failed",
                            file=file_path,
                            error=str(e))
            return [], nx.DiGraph()
            
    def stitch_context(
        self,
        chunks: List[Chunk],
        query: str,
        max_context_chunks: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Stitch together adjacent chunks for better context.
        
        Args:
            chunks: List of chunks to stitch
            query: Search query for relevance checking
            max_context_chunks: Max number of chunks to combine
            
        Returns:
            List of stitched chunks with citations
        """
        if not chunks:
            return []
            
        # Sort chunks by page and position
        chunks = sorted(
            chunks,
            key=lambda c: (c.bbox.page, c.bbox.y0)
        )
        
        results = []
        processed = set()
        
        for i, chunk in enumerate(chunks):
            if i in processed:
                continue
                
            # Find adjacent chunks to merge
            context_chunks = [chunk]
            current_len = len(chunk.text)
            
            # Look backward
            j = i - 1
            while (j >= 0 and
                   len(context_chunks) < max_context_chunks and
                   current_len < self.max_chunk_chars):
                if j not in processed and self._should_merge_chunks(
                    chunks[j], context_chunks[0]
                ):
                    context_chunks.insert(0, chunks[j])
                    current_len += len(chunks[j].text)
                    processed.add(j)
                j -= 1
                
            # Look forward
            j = i + 1
            while (j < len(chunks) and
                   len(context_chunks) < max_context_chunks and
                   current_len < self.max_chunk_chars):
                if j not in processed and self._should_merge_chunks(
                    context_chunks[-1], chunks[j]
                ):
                    context_chunks.append(chunks[j])
                    current_len += len(chunks[j].text)
                    processed.add(j)
                j += 1
                
            # Create stitched result
            if len(context_chunks) > 1:
                citations = []
                text_parts = []
                
                for c in context_chunks:
                    start_pos = len("".join(text_parts))
                    text_parts.append(c.text)
                    
                    citations.append({
                        "text": c.text,
                        "span": (start_pos, start_pos + len(c.text)),
                        "page": c.bbox.page,
                        "section": c.section_id,
                        "heading": c.heading
                    })
                    
                results.append({
                    "text": "".join(text_parts),
                    "citations": citations,
                    "metadata": {
                        "sections": list({
                            c.section_id for c in context_chunks
                        }),
                        "headings": list({
                            c.heading for c in context_chunks
                            if c.heading
                        })
                    }
                })
                
            else:
                # Single chunk
                results.append({
                    "text": chunk.text,
                    "citations": [{
                        "text": chunk.text,
                        "span": (0, len(chunk.text)),
                        "page": chunk.bbox.page,
                        "section": chunk.section_id,
                        "heading": chunk.heading
                    }],
                    "metadata": {
                        "sections": [chunk.section_id],
                        "headings": [chunk.heading] if chunk.heading else []
                    }
                })
                
        return results