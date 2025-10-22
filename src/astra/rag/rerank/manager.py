"""
Manager class for coordinating reranking operations.

Provides centralized control for:
- Model loading and caching
- Batch processing
- Diversity reranking
- Explanation generation
"""
from typing import List, Dict, Any, Optional
import structlog
from pathlib import Path
import torch

from .config import RerankerConfig
from .cross_encoder import CrossEncoder

logger = structlog.get_logger(__name__)

class RerankerManager:
    """Manager for reranking operations."""
    
    def __init__(
        self,
        config: Optional[RerankerConfig] = None,
        cache_dir: Optional[str] = None
    ):
        """Initialize reranker manager."""
        self.config = config or RerankerConfig()
        if cache_dir:
            self.config.cache_dir = cache_dir
            
        self.logger = logger.bind(component="reranker_manager")
        self._reranker = None
        
    @property
    def reranker(self) -> CrossEncoder:
        """Get or initialize reranker."""
        if self._reranker is None:
            try:
                self._reranker = CrossEncoder(self.config)
                self.logger.info(
                    "reranker_initialized",
                    model=self.config.model_name
                )
            except Exception as e:
                self.logger.error(
                    "reranker_init_failed",
                    error=str(e)
                )
                raise
        return self._reranker
        
    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        return_scores: bool = False,
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank results with batching and diversity.
        
        Args:
            query: Search query
            results: Initial results to rerank
            return_scores: Include scores in output
            batch_size: Override default batch size
            
        Returns:
            Reranked results
        """
        if not results:
            return results
            
        try:
            # Use configured or override batch size
            _batch_size = batch_size or self.config.batch_size
            
            # Process in batches
            reranked = []
            for i in range(0, len(results), _batch_size):
                batch = results[i:i + _batch_size]
                reranked.extend(
                    self.reranker.rerank(
                        query,
                        batch,
                        return_scores=return_scores
                    )
                )
                
            return reranked
            
        except Exception as e:
            self.logger.error(
                "reranking_failed",
                query=query,
                error=str(e)
            )
            return results
            
    def explain(
        self,
        query: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get explanation for ranking.
        
        Args:
            query: Search query
            result: Result to explain
            
        Returns:
            Explanation details
        """
        try:
            return self.reranker.get_explanation(query, result)
        except Exception as e:
            self.logger.error(
                "explanation_failed",
                query=query,
                error=str(e)
            )
            return {}
            
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.to_dict()
        
    def update_config(
        self,
        config: Dict[str, Any]
    ) -> None:
        """
        Update configuration.
        
        Args:
            config: New configuration dict
        """
        try:
            new_config = RerankerConfig.from_dict(config)
            
            # Only reload model if necessary
            if (new_config.model_name != self.config.model_name or
                new_config.use_fp16 != self.config.use_fp16):
                self._reranker = None
                
            self.config = new_config
            self.logger.info("config_updated")
            
        except Exception as e:
            self.logger.error(
                "config_update_failed",
                error=str(e)
            )
            raise