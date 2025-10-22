"""
Neural Query Router for intelligent retrieval strategy selection.

This module provides query intent classification and routing to optimize 
retrieval strategies (BM25, Dense, Hybrid) based on query characteristics.
"""
from dataclasses import dataclass
from typing import Set, List, Dict, Optional
import re
from pathlib import Path
import json
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class Route:
    """Query routing configuration."""
    intent: str
    use_bm25: bool 
    use_dense: bool
    alpha: float
    
    @property
    def strategy(self) -> str:
        """Get the retrieval strategy name."""
        if self.use_bm25 and self.use_dense:
            return "hybrid"
        elif self.use_bm25:
            return "bm25"
        elif self.use_dense:
            return "dense"
        return "none"

class QueryRouter:
    """Neural query router for optimizing retrieval strategy."""
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        intent_embedder = None,  # Optional intent embedder
        confidence_threshold: float = 0.6
    ):
        """Initialize router with optional config and embedder."""
        self.logger = logger.bind(component="query_router")
        
        # Load or initialize config
        self.config = self._load_config(config_path)
        
        # Neural intent classifier
        self.intent_embedder = intent_embedder
        self.confidence_threshold = confidence_threshold
        
        # Core keyword sets for intent classification (fallback)
        self.keyword_intent: Set[str] = {
            "define", "what is", "error", "status", "config", "flag",
            "where", "when", "who", "which", "list", "show", "find",
            "how many", "count", "total", "number of"
        }
        
        self.code_intent: Set[str] = {
            "code", "function", "class", "method", "api",
            "error", "exception", "stack", "trace", "debug",
            "null", "undefined", "nan", "import", "require",
            "parameter", "argument", "return", "type"
        }
        
        # Initialize counters for analytics
        self.intent_counts: Dict[str, int] = {
            "keyword": 0,
            "semantic": 0,
            "code": 0
        }
        
        # Optional neural intent classifier
        self.intent_embedder = intent_embedder
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load routing configuration from file."""
        default_config = {
            "intent_weights": {
                "keyword": {"bm25": 0.8, "dense": 0.2},
                "semantic": {"bm25": 0.2, "dense": 0.8},
                "code": {"bm25": 0.4, "dense": 0.6}
            },
            "thresholds": {
                "keyword_ratio": 0.3,
                "code_ratio": 0.25,
                "length_threshold": 4
            }
        }
        
        if not config_path:
            return default_config
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.logger.info("loaded_config", path=config_path)
            return config
        except Exception as e:
            self.logger.warning("config_load_failed", 
                              error=str(e),
                              using="defaults")
            return default_config
    
    def _get_token_ratios(self, query: str) -> Dict[str, float]:
        """Calculate ratios of different token types in query."""
        tokens = query.lower().split()
        if not tokens:
            return {"keyword": 0.0, "code": 0.0}
            
        # Count matches in each intent set
        keyword_matches = sum(
            any(kw in " ".join(tokens[i:i+3]) for kw in self.keyword_intent)
            for i in range(len(tokens))
        )
        
        code_matches = sum(
            any(kw in " ".join(tokens[i:i+3]) for kw in self.code_intent)
            for i in range(len(tokens))
        )
        
        total = len(tokens)
        return {
            "keyword": keyword_matches / total,
            "code": code_matches / total
        }
    
    def _get_neural_intent(self, query: str) -> Tuple[Optional[str], float]:
        """Get intent using neural classifier if available."""
        if not self.intent_embedder:
            return None, 0.0
            
        try:
            # Get intent and confidence from embedder
            intent, confidence = self.intent_embedder.get_intent(
                query,
                threshold=self.confidence_threshold
            )
            if intent:
                self.logger.debug("neural_intent_success",
                                intent=intent,
                                confidence=confidence)
            return intent, confidence
        except Exception as e:
            self.logger.error("neural_intent_failed", error=str(e))
            return None, 0.0
    
    def route(self, query: str) -> Route:
        """
        Route a query to optimal retrieval strategy.
        
        Args:
            query: The search query
            
        Returns:
            Route object with intent and strategy weights
        """
        # Clean query
        query = query.strip()
        if not query:
            return Route("semantic", False, True, 0.8)
            
        # Get token type ratios
        ratios = self._get_token_ratios(query)
        
        # Try neural intent classification first
        neural_intent, confidence = self._get_neural_intent(query)
        
        # Fallback to rule-based if neural fails or low confidence
        if not neural_intent or confidence < self.confidence_threshold:
            # Determine intent
            is_short = len(query.split()) <= self.config["thresholds"]["length_threshold"]
            is_keywordy = (ratios["keyword"] >= self.config["thresholds"]["keyword_ratio"] 
                          or is_short)
            is_code = ratios["code"] >= self.config["thresholds"]["code_ratio"]
            
            # Select intent and weights
            if is_code:
                intent = "code"
                weights = self.config["intent_weights"]["code"]
            elif is_keywordy:
                intent = "keyword" 
                weights = self.config["intent_weights"]["keyword"]
            else:
                intent = "semantic"
                weights = self.config["intent_weights"]["semantic"]
                
            self.logger.debug("using_rule_based_intent",
                            intent=intent,
                            is_code=is_code,
                            is_keywordy=is_keywordy)
        else:
            # Use neural intent
            intent = neural_intent
            weights = self.config["intent_weights"][intent]
            self.logger.debug("using_neural_intent",
                            intent=intent,
                            confidence=confidence)
            
        # Update analytics
        self.intent_counts[intent] += 1
        
        # Create route
        route = Route(
            intent=intent,
            use_bm25=weights["bm25"] > 0,
            use_dense=weights["dense"] > 0,
            alpha=weights["dense"]  # Alpha is the dense weight
        )
        
        self.logger.debug("query_routed",
                         query=query,
                         intent=intent,
                         strategy=route.strategy,
                         alpha=route.alpha)
        
        return route
    
    def get_analytics(self) -> Dict:
        """Get router analytics."""
        total = sum(self.intent_counts.values())
        if total == 0:
            return {"intents": self.intent_counts}
            
        return {
            "intents": self.intent_counts,
            "intent_dist": {
                k: round(v/total, 3) 
                for k,v in self.intent_counts.items()
            }
        }