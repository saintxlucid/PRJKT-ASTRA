"""
Base retriever interfaces for ASTRA Multi-RAG system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import time
import structlog

from .callbacks import RetrievalEvent

from .document import Document, SearchResults

logger = structlog.get_logger()

class BaseRetriever(ABC):
    """Abstract base class for all retrievers."""
    
    def __init__(self, retriever_id: str):
        """Initialize retriever.
        
        Args:
            retriever_id: Unique identifier for this retriever
        """
        self.retriever_id = retriever_id
        self._callback = None
    
    def set_callback(self, callback: callable):
        """Set callback function for retrieval events."""
        self._callback = callback
    
    def _emit_event(self, event_type: str, **kwargs):
        """Emit retrieval event through callback if set."""
        if self._callback:
            event = RetrievalEvent(
                event_type=event_type,
                retriever_id=self.retriever_id,
                metadata=kwargs
            )
            self._callback(event)
    
    @abstractmethod
    async def retrieve(self,
                      query: str,
                      k: int = 10,
                      **kwargs) -> SearchResults:
        """Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            **kwargs: Additional retriever-specific parameters
            
        Returns:
            SearchResults containing retrieved documents
        """
        pass
    
    @abstractmethod
    async def add_documents(self,
                          documents: List[Document],
                          **kwargs) -> bool:
        """Add documents to the retriever's index.
        
        Args:
            documents: List of documents to add
            **kwargs: Additional retriever-specific parameters
            
        Returns:
            True if successful
        """
        pass

class DenseRetriever(BaseRetriever):
    """Base class for dense vector retrievers."""
    
    def __init__(self, 
                retriever_id: str,
                embedding_dim: int,
                distance_metric: str = "cosine"):
        """Initialize dense retriever.
        
        Args:
            retriever_id: Unique identifier for this retriever
            embedding_dim: Dimension of embeddings
            distance_metric: Distance metric to use ("cosine", "l2", "dot")
        """
        super().__init__(retriever_id)
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate query embedding.
        
        Args:
            query: Query to embed
            
        Returns:
            Query embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate document embeddings.
        
        Args:
            documents: Documents to embed
            
        Returns:
            List of document embedding vectors
        """
        pass

class SparseRetriever(BaseRetriever):
    """Base class for sparse retrievers (e.g. BM25, TF-IDF)."""
    
    def __init__(self, 
                retriever_id: str,
                analyzer: Optional[callable] = None):
        """Initialize sparse retriever.
        
        Args:
            retriever_id: Unique identifier for this retriever
            analyzer: Optional text analyzer function
        """
        super().__init__(retriever_id)
        self.analyzer = analyzer or (lambda x: x.lower().split())
    
    @abstractmethod
    async def tokenize(self, text: str) -> List[str]:
        """Tokenize text using retriever's analyzer.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        pass
    
    @abstractmethod
    async def compute_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """Compute corpus statistics for documents.
        
        Args:
            documents: Documents to analyze
            
        Returns:
            Dictionary of corpus statistics
        """
        pass