"""
Vector store factory for ASTRA
"""
from typing import Dict, Any

from .qdrant_store import QdrantStore, QdrantConfig
from .dense_store import DenseStore
from ..core.types import VectorStore

def create_store(config: Dict[str, Any]) -> VectorStore:
    """Create vector store based on configuration"""
    store_type = config.get("kind", "dense")
    
    if store_type == "qdrant":
        qdrant_config = QdrantConfig(
            host=config["host"],
            port=config["port"],
            collection=config["collection"],
            distance=config.get("distance", "Cosine"),
            dim=config.get("dim", 1024)
        )
        return QdrantStore(qdrant_config)
    elif store_type == "dense":
        return DenseStore()
    else:
        raise ValueError(f"Unknown store type: {store_type}")