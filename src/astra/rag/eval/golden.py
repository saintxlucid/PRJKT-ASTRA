"""
Tools for building and managing golden sets for RAG evaluation
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional, Set
import json
from pathlib import Path
import structlog
from dataclasses import dataclass
import numpy as np
from sklearn.model_selection import train_test_split
import pandas as pd
from datetime import datetime

logger = structlog.get_logger(__name__)

@dataclass
class GoldenQuery:
    """Single golden query with expected results"""
    query: str
    intent: str  # keyword, semantic, code
    relevant_ids: List[str]  # Relevant document IDs
    irrelevant_ids: List[str]  # Known irrelevant documents
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = None  # Optional tags
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "intent": self.intent,
            "relevant_ids": self.relevant_ids,
            "irrelevant_ids": self.irrelevant_ids,
            "difficulty": self.difficulty,
            "tags": self.tags or []
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> GoldenQuery:
        return cls(
            query=data["query"],
            intent=data["intent"],
            relevant_ids=data["relevant_ids"],
            irrelevant_ids=data.get("irrelevant_ids", []),
            difficulty=data.get("difficulty", "medium"),
            tags=data.get("tags", [])
        )

class GoldenSet:
    """
    Golden set manager for RAG evaluation and tuning
    """
    
    def __init__(self, path: Optional[str] = None):
        """Initialize golden set"""
        self.logger = logger.bind(component="golden_set")
        self.queries: Dict[str, GoldenQuery] = {}
        self.metadata: Dict[str, Any] = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "num_queries": 0,
            "intent_dist": {}
        }
        
        if path:
            self.load(path)
            
    def add_query(
        self,
        query: str,
        relevant_ids: List[str],
        intent: str,
        irrelevant_ids: Optional[List[str]] = None,
        difficulty: str = "medium",
        tags: Optional[List[str]] = None
    ) -> None:
        """Add query to golden set"""
        self.queries[query] = GoldenQuery(
            query=query,
            intent=intent,
            relevant_ids=relevant_ids,
            irrelevant_ids=irrelevant_ids or [],
            difficulty=difficulty,
            tags=tags
        )
        
        # Update metadata
        self.metadata["num_queries"] = len(self.queries)
        self._update_intent_dist()
        self.metadata["last_updated"] = datetime.now().isoformat()
        
    def remove_query(self, query: str) -> None:
        """Remove query from golden set"""
        self.queries.pop(query, None)
        self._update_intent_dist()
        
    def _update_intent_dist(self) -> None:
        """Update intent distribution statistics"""
        intents = [q.intent for q in self.queries.values()]
        intent_counts = pd.Series(intents).value_counts()
        total = len(intents)
        
        self.metadata["intent_dist"] = {
            intent: round(count/total, 3)
            for intent, count in intent_counts.items()
        }
        
    def save(self, path: str) -> None:
        """Save golden set to disk"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "metadata": self.metadata,
            "queries": {
                query: q.to_dict()
                for query, q in self.queries.items()
            }
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
        self.logger.info("golden_set_saved",
                        path=str(path),
                        queries=len(self.queries))
                        
    def load(self, path: str) -> None:
        """Load golden set from disk"""
        with open(path) as f:
            data = json.load(f)
            
        self.metadata = data["metadata"]
        self.queries = {
            query: GoldenQuery.from_dict(q)
            for query, q in data["queries"].items()
        }
        
        self.logger.info("golden_set_loaded",
                        path=path,
                        queries=len(self.queries))
                        
    def evaluate(
        self,
        results: Dict[str, List[Dict]],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Evaluate retrieval results against golden set
        
        Args:
            results: Dict mapping queries to retrieved results
            metrics: Optional list of metrics to compute
            
        Returns:
            Dict of evaluation metrics
        """
        metrics = metrics or ["mrr", "hit@5", "hit@10", "ndcg@10"]
        scores = {m: [] for m in metrics}
        
        for query, golden in self.queries.items():
            if query not in results:
                continue
                
            retrieved = results[query]
            retrieved_ids = [r["id"] for r in retrieved]
            
            # Calculate metrics
            for metric in metrics:
                if metric == "mrr":
                    # Mean Reciprocal Rank
                    for i, doc_id in enumerate(retrieved_ids, 1):
                        if doc_id in golden.relevant_ids:
                            scores[metric].append(1.0 / i)
                            break
                    else:
                        scores[metric].append(0.0)
                        
                elif metric.startswith("hit@"):
                    # Hit Rate at K
                    k = int(metric.split("@")[1])
                    retrieved_k = set(retrieved_ids[:k])
                    relevant = set(golden.relevant_ids)
                    scores[metric].append(
                        len(retrieved_k & relevant) > 0
                    )
                    
                elif metric.startswith("ndcg@"):
                    # Normalized DCG
                    k = int(metric.split("@")[1])
                    dcg = 0.0
                    idcg = 0.0
                    
                    # Calculate DCG
                    for i, doc_id in enumerate(retrieved_ids[:k], 1):
                        if doc_id in golden.relevant_ids:
                            dcg += 1.0 / np.log2(i + 1)
                            
                    # Calculate IDCG
                    for i in range(min(k, len(golden.relevant_ids))):
                        idcg += 1.0 / np.log2(i + 2)
                        
                    if idcg > 0:
                        scores[metric].append(dcg / idcg)
                    else:
                        scores[metric].append(0.0)
                        
        # Average scores
        return {
            metric: np.mean(values) if values else 0.0
            for metric, values in scores.items()
        }
        
    def split(
        self,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[GoldenSet, GoldenSet]:
        """
        Split golden set into train/test sets
        
        Args:
            test_size: Fraction of queries for test set
            random_state: Random seed
            
        Returns:
            (train_set, test_set) tuple
        """
        queries = list(self.queries.items())
        train_items, test_items = train_test_split(
            queries,
            test_size=test_size,
            random_state=random_state
        )
        
        # Create train set
        train_set = GoldenSet()
        for query, golden in train_items:
            train_set.queries[query] = golden
            
        # Create test set  
        test_set = GoldenSet()
        for query, golden in test_items:
            test_set.queries[query] = golden
            
        return train_set, test_set
        
    def analyze_errors(
        self,
        results: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """
        Analyze retrieval errors
        
        Args:
            results: Dict mapping queries to retrieved results
            
        Returns:
            Error analysis statistics
        """
        stats = {
            "total_queries": len(self.queries),
            "evaluated_queries": len(results),
            "errors_by_intent": {},
            "errors_by_difficulty": {},
            "common_false_positives": [],
            "missing_relevant": []
        }
        
        # Track errors by intent and difficulty
        for query, golden in self.queries.items():
            if query not in results:
                continue
                
            retrieved = results[query]
            retrieved_ids = set(r["id"] for r in retrieved)
            relevant_ids = set(golden.relevant_ids)
            
            # Check for errors
            false_positives = retrieved_ids - relevant_ids
            false_negatives = relevant_ids - retrieved_ids
            
            if false_positives or false_negatives:
                # Count by intent
                stats["errors_by_intent"][golden.intent] = \
                    stats["errors_by_intent"].get(golden.intent, 0) + 1
                    
                # Count by difficulty    
                stats["errors_by_difficulty"][golden.difficulty] = \
                    stats["errors_by_difficulty"].get(golden.difficulty, 0) + 1
                    
                # Track specific errors
                if false_positives:
                    stats["common_false_positives"].extend([
                        {
                            "query": query,
                            "doc_id": doc_id,
                            "rank": list(retrieved_ids).index(doc_id) + 1
                        }
                        for doc_id in false_positives
                    ])
                    
                if false_negatives:
                    stats["missing_relevant"].extend([
                        {
                            "query": query,
                            "doc_id": doc_id
                        }
                        for doc_id in false_negatives
                    ])
                    
        # Summarize common errors
        stats["common_false_positives"] = pd.DataFrame(
            stats["common_false_positives"]
        ).value_counts(["doc_id"]).head(10).to_dict()
        
        stats["missing_relevant"] = pd.DataFrame(
            stats["missing_relevant"]
        ).value_counts(["doc_id"]).head(10).to_dict()
        
        return stats