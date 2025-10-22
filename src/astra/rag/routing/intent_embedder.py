"""
Neural intent classifier using SentenceTransformers.
"""
from typing import Dict, List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import structlog

logger = structlog.get_logger(__name__)

class IntentEmbedder:
    """Neural intent classifier using prototype-based matching."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """Initialize intent embedder.
        
        Args:
            model_name: SentenceTransformer model to use
            device: Device to run model on ('cuda', 'cpu', etc)
            cache_dir: Directory to cache model files
        """
        self.logger = logger.bind(component="intent_embedder")
        
        # Auto-select device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_dir
            )
            self.logger.info("model_loaded",
                           model=model_name,
                           device=device)
        except Exception as e:
            self.logger.error("model_load_failed",
                            error=str(e))
            raise
            
        # Intent prototypes with examples
        self.intent_prototypes = {
            "keyword": [
                "what is the status code",
                "define artificial intelligence",
                "show me the configuration",
                "list all users",
                "how many records are there",
                "find errors in the log"
            ],
            "semantic": [
                "explain how machine learning works",
                "compare supervised and unsupervised learning",
                "describe the benefits of cloud computing",
                "analyze the impact of AI on society",
                "evaluate different database options"
            ],
            "code": [
                "fix python indexerror list index out of range",
                "debug null pointer exception in java",
                "implement binary search algorithm",
                "example rest api endpoint flask",
                "how to use async await javascript"
            ]
        }
        
        # Cache prototype embeddings
        self.prototype_embeddings = {}
        self._cache_prototypes()
        
    def _cache_prototypes(self):
        """Pre-compute and cache prototype embeddings."""
        for intent, examples in self.intent_prototypes.items():
            try:
                embeddings = self.model.encode(
                    examples,
                    convert_to_tensor=True,
                    show_progress_bar=False
                )
                self.prototype_embeddings[intent] = embeddings.mean(dim=0)
            except Exception as e:
                self.logger.error("prototype_cache_failed",
                                intent=intent,
                                error=str(e))
                
    def get_intent(
        self,
        query: str,
        threshold: float = 0.5
    ) -> Tuple[Optional[str], float]:
        """Classify query intent using neural similarity.
        
        Args:
            query: The query to classify
            threshold: Minimum similarity threshold
            
        Returns:
            Tuple of (predicted intent, confidence score)
        """
        try:
            # Get query embedding
            query_emb = self.model.encode(
                query,
                convert_to_tensor=True,
                show_progress_bar=False
            )
            
            # Calculate similarities to prototypes
            sims = {
                intent: torch.cosine_similarity(
                    query_emb,
                    proto_emb.to(query_emb.device),
                    dim=0
                ).item()
                for intent, proto_emb in self.prototype_embeddings.items()
            }
            
            # Get highest scoring intent
            max_intent = max(sims.items(), key=lambda x: x[1])
            
            if max_intent[1] >= threshold:
                return max_intent
            return None, 0.0
            
        except Exception as e:
            self.logger.error("intent_classification_failed",
                            error=str(e))
            return None, 0.0
            
    def update_prototypes(
        self,
        new_examples: Dict[str, List[str]]
    ):
        """Update intent prototypes with new examples.
        
        Args:
            new_examples: Dict mapping intents to lists of examples
        """
        for intent, examples in new_examples.items():
            if intent not in self.intent_prototypes:
                continue
                
            self.intent_prototypes[intent].extend(examples)
            
        # Recompute prototype embeddings
        self._cache_prototypes()
        self.logger.info("prototypes_updated",
                        num_intents=len(new_examples))