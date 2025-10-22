"""
Configuration presets for Qdrant vector store optimization.

Provides tuned configurations for different performance profiles:
- fast: Optimized for speed with lower accuracy
- balanced: Good balance of speed and quality
- quality: Maximum quality with higher latency
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class QdrantHNSWConfig:
    """HNSW index configuration."""
    m: int  # Number of connections per element
    ef_construct: int  # Size of dynamic candidate list during construction
    ef_search: int  # Size of dynamic candidate list during search
    on_disk: bool = False  # Whether to store vectors on disk
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Qdrant client."""
        return {
            "m": self.m,
            "ef_construct": self.ef_construct,
            "ef_search": self.ef_search,
            "on_disk": self.on_disk
        }

# Performance profiles
PRESET_CONFIGS = {
    "fast": QdrantHNSWConfig(
        m=16,  # Fewer connections = faster build
        ef_construct=128,  # Smaller construct list
        ef_search=64,  # Faster but less accurate search
    ),
    
    "balanced": QdrantHNSWConfig(
        m=32,  # Default connections
        ef_construct=256,  # Balanced construct quality
        ef_search=128,  # Good accuracy/speed trade-off
    ),
    
    "quality": QdrantHNSWConfig(
        m=48,  # More connections = better recall
        ef_construct=512,  # Larger construct list
        ef_search=256,  # More accurate search
    )
}

class VectorStoreConfig:
    """Configuration manager for vector store."""
    
    def __init__(
        self,
        preset: str = "balanced",
        custom_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize with preset or custom config."""
        self.logger = logger.bind(component="vector_store_config")
        
        if custom_config:
            self.config = QdrantHNSWConfig(**custom_config)
            self.logger.info("using_custom_config",
                           config=custom_config)
        else:
            if preset not in PRESET_CONFIGS:
                preset = "balanced"
                self.logger.warning(
                    "invalid_preset_fallback",
                    requested=preset,
                    using="balanced"
                )
                
            self.config = PRESET_CONFIGS[preset]
            self.logger.info("using_preset_config",
                           preset=preset)
            
    def get_collection_params(
        self,
        collection_name: str,
        dimension: int
    ) -> Dict[str, Any]:
        """
        Get collection creation parameters.
        
        Args:
            collection_name: Name of collection
            dimension: Vector dimension
            
        Returns:
            Dict of collection parameters
        """
        return {
            "name": collection_name,
            "vectors_config": {
                "size": dimension,
                "distance": "Cosine",
                "on_disk": self.config.on_disk
            },
            "hnsw_config": self.config.to_dict(),
            "optimizers_config": {
                "default_segment_number": 2,
                "memmap_threshold": 20000
            },
            "replication_factor": 2,  # For redundancy
            "write_consistency_factor": 1  # Fast writes
        }
        
    def get_search_params(
        self,
        limit: int,
        score_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get search parameters.
        
        Args:
            limit: Number of results to return
            score_threshold: Optional score threshold
            
        Returns:
            Dict of search parameters
        """
        params = {
            "limit": limit,
            "hnsw_ef": self.config.ef_search
        }
        
        if score_threshold is not None:
            params["score_threshold"] = score_threshold
            
        return params
        
    @property
    def index_params(self) -> Dict[str, Any]:
        """Get index parameters for building."""
        return self.config.to_dict()
        
def get_config(
    preset: str = "balanced",
    **kwargs
) -> VectorStoreConfig:
    """Factory function to get config instance."""
    return VectorStoreConfig(preset, kwargs or None)