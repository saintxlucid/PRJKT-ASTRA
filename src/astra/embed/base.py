"""
Base classes for embeddings.
"""
from abc import ABC, abstractmethod
from typing import List

import numpy as np


class BaseEmbedder(ABC):
    """Base class for text embedders."""

    @abstractmethod
    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """Embed a batch of documents.
        
        Args:
            documents: List of text documents to embed
            
        Returns:
            Array of shape (len(documents), embedding_dim) containing
            document vectors
        """
        pass