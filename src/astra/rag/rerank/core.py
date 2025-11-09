"""
RAG Fusion v2 reranking module.

This module implements advanced reranking strategies including:
1. Maximal Marginal Relevance (MMR) for diversity-aware reranking
2. Recency blending to balance temporal relevance 
3. Cross-encoder rescoring for accuracy
4. Citation tracking for attribution

Created: October 31, 2025
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
import numpy as np
from sentence_transformers import CrossEncoder
import structlog
from astra.utils.logging import get_logger
from astra.metrics import RAG_RERANK_LATENCY, RAG_RERANK_COUNT

logger = get_logger(__name__)

@dataclass
class RankedResult:
    """A single reranked search result with metadata"""
    content: str
    score: float
    timestamp: datetime
    citation: Dict[str, Any]
    embedding: np.ndarray

class ResultReranker:
    """
    Advanced reranking for RAG Fusion v2.
    
    Features:
    - MMR diversity-aware reranking
    - Recency blending 
    - Cross-encoder rescoring
    - Citation tracking
    """
    
    def __init__(
        self,
        cross_encoder: Optional[CrossEncoder] = None,
        mmr_lambda: float = 0.7,
        recency_boost: float = 0.3,
        max_age_days: int = 365
    ):
        """Initialize reranker with configured weights"""
        self.cross_encoder = cross_encoder
        self.mmr_lambda = mmr_lambda  # Balance between relevance and diversity
        self.recency_boost = recency_boost  # Weight for recency in final score
        self.max_age_days = max_age_days
        
    async def rerank(
        self,
        query: str,
        results: List[RankedResult],
        top_k: int = 10
    ) -> List[RankedResult]:
        """
        Rerank results using MMR and recency blending.
        
        Args:
            query: Original query string
            results: Initial ranked results
            top_k: Number of results to return
            
        Returns:
            Reranked results with diversity and recency
        """
        with RAG_RERANK_LATENCY.time():
            try:
                # Optional cross-encoder rescoring
                if self.cross_encoder:
                    RAG_RERANK_COUNT.labels(strategy="cross_encoder").inc()
                    results = await self._cross_encode(query, results)
                
                # MMR diversity reranking
                RAG_RERANK_COUNT.labels(strategy="mmr").inc()
                results = self._mmr_rerank(results, top_k)
                
                # Recency score blending  
                RAG_RERANK_COUNT.labels(strategy="recency").inc()
                results = self._recency_blend(results)
                
                # Sort by final blended score
                results.sort(key=lambda x: x.score, reverse=True)
                
                return results[:top_k]
                
            except Exception as e:
                logger.error(
                    "rerank_error",
                    error=str(e),
                    query=query
                )
                raise

    async def _cross_encode(
        self,
        query: str,
        results: List[RankedResult]
    ) -> List[RankedResult]:
        """Apply cross-encoder rescoring"""
        if not self.cross_encoder:
            return results
            
        pairs = [(query, r.content) for r in results]
        scores = self.cross_encoder.predict(pairs)
        
        for result, score in zip(results, scores):
            result.score = score
            
        return results
        
    def _mmr_rerank(
        self,
        results: List[RankedResult],
        top_k: int
    ) -> List[RankedResult]:
        """
        Apply Maximal Marginal Relevance reranking.
        
        Balances relevance with diversity using embeddings.
        """
        # Handle empty results
        if not results:
            return []
            
        # Initialize
        selected = []
        candidates = results.copy()
        
        while len(selected) < top_k and candidates:
            # Calculate MMR scores
            mmr_scores = []
            for candidate in candidates:
                relevance = candidate.score
                
                if not selected:
                    diversity = 0
                else:
                    # Calculate max similarity to already selected
                    similarities = [
                        np.dot(candidate.embedding, s.embedding)
                        for s in selected
                    ]
                    diversity = max(similarities)
                    
                mmr = self.mmr_lambda * relevance - \
                      (1 - self.mmr_lambda) * diversity
                mmr_scores.append(mmr)
            
            # Select maximum MMR score
            best_ix = np.argmax(mmr_scores)
            selected.append(candidates.pop(best_ix))
            
        return selected

    def _recency_blend(self, results: List[RankedResult]) -> List[RankedResult]:
        """
        Blend relevance scores with recency.
        
        Uses configured recency_boost weight and max_age cutoff.
        """
        now = datetime.now()
        
        for result in results:
            age_days = (now - result.timestamp).days
            
            # Calculate time decay (1.0 -> 0.0)
            recency = max(0.0, 1.0 - (age_days / self.max_age_days))
            
            # Blend with base score 
            result.score = (1 - self.recency_boost) * result.score + \
                         self.recency_boost * recency
                         
        return results