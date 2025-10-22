"""
PDF processor with layout-aware parsing.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog
import networkx as nx

from .base import BaseProcessor
from ..parser.layout_parser import LayoutParser, Chunk

logger = structlog.get_logger(__name__)

class PDFProcessor(BaseProcessor):
    """Layout-aware PDF processor."""
    
    def __init__(
        self,
        min_chunk_chars: int = 200,
        max_chunk_chars: int = 1000,
        overlap_chars: int = 50,
        merge_threshold: float = 50,
        **kwargs
    ):
        """Initialize processor."""
        super().__init__()
        self.parser = LayoutParser(
            min_chunk_chars=min_chunk_chars,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars
        )
        self.merge_threshold = merge_threshold
        
    def enrich_chunk_metadata(
        self,
        chunk: Chunk,
        doc_id: str,
        section_graph: nx.DiGraph,
        base_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add rich metadata to chunk."""
        # Get parent sections from graph
        parent_sections = []
        if chunk.section_id and section_graph:
            for parent in section_graph.predecessors(chunk.section_id):
                parent_sections.append(parent)
                
        # Get layout type (text vs table)
        layout_type = "table" if chunk.chunk_type == "table" else "text"
        
        return {
            "doc_id": doc_id,
            "chunk_type": layout_type,
            "page": chunk.bbox.page,
            "bbox": {
                "x0": chunk.bbox.x0,
                "y0": chunk.bbox.y0,
                "x1": chunk.bbox.x1,
                "y1": chunk.bbox.y1
            },
            "section": {
                "id": chunk.section_id,
                "heading": chunk.heading,
                "parent_sections": parent_sections
            },
            "file_metadata": base_metadata,
            "consent": {
                "scope": "internal",  # Default to internal
                "contains_pii": False  # Default to no PII
            }
        }
        
    def process(
        self,
        file_path: Path,
        stitch_context: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process PDF document.
        
        Args:
            file_path: Path to PDF
            stitch_context: Whether to stitch adjacent chunks
            **kwargs: Additional options
            
        Returns:
            List of chunks with metadata
        """
        try:
            # Parse document
            chunks, section_graph = self.parser.parse_document(str(file_path))
            if not chunks:
                self.logger.warning("no_chunks_extracted", file=str(file_path))
                return []
                
            # Get document ID and base metadata
            doc_id = self.compute_doc_id(
                file_path,
                chunks[0].text  # Use first chunk for ID
            )
            base_metadata = self.get_metadata(file_path)
            
            # Process chunks
            if stitch_context:
                # Use layout-aware stitching
                processed = []
                stitched = self.parser.stitch_context(
                    chunks=chunks,
                    query="",  # No query for ingestion
                    max_context_chunks=3
                )
                
                for result in stitched:
                    # Get metadata from first citation
                    first_cite = result["citations"][0]
                    chunk_metadata = self.enrich_chunk_metadata(
                        Chunk(
                            text=first_cite["text"],
                            bbox=chunks[0].bbox,  # Placeholder
                            heading=first_cite["heading"],
                            section_id=first_cite["section"]
                        ),
                        doc_id,
                        section_graph,
                        base_metadata
                    )
                    
                    # Add citation metadata
                    chunk_metadata["citations"] = result["citations"]
                    
                    processed.append({
                        "text": result["text"],
                        "metadata": {
                            **chunk_metadata,
                            **result["metadata"]
                        }
                    })
                    
                return processed
                
            else:
                # Process chunks individually
                return [
                    {
                        "text": chunk.text,
                        "metadata": self.enrich_chunk_metadata(
                            chunk,
                            doc_id,
                            section_graph,
                            base_metadata
                        )
                    }
                    for chunk in chunks
                ]
                
        except Exception as e:
            self.logger.error(
                "pdf_processing_failed",
                file=str(file_path),
                error=str(e)
            )
            return []