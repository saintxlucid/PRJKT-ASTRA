"""
Embedder interface and implementations for ASTRA Multi-RAG.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import numpy as np
from numpy.linalg import norm
import structlog

from astra.core.actions import action, ActionRegistry

logger = structlog.get_logger(__name__)


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """
    L2 normalize vectors.
    
    Args:
        vectors: Array of shape (n_vectors, dim)
        
    Returns:
        L2 normalized vectors of same shape
    """
    # Compute L2 norm along last axis (dim)
    norms = norm(vectors, axis=1, keepdims=True)
    # Handle zero vectors to avoid division by zero
    norms[norms == 0] = 1.0
    return vectors / norms


@dataclass
class EmbedderConfig:
    """Configuration for embedders."""
    
    model_name: str
    dimension: int
    normalize: bool = True
    use_fp16: bool = False
    device: str = "cpu"
    batch_size: int = 32
    metadata: Dict[str, Any] = None


class BaseEmbedder(ABC):
    """Base class for text embedders."""
    
    def __init__(self, config: EmbedderConfig):
        """
        Initialize embedder.
        
        Args:
            config: Embedder configuration
        """
        self.config = config
        self.registry = ActionRegistry()
        self._register_actions()
        
        logger.info("embedder_initialized",
                   model=config.model_name,
                   dim=config.dimension)
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate query embedding.
        
        Args:
            query: Query to embed
            
        Returns:
            Query embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate document embeddings.
        
        Args:
            documents: Documents to embed
            
        Returns:
            Document embedding vectors
        """
        pass
    
    def _register_actions(self) -> None:
        """Register embedder actions."""
        
        @self.registry.register(
            "embedder.embed_query",
            description="Generate query embedding",
            supports_dry_run=True
        )
        async def embed_query_action(query: str) -> List[float]:
            return await self.embed_query(query)
            
        @self.registry.register(
            "embedder.embed_documents",
            description="Generate document embeddings",
            supports_dry_run=True
        )
        async def embed_documents_action(documents: List[str]) -> List[List[float]]:
            return await self.embed_documents(documents)


class BGEM3Embedder(BaseEmbedder):
    """BGE-M3 text embedder."""
    
    def __init__(self, config: EmbedderConfig):
        """
        Initialize BGE-M3 embedder.
        
        Args:
            config: Embedder configuration
        """
        super().__init__(config)
        
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError:
            logger.error(
                "FlagEmbedding not installed. Install with: pip install FlagEmbedding"
            )
            raise
            
        try:
            self.model = BGEM3FlagModel(
                model_name_or_path=config.model_name,
                use_fp16=config.use_fp16,
                device=config.device
            )
            logger.info("bge_m3_model_loaded")
        except Exception as e:
            logger.error("bge_m3_load_failed", error=str(e))
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate query embedding with BGE-M3."""
        try:
            result = self.model.encode({"query": query})
            vectors = result["dense_vecs"]  # Shape: (1, dim)
            
            # L2 normalize if configured
            if self.config.normalize:
                vectors = l2_normalize(vectors)
                
            # Return first (only) vector
            return vectors[0].tolist()
            
        except Exception as e:
            logger.error("query_embedding_failed", error=str(e))
            raise
    
    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate document embeddings with BGE-M3."""
        try:
            batch_vectors = []
            
            # Process in batches
            for i in range(0, len(documents), self.config.batch_size):
                batch = documents[i:i + self.config.batch_size]
                
                # Encode batch
                result = self.model.encode([{"passage": doc} for doc in batch])
                vectors = result["dense_vecs"]  # Shape: (batch_size, dim)
                
                if self.config.normalize:
                    vectors = l2_normalize(vectors)
                    
                batch_vectors.extend(vectors.tolist())
                
            return batch_vectors
            
        except Exception as e:
            logger.error("document_embedding_failed", error=str(e))
            raise