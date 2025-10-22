"""
Neural query intent classifier using BGE embeddings
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import json
import torch
from torch import nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

@dataclass
class IntentClassifierConfig:
    """Configuration for neural intent classifier"""
    model_name: str = "BAAI/bge-small-en-v1.5"
    max_length: int = 128
    batch_size: int = 32
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    cache_dir: Optional[str] = None

class QueryIntentClassifier:
    """
    Neural intent classifier using BGE embeddings
    """
    
    INTENT_DESCRIPTIONS = {
        "keyword": (
            "Direct lookup queries seeking specific information, "
            "like 'what is X' or 'show configuration'"
        ),
        "semantic": (
            "Complex natural language queries requiring understanding, "
            "like explanations or comparisons"
        ),
        "code": (
            "Code-related queries about functions, errors, or implementation, "
            "often containing technical terms"
        )
    }
    
    def __init__(self, config: Optional[IntentClassifierConfig] = None):
        """Initialize classifier"""
        self.config = config or IntentClassifierConfig()
        self.logger = logger.bind(component="intent_classifier")
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            cache_dir=self.config.cache_dir
        )
        self.model = AutoModel.from_pretrained(
            self.config.model_name,
            cache_dir=self.config.cache_dir
        )
        
        # Move model to device
        self.model = self.model.to(self.config.device)
        self.model.eval()
        
        # Create intent embeddings
        self.intent_embeddings = self._create_intent_embeddings()
        
        self.logger.info("classifier_initialized",
                        model=self.config.model_name,
                        device=self.config.device)
                        
    def _create_intent_embeddings(self) -> torch.Tensor:
        """Create embeddings for intent descriptions"""
        descriptions = [
            self.INTENT_DESCRIPTIONS[intent]
            for intent in ["keyword", "semantic", "code"]
        ]
        
        # Tokenize descriptions
        tokens = self.tokenizer(
            descriptions,
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        tokens = {k: v.to(self.config.device) for k, v in tokens.items()}
        
        # Get embeddings
        with torch.no_grad():
            outputs = self.model(**tokens)
            # Use CLS token embedding
            embeddings = outputs.last_hidden_state[:, 0]
            # Normalize
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
        return embeddings
        
    @torch.no_grad()
    def classify(
        self,
        queries: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Classify queries by intent
        
        Args:
            queries: List of queries to classify
            
        Returns:
            List of (intent, confidence) tuples
        """
        if not queries:
            return []
            
        # Tokenize queries
        tokens = self.tokenizer(
            queries,
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )
        tokens = {k: v.to(self.config.device) for k, v in tokens.items()}
        
        # Get query embeddings
        outputs = self.model(**tokens)
        query_embeddings = outputs.last_hidden_state[:, 0]
        query_embeddings = F.normalize(query_embeddings, p=2, dim=1)
        
        # Calculate similarities with intent embeddings
        similarities = torch.matmul(
            query_embeddings,
            self.intent_embeddings.T
        )
        
        # Get predicted intents
        pred_indices = similarities.argmax(dim=1)
        confidences = similarities.max(dim=1).values
        
        intents = ["keyword", "semantic", "code"]
        results = [
            (intents[idx], float(conf))
            for idx, conf in zip(pred_indices, confidences)
        ]
        
        return results
        
    def classify_batch(
        self,
        queries: List[str],
        batch_size: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Classify queries in batches
        
        Args:
            queries: List of queries to classify
            batch_size: Optional batch size override
            
        Returns:
            List of (intent, confidence) tuples
        """
        if not queries:
            return []
            
        batch_size = batch_size or self.config.batch_size
        results = []
        
        # Process in batches
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_results = self.classify(batch)
            results.extend(batch_results)
            
        return results
        
    def save_state(self, path: str) -> None:
        """Save model state and config"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save config
        with open(path / "config.json", "w") as f:
            json.dump(vars(self.config), f, indent=2)
            
        # Save model
        torch.save(self.model.state_dict(), path / "model.pt")
        
        self.logger.info("state_saved", path=str(path))
        
    @classmethod
    def load_state(cls, path: str) -> QueryIntentClassifier:
        """Load classifier from saved state"""
        path = Path(path)
        
        # Load config
        with open(path / "config.json") as f:
            config = IntentClassifierConfig(**json.load(f))
            
        classifier = cls(config)
        
        # Load model weights
        state_dict = torch.load(
            path / "model.pt",
            map_location=config.device
        )
        classifier.model.load_state_dict(state_dict)
        
        return classifier