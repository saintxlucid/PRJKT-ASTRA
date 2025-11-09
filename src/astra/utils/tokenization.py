"""
ASTRA Tokenization Utilities
Created: October 25, 2025

Provides tokenization and text measurement utilities for
ASTRA's context planning and length budgeting.
"""
from typing import List, Tuple, Optional
import tiktoken
import logging
import structlog

logger = structlog.get_logger()

class TokenCounter:
    """Token counting and text measurement utility"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """Initialize token counter for specific model"""
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(
                "model_not_found_using_default",
                model=model,
                default="cl100k_base"
            )
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
        
    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        add_ellipsis: bool = True
    ) -> str:
        """Truncate text to fit within token budget"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
            
        truncated = self.encoding.decode(tokens[:max_tokens])
        if add_ellipsis:
            truncated = truncated.rstrip() + "..."
            
        return truncated
        
    def chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int = 0
    ) -> List[str]:
        """Split text into chunks with optional overlap"""
        tokens = self.encoding.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + chunk_size
            chunk_tokens = tokens[start:end]
            chunks.append(self.encoding.decode(chunk_tokens))
            start = end - overlap
            
        return chunks
        
    def measure_components(
        self,
        texts: List[str],
        budget: int
    ) -> Tuple[List[str], int]:
        """Measure and select texts to fit within budget
        
        Args:
            texts: List of text components to measure
            budget: Total token budget
            
        Returns:
            Tuple of (selected texts, remaining budget)
        """
        selected = []
        remaining = budget
        
        for text in texts:
            tokens = self.count_tokens(text)
            if tokens <= remaining:
                selected.append(text)
                remaining -= tokens
            else:
                # Try to fit a truncated version
                truncated = self.truncate_to_tokens(text, remaining)
                if truncated:
                    selected.append(truncated)
                remaining = 0
                break
                
        return selected, remaining