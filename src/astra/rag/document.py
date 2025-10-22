"""
Document model and utilities for ASTRA Multi-RAG system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np

@dataclass
class Document:
    """Base document class for RAG pipeline."""
    
    # Core content
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Embedding and scoring
    embedding: Optional[List[float]] = None
    score: Optional[float] = None
    
    # Source tracking
    source_id: Optional[str] = None
    retriever_id: Optional[str] = None
    
    def __post_init__(self):
        """Convert embedding to numpy array if provided."""
        if self.embedding is not None:
            self.embedding = np.array(self.embedding)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "score": float(self.score) if self.score is not None else None,
            "source_id": self.source_id,
            "retriever_id": self.retriever_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create document from dictionary."""
        return cls(**data)

@dataclass
class SearchResults:
    """Container for search results from a retriever."""
    
    documents: List[Document]
    retriever_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.documents)
    
    def __getitem__(self, idx) -> Document:
        return self.documents[idx]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search results to dictionary."""
        return {
            "documents": [doc.to_dict() for doc in self.documents],
            "retriever_id": self.retriever_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResults":
        """Create search results from dictionary."""
        documents = [Document.from_dict(doc) for doc in data["documents"]]
        return cls(
            documents=documents,
            retriever_id=data["retriever_id"],
            metadata=data["metadata"]
        )