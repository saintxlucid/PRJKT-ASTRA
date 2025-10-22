"""
Base retriever interfaces and callback system for Multi-RAG pipeline.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
import structlog
from .document import Document, SearchResults

logger = structlog.get_logger()

@runtime_checkable
class RetrievalCallback(Protocol):
    """Callback protocol for retrieval events."""
    
    def on_retrieval_start(self, query: str, metadata: Dict[str, Any]) -> None:
        """Called when retrieval starts."""
        ...
    
    def on_retrieval_error(
        self,
        error: Exception,
        query: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Called when retrieval fails."""
        ...
    
    def on_results_ready(
        self,
        results: SearchResults,
        query: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Called when results are ready from a retriever."""
        ...
    
    def on_fusion_complete(
        self,
        final_results: List[Document],
        query: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Called when fusion is complete."""
        ...

@dataclass
class RetrieverConfig:
    """Base configuration for retrievers."""
    
    retriever_id: str
    top_k: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseRetriever(ABC):
    """Base class for document retrievers."""
    
    def __init__(
        self,
        config: RetrieverConfig,
        callbacks: Optional[List[RetrievalCallback]] = None
    ):
        """Initialize retriever."""
        self.config = config
        self.callbacks = callbacks or []
        
        logger.info(
            "Initialized retriever",
            retriever_id=config.retriever_id,
            top_k=config.top_k
        )
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Retrieve documents for query.
        
        Args:
            query: Search query
            metadata: Optional metadata to pass through pipeline
            
        Returns:
            SearchResults containing matched documents
        """
        pass
    
    def _notify_start(self, query: str, metadata: Dict[str, Any]) -> None:
        """Notify callbacks of retrieval start."""
        for cb in self.callbacks:
            try:
                cb.on_retrieval_start(query, metadata)
            except Exception as e:
                logger.error(
                    "Callback error",
                    callback=cb.__class__.__name__,
                    error=str(e)
                )
    
    def _notify_error(
        self,
        error: Exception,
        query: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Notify callbacks of retrieval error."""
        for cb in self.callbacks:
            try:
                cb.on_retrieval_error(error, query, metadata)
            except Exception as e:
                logger.error(
                    "Callback error",
                    callback=cb.__class__.__name__,
                    error=str(e)
                )
    
    def _notify_results(
        self,
        results: SearchResults,
        query: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Notify callbacks of results."""
        for cb in self.callbacks:
            try:
                cb.on_results_ready(results, query, metadata)
            except Exception as e:
                logger.error(
                    "Callback error",
                    callback=cb.__class__.__name__,
                    error=str(e)
                )