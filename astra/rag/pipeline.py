"""
Multi-RAG pipeline implementation.
Handles document retrieval, fusion, and caching.
"""
from typing import List, Optional
import yaml

from astra.rag.document import Document
from astra.store.qdrant_store import QdrantStore
from astra.embed.bge import BGEM3Embedder

class MultiRAGPipeline:
    """Multi-retriever pipeline with fusion."""
    
    def __init__(
        self,
        dense_index: QdrantStore,
        embedder: BGEM3Embedder
    ):
        """Initialize pipeline."""
        self.dense_index = dense_index
        self.embedder = embedder
        
    @classmethod
    def from_config_file(cls, config_path: str) -> "MultiRAGPipeline":
        """Create pipeline from config file."""
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Create embedder
        embedder = BGEM3Embedder(**config["embedder"]["config"])
        
        # Create dense index
        dense_index = QdrantStore(
            embedder=embedder,
            **config["dense_index"]["config"]
        )
        
        return cls(
            dense_index=dense_index,
            embedder=embedder
        )
        
    def retrieve(
        self,
        query: str,
        k: int = 5
    ) -> List[Document]:
        """Retrieve documents for query."""
        # Get dense results
        dense_results = self.dense_index.search(
            query,
            k=k
        )
        
        return dense_results