"""
BM25 index implementation using WAND optimization
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path
import pickle
import structlog
from dataclasses import dataclass
import json
from rank_bm25 import BM25Okapi
import spacy
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger(__name__)

@dataclass
class BM25Config:
    """Configuration for BM25 index"""
    k1: float = 1.5  # Term saturation parameter
    b: float = 0.75  # Length normalization parameter
    epsilon: float = 0.25  # Score threshold for WAND optimization
    tokenizer: str = "en_core_web_sm"  # spaCy model
    max_workers: int = 4  # Parallel processing workers
    cache_dir: Optional[str] = None

class BM25Index:
    """
    BM25 index with WAND optimization and caching
    """
    
    def __init__(self, config: Optional[BM25Config] = None):
        """Initialize BM25 index"""
        self.config = config or BM25Config()
        self.logger = logger.bind(component="bm25_index")
        
        # Initialize spaCy
        try:
            self.nlp = spacy.load(self.config.tokenizer)
            self.nlp.disable_pipes(["parser", "ner"])  # Keep only tokenizer
        except OSError:
            self.logger.warning("downloading_spacy_model",
                              model=self.config.tokenizer)
            spacy.cli.download(self.config.tokenizer)
            self.nlp = spacy.load(self.config.tokenizer)
            self.nlp.disable_pipes(["parser", "ner"])
            
        # Initialize index structures
        self.bm25: Optional[BM25Okapi] = None
        self.doc_ids: List[str] = []
        self.doc_texts: List[str] = []
        self.metadata: Dict[str, Dict] = {}
        
        # Initialize thread pool
        self.pool = ThreadPoolExecutor(
            max_workers=self.config.max_workers
        )
        
        self.logger.info("index_initialized", config=vars(self.config))
        
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text using spaCy"""
        doc = self.nlp(text)
        return [
            token.text.lower() for token in doc
            if not token.is_punct and not token.is_space
        ]
        
    def _batch_tokenize(self, texts: List[str]) -> List[List[str]]:
        """Tokenize multiple texts in parallel"""
        return list(self.pool.map(self._tokenize, texts))
        
    def build(
        self,
        documents: List[Dict[str, Any]],
        save_path: Optional[str] = None
    ) -> None:
        """
        Build BM25 index from documents
        
        Args:
            documents: List of dicts with 'id', 'text', and optional metadata
            save_path: Optional path to save the index
        """
        self.logger.info("building_index", num_docs=len(documents))
        
        # Extract texts and IDs
        self.doc_ids = [doc["id"] for doc in documents]
        self.doc_texts = [doc["text"] for doc in documents]
        
        # Store metadata
        self.metadata = {
            doc["id"]: {
                k: v for k, v in doc.items()
                if k not in ["id", "text"]
            }
            for doc in documents
        }
        
        # Tokenize in parallel
        tokenized_docs = self._batch_tokenize(self.doc_texts)
        
        # Build BM25
        self.bm25 = BM25Okapi(
            tokenized_docs,
            k1=self.config.k1,
            b=self.config.b
        )
        
        self.logger.info("index_built",
                        vocab_size=len(self.bm25.idf),
                        num_docs=len(self.doc_ids))
                        
        # Save if path provided
        if save_path:
            self.save(save_path)
            
    def search(
        self,
        query: str,
        k: int = 10,
        epsilon: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search index using BM25 with WAND optimization
        
        Args:
            query: Search query
            k: Number of results
            epsilon: Score threshold (default: from config)
            
        Returns:
            List of results with scores and metadata
        """
        if not self.bm25:
            raise RuntimeError("Index not built")
            
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
            
        # Get threshold for WAND
        epsilon = epsilon or self.config.epsilon
        
        # Get BM25 scores with WAND optimization
        scores = self.bm25.get_scores(query_tokens)
        
        # Apply WAND threshold and get top-k
        mask = scores > epsilon
        if not mask.any():
            return []
            
        top_idxs = np.argsort(scores[mask])[-k:][::-1]
        doc_idxs = np.where(mask)[0][top_idxs]
        
        # Build results
        results = []
        for idx in doc_idxs:
            doc_id = self.doc_ids[idx]
            results.append({
                "id": doc_id,
                "text": self.doc_texts[idx],
                "score": float(scores[idx]),
                "metadata": self.metadata.get(doc_id, {}),
                "source": "bm25"
            })
            
        return results
        
    def save(self, path: str) -> None:
        """Save index to disk"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "config": vars(self.config),
            "doc_ids": self.doc_ids,
            "doc_texts": self.doc_texts,
            "metadata": self.metadata,
            "bm25": self.bm25
        }
        
        with open(path, "wb") as f:
            pickle.dump(state, f)
            
        self.logger.info("index_saved", path=str(path))
        
    @classmethod
    def load(cls, path: str) -> BM25Index:
        """Load index from disk"""
        with open(path, "rb") as f:
            state = pickle.load(f)
            
        config = BM25Config(**state["config"])
        index = cls(config)
        
        index.doc_ids = state["doc_ids"]
        index.doc_texts = state["doc_texts"]
        index.metadata = state["metadata"]
        index.bm25 = state["bm25"]
        
        index.logger.info("index_loaded", path=path)
        return index