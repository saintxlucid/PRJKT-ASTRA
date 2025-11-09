"""
BGE-M3 Embedding Service for Dream Grove Memory System
Provides semantic embeddings and FAISS-based similarity search
"""

import numpy as np
import logging
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer
import faiss
import os

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    BGE-M3 embedding service with FAISS vector store.
    
    Features:
    - 1024-dimensional semantic embeddings
    - FAISS IndexFlatIP for cosine similarity search
    - Batch encoding support
    - Memory-efficient caching
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", dimension: int = 1024):
        """
        Initialize BGE-M3 model and FAISS index.
        
        Args:
            model_name: HuggingFace model identifier
            dimension: Embedding dimension (1024 for BGE-M3)
        """
        self.model_name = model_name
        self.dimension = dimension
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None
        self.memory_ids: List[str] = []  # Track memory IDs corresponding to vectors
        
        logger.info(f"Initializing EmbeddingService with {model_name}")
    
    def load_model(self):
        """Load BGE-M3 model (lazy loading)."""
        if self.model is None:
            logger.info(f"Loading BGE-M3 model: {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            logger.info("BGE-M3 model loaded successfully")
    
    def ensure_model_loaded(self):
        """Ensure model is loaded before use."""
        if self.model is None:
            self.load_model()
    
    def initialize_index(self):
        """Initialize FAISS index for inner product (cosine similarity)."""
        if self.index is None:
            logger.info(f"Initializing FAISS index (dimension={self.dimension})")
            self.index = faiss.IndexFlatIP(self.dimension)
            logger.info("FAISS index initialized")
    
    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            1024-dimensional embedding vector (normalized)
        """
        self.ensure_model_loaded()
        
        # BGE-M3 generates normalized embeddings suitable for cosine similarity
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts (more efficient).
        
        Args:
            texts: List of input texts
            
        Returns:
            Array of embeddings (shape: [len(texts), 1024])
        """
        self.ensure_model_loaded()
        
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings
    
    def add_to_index(self, memory_id: str, embedding: np.ndarray):
        """
        Add a single embedding to the FAISS index.
        
        Args:
            memory_id: Unique memory identifier
            embedding: 1024-dimensional vector
        """
        self.initialize_index()
        
        # Ensure embedding is 2D for FAISS
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        self.index.add(embedding.astype('float32'))
        self.memory_ids.append(memory_id)
        
        logger.debug(f"Added memory {memory_id} to index (total: {len(self.memory_ids)})")
    
    def add_batch_to_index(self, memory_ids: List[str], embeddings: np.ndarray):
        """
        Add multiple embeddings to the FAISS index.
        
        Args:
            memory_ids: List of memory identifiers
            embeddings: Array of embeddings (shape: [n, 1024])
        """
        self.initialize_index()
        
        self.index.add(embeddings.astype('float32'))
        self.memory_ids.extend(memory_ids)
        
        logger.info(f"Added {len(memory_ids)} memories to index (total: {len(self.memory_ids)})")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for similar memories using semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of (memory_id, similarity_score) tuples, sorted by relevance
        """
        if self.index is None or len(self.memory_ids) == 0:
            logger.warning("Index is empty, returning no results")
            return []
        
        # Generate query embedding
        query_embedding = self.encode(query)
        
        # Ensure query embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search FAISS index
        # IndexFlatIP returns inner product scores (cosine similarity for normalized vectors)
        scores, indices = self.index.search(query_embedding.astype('float32'), min(top_k, len(self.memory_ids)))
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.memory_ids):  # Valid index
                memory_id = self.memory_ids[idx]
                # Clamp similarity to [0, 1] range
                similarity = max(0.0, min(1.0, float(score)))
                results.append((memory_id, similarity))
        
        logger.debug(f"Search for '{query[:50]}...' returned {len(results)} results")
        return results
    
    def search_by_embedding(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Search using a pre-computed embedding.
        
        Args:
            query_embedding: Pre-computed 1024-dimensional vector
            top_k: Number of results to return
            
        Returns:
            List of (memory_id, similarity_score) tuples
        """
        if self.index is None or len(self.memory_ids) == 0:
            return []
        
        # Ensure query embedding is 2D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        scores, indices = self.index.search(query_embedding.astype('float32'), min(top_k, len(self.memory_ids)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.memory_ids):
                memory_id = self.memory_ids[idx]
                similarity = max(0.0, min(1.0, float(score)))
                results.append((memory_id, similarity))
        
        return results
    
    def remove_from_index(self, memory_id: str):
        """
        Remove a memory from the index.
        
        Note: FAISS doesn't support efficient deletion, so we rebuild the index.
        For production, consider using IndexIDMap or periodic rebuilds.
        
        Args:
            memory_id: Memory to remove
        """
        if memory_id not in self.memory_ids:
            logger.warning(f"Memory {memory_id} not in index")
            return
        
        # Find and remove from tracking list
        idx = self.memory_ids.index(memory_id)
        self.memory_ids.pop(idx)
        
        # For now, we'll just mark it as removed
        # Full implementation would require rebuilding the index
        logger.info(f"Removed memory {memory_id} from index (index rebuild required for full cleanup)")
    
    def rebuild_index(self, memories: List[Tuple[str, np.ndarray]]):
        """
        Rebuild the entire FAISS index from scratch.
        
        Args:
            memories: List of (memory_id, embedding) tuples
        """
        logger.info(f"Rebuilding FAISS index with {len(memories)} memories")
        
        # Reset index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.memory_ids = []
        
        if memories:
            memory_ids = [mid for mid, _ in memories]
            embeddings = np.array([emb for _, emb in memories])
            self.add_batch_to_index(memory_ids, embeddings)
        
        logger.info("Index rebuild complete")
    
    def get_stats(self) -> dict:
        """Get embedding service statistics."""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "model_loaded": self.model is not None,
            "index_initialized": self.index is not None,
            "total_vectors": len(self.memory_ids),
            "index_size_mb": (len(self.memory_ids) * self.dimension * 4) / (1024 * 1024) if self.memory_ids else 0
        }


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance (singleton pattern)."""
    global _embedding_service
    
    if _embedding_service is None:
        model_name = os.getenv("ASTRA_EMBEDDINGS_MODEL", "BAAI/bge-m3")
        # Allow a smaller fallback model for development/testing via env var
        _embedding_service = EmbeddingService(model_name=model_name)
    
    return _embedding_service
