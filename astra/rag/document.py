"""
Document model for RAG system.
"""
from typing import Dict, Any, Optional

class Document:
    """Document for retrieval."""
    
    def __init__(
        self,
        id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize document."""
        self.id = id
        self.text = text
        self.metadata = metadata or {}