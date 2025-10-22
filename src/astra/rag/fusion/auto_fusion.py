"""
Adaptive fusion strategies for combining multiple retrieval results.

This module provides score normalization and interpolation methods that
can be automatically tuned based on intent and performance metrics.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import structlog
from pathlib import Path
import json
import datetime

logger = structlog.get_logger(__name__)

@dataclass
class FusionConfig:
    """Configuration for rank fusion."""
    rrf_k: int = 60  # RRF constant
    mmr_lambda: float = 0.7  # MMR diversity weight
    rerank_cutoff: int = 50  # How many docs to rerank
    min_score_threshold: float = 0.01  # Filter very low scores

class AutoFusion:
    """
    Adaptive rank fusion with automatic parameter tuning.
    """
    
    def __init__(
        self,
        config: Optional[FusionConfig] = None,
        golden_set_path: Optional[str] = None
    ):
        """Initialize fusion with config and optional golden set."""
        self.config = config or FusionConfig()
        self.logger = logger.bind(component="auto_fusion")
        
        # Load golden set if provided
        self.golden_set = self._load_golden_set(golden_set_path)
        
        # Initialize intent-specific fusion parameters
        self.alpha_map = {
            "keyword": 0.2,  # Low dense weight for keyword queries
            "semantic": 0.8,  # High dense weight for semantic queries
            "code": 0.6      # Balanced for code queries
        }
        
        # Track fusion stats
        self.stats = {
            "queries": 0,
            "avg_hit_rate": 0.0,
            "intent_hit_rates": {
                "keyword": 0.0,
                "semantic": 0.0,
                "code": 0.0
            }
        }
    
    def _load_golden_set(
        self,
        path: Optional[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Load golden query set with expected results."""
        if not path:
            return {}
            
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.logger.info("loaded_golden_set", 
                           queries=len(data),
                           path=path)
            return data
        except Exception as e:
            self.logger.warning("golden_set_load_failed",
                              error=str(e))
            return {}
    
    def _normalize_scores(
        self,
        results: List[Dict[str, Any]],
        method: str = "minmax"
    ) -> List[Dict[str, Any]]:
        """Normalize relevance scores to [0,1] range."""
        if not results:
            return results
            
        scores = np.array([r["score"] for r in results])
        
        if method == "minmax":
            min_score = np.min(scores)
            score_range = np.max(scores) - min_score
            if score_range > 0:
                scores = (scores - min_score) / score_range
                
        elif method == "softmax":
            scores = np.exp(scores) / np.sum(np.exp(scores))
            
        # Update scores
        for r, s in zip(results, scores):
            r["score"] = float(s)
            
        return results
    
    def interpolate(
        self,
        bm25_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
        alpha: float
    ) -> List[Dict[str, Any]]:
        """
        Interpolate BM25 and dense scores with alpha weight.
        
        Args:
            bm25_results: Results from BM25 retrieval
            dense_results: Results from dense retrieval  
            alpha: Weight for dense scores (1-alpha for BM25)
            
        Returns:
            Merged and reranked results
        """
        # Normalize scores
        bm25_results = self._normalize_scores(bm25_results)
        dense_results = self._normalize_scores(dense_results)
        
        # Build score maps
        scores: Dict[str, float] = {}
        docs: Dict[str, Dict] = {}
        
        # Combine BM25 scores
        for i, doc in enumerate(bm25_results):
            doc_id = doc["id"]
            # RRF-style score
            score = (1.0 - alpha) * (1.0 / (self.config.rrf_k + i))
            scores[doc_id] = scores.get(doc_id, 0.0) + score
            docs[doc_id] = doc
            
        # Combine dense scores  
        for i, doc in enumerate(dense_results):
            doc_id = doc["id"]
            score = alpha * (1.0 / (self.config.rrf_k + i))
            scores[doc_id] = scores.get(doc_id, 0.0) + score
            docs[doc_id] = doc
            
        # Create merged results
        merged = []
        for doc_id, score in scores.items():
            if score >= self.config.min_score_threshold:
                doc = docs[doc_id].copy()
                doc["score"] = score
                merged.append(doc)
                
        # Sort by score
        merged.sort(key=lambda x: x["score"], reverse=True)
        
        return merged
    
    def apply_mmr(
        self,
        results: List[Dict[str, Any]],
        embedder
    ) -> List[Dict[str, Any]]:
        """
        Apply Maximal Marginal Relevance reranking for diversity.
        
        Args:
            results: Initial results to rerank
            embedder: Embedder for computing similarities
            
        Returns:
            Reranked results with diversity penalty
        """
        if len(results) <= 1:
            return results
            
        try:
            # Get embeddings for MMR
            texts = [r.get("text", "") for r in results]
            vectors = embedder.embed_documents(texts)
            
            # Track selected and remaining
            selected_idx = []
            remaining_idx = list(range(len(results)))
            
            # MMR selection
            while remaining_idx and len(selected_idx) < len(results):
                # Get scores for remaining
                scores = np.array([results[i]["score"] for i in remaining_idx])
                
                if selected_idx:
                    # Calculate similarities to selected
                    selected_vecs = vectors[selected_idx]
                    remaining_vecs = vectors[remaining_idx]
                    
                    # Get max similarity to any selected doc
                    sims = np.max(
                        np.dot(remaining_vecs, selected_vecs.T),
                        axis=1
                    )
                    
                    # MMR score
                    mmr_scores = (self.config.mmr_lambda * scores - 
                                (1.0 - self.config.mmr_lambda) * sims)
                else:
                    mmr_scores = scores
                    
                # Select max MMR score
                best_idx = remaining_idx[np.argmax(mmr_scores)]
                selected_idx.append(best_idx)
                remaining_idx.remove(best_idx)
            
            # Reorder results
            return [results[i] for i in selected_idx]
            
        except Exception as e:
            self.logger.error("mmr_failed", error=str(e))
            return results
    
    def update_weights(
        self,
        query: str,
        intent: str,
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Update fusion weights based on result quality.
        
        Args:
            query: The search query
            intent: Query intent (keyword/semantic/code)
            results: Retrieved results
        """
        if not self.golden_set or query not in self.golden_set:
            return
            
        try:
            # Get expected results
            expected = set(self.golden_set[query]["relevant_ids"])
            
            # Calculate hit rate
            retrieved = set(r["id"] for r in results[:10])
            hits = len(expected & retrieved)
            hit_rate = hits / len(expected) if expected else 0.0
            
            # Update stats
            self.stats["queries"] += 1
            old_rate = self.stats["intent_hit_rates"][intent]
            n = self.stats["queries"]
            
            # Running average
            self.stats["intent_hit_rates"][intent] = (
                (old_rate * (n-1) + hit_rate) / n
            )
            
            # Adjust alpha based on performance
            if hit_rate < old_rate and n > 10:
                # Nudge alpha in opposite direction
                delta = 0.05 * (1.0 if hit_rate < 0.5 else -1.0)
                self.alpha_map[intent] = max(0.1, min(0.9,
                    self.alpha_map[intent] + delta
                ))
                
            self.logger.debug("weights_updated",
                            intent=intent,
                            hit_rate=hit_rate,
                            new_alpha=self.alpha_map[intent])
                            
        except Exception as e:
            self.logger.error("weight_update_failed", error=str(e))
    
    def save_state(self, path: str) -> None:
        """Save current fusion state and stats."""
        try:
            state = {
                "timestamp": datetime.datetime.now().isoformat(),
                "alpha_map": self.alpha_map,
                "stats": self.stats
            }
            
            with open(path, 'w') as f:
                json.dump(state, f, indent=2)
                
            self.logger.info("state_saved", path=path)
            
        except Exception as e:
            self.logger.error("state_save_failed", 
                            path=path,
                            error=str(e))