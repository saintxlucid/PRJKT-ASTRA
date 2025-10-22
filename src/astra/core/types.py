"""
Core data types for ASTRA.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class Document:
    """A document to be indexed."""
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """A search result."""
    document: Document
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
