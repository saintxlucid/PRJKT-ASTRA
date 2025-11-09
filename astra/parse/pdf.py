"""
Layout-aware PDF chunking implementation.
Handles PDF parsing with layout, heading, and page metadata.
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
import numpy as np
from dataclasses import dataclass

import pdfplumber
from transformers import AutoTokenizer

@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""
    page: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    heading: Optional[str]
    
@dataclass
class LayoutChunk:
    """A layout-aware chunk of text."""
    text: str
    metadata: ChunkMetadata
    
class PDFParser:
    """Layout-aware PDF parser."""
    
    def __init__(
        self,
        chunk_size: int = 700,
        stride_ratio: float = 0.25,
        tokenizer_name: str = "BAAI/bge-m3"
    ):
        """Initialize parser."""
        self.chunk_size = chunk_size
        self.stride_size = int(chunk_size * stride_ratio)
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        
    def _extract_page_content(self, page) -> List[Dict[str, Any]]:
        """Extract text blocks with layout from page."""
        blocks = []
        
        # Extract text with bounding boxes
        for element in page.extract_words():
            blocks.append({
                "text": element["text"],
                "bbox": (
                    element["x0"],
                    element["top"],
                    element["x1"],
                    element["bottom"]
                )
            })
            
        return blocks
        
    def _find_headings(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """Identify headings based on font size and position."""
        headings = []
        
        # Find elements with larger font or special positioning
        for block in blocks:
            if block.get("font_size", 0) > 12:  # Arbitrary threshold
                headings.append(block["text"])
                
        return headings
        
    def _merge_adjacent_blocks(
        self,
        blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge adjacent text blocks."""
        merged = []
        current_block = None
        
        for block in blocks:
            if current_block is None:
                current_block = block.copy()
            else:
                # Check if blocks are on same line
                if abs(block["bbox"][1] - current_block["bbox"][1]) < 2:
                    # Merge text and update bbox
                    current_block["text"] += " " + block["text"]
                    current_block["bbox"] = (
                        min(current_block["bbox"][0], block["bbox"][0]),
                        min(current_block["bbox"][1], block["bbox"][1]),
                        max(current_block["bbox"][2], block["bbox"][2]),
                        max(current_block["bbox"][3], block["bbox"][3])
                    )
                else:
                    merged.append(current_block)
                    current_block = block.copy()
                    
        if current_block:
            merged.append(current_block)
            
        return merged
        
    def _create_chunks(
        self,
        text: str,
        page: int,
        bbox: Tuple[float, float, float, float],
        heading: Optional[str] = None
    ) -> List[LayoutChunk]:
        """Create overlapping chunks from text."""
        chunks = []
        
        # Tokenize text
        tokens = self.tokenizer.tokenize(text)
        
        # Create chunks with overlap
        for i in range(0, len(tokens), self.stride_size):
            chunk_tokens = tokens[i:i + self.chunk_size]
            if not chunk_tokens:
                continue
                
            # Decode chunk
            chunk_text = self.tokenizer.convert_tokens_to_string(chunk_tokens)
            
            # Create chunk with metadata
            chunk = LayoutChunk(
                text=chunk_text,
                metadata=ChunkMetadata(
                    page=page,
                    bbox=bbox,
                    heading=heading
                )
            )
            chunks.append(chunk)
            
        return chunks
        
    def parse_pdf(self, path: str) -> List[LayoutChunk]:
        """Parse PDF into layout-aware chunks."""
        chunks = []
        current_heading = None
        
        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract content blocks
                blocks = self._extract_page_content(page)
                
                # Merge adjacent blocks
                blocks = self._merge_adjacent_blocks(blocks)
                
                # Find headings
                headings = self._find_headings(blocks)
                
                # Process blocks
                for block in blocks:
                    # Update current heading if block is a heading
                    if block["text"] in headings:
                        current_heading = block["text"]
                        continue
                        
                    # Create chunks from block
                    block_chunks = self._create_chunks(
                        text=block["text"],
                        page=page_num,
                        bbox=block["bbox"],
                        heading=current_heading
                    )
                    chunks.extend(block_chunks)
                    
        return chunks