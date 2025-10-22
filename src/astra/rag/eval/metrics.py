"""
Evaluation metrics and tracking for RAG system.

Provides:
- nDCG@k calculation
- Hit@k metrics
- Section diversity tracking
- Reranking impact analysis
- Golden set management
"""
from typing import List, Dict, Any, Set, Optional
import numpy as np
from dataclasses import dataclass
import json
from pathlib import Path
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

@dataclass
class QueryResult:
    """Represents a single query result."""
    query_id: str
    query: str
    expected_doc_ids: List[str]
    actual_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
class EvaluationMetrics:
    """Calculator for retrieval metrics."""
    
    @staticmethod
    def dcg_at_k(relevance: List[int], k: int) -> float:
        """Calculate DCG@k."""
        dcg = 0.0
        for i in range(min(len(relevance), k)):
            dcg += (2 ** relevance[i] - 1) / np.log2(i + 2)
        return dcg
        
    @staticmethod
    def ndcg_at_k(
        relevance: List[int],
        k: int,
        ideal_relevance: Optional[List[int]] = None
    ) -> float:
        """Calculate nDCG@k."""
        if not relevance:
            return 0.0
            
        dcg = EvaluationMetrics.dcg_at_k(relevance, k)
        if ideal_relevance is None:
            ideal_relevance = sorted(relevance, reverse=True)
            
        idcg = EvaluationMetrics.dcg_at_k(ideal_relevance, k)
        return dcg / idcg if idcg > 0 else 0.0
        
    @staticmethod
    def hits_at_k(
        actual_ids: List[str],
        expected_ids: List[str],
        k: int
    ) -> float:
        """Calculate Hit@k."""
        if not actual_ids or not expected_ids:
            return 0.0
            
        hits = len(
            set(actual_ids[:k]).intersection(set(expected_ids))
        )
        return hits / min(k, len(expected_ids))
        
    @staticmethod
    def section_diversity(results: List[Dict[str, Any]]) -> float:
        """Calculate section diversity score."""
        if not results:
            return 0.0
            
        sections: Set[str] = set()
        for result in results:
            metadata = result.get("metadata", {})
            sections.update(metadata.get("sections", []))
            
        max_sections = max(len(results), 1)
        return len(sections) / max_sections
        
class GoldenSet:
    """Manager for golden query sets."""
    
    def __init__(self, file_path: str):
        """Initialize with golden set file."""
        self.file_path = Path(file_path)
        self.logger = logger.bind(component="golden_set")
        self.queries: Dict[str, Dict[str, Any]] = {}
        
        if self.file_path.exists():
            self._load()
        else:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()
            
    def _load(self) -> None:
        """Load queries from file."""
        try:
            with open(self.file_path) as f:
                self.queries = json.load(f)
                self.logger.info(
                    "golden_set_loaded",
                    queries=len(self.queries)
                )
        except Exception as e:
            self.logger.error(
                "golden_set_load_failed",
                error=str(e)
            )
            self.queries = {}
            
    def _save(self) -> None:
        """Save queries to file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(
                    self.queries,
                    f,
                    indent=2
                )
            self.logger.info(
                "golden_set_saved",
                queries=len(self.queries)
            )
        except Exception as e:
            self.logger.error(
                "golden_set_save_failed",
                error=str(e)
            )
            
    def add_query(
        self,
        query: str,
        expected_doc_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add query to golden set.
        
        Args:
            query: Search query
            expected_doc_ids: Expected document IDs
            metadata: Optional query metadata
        """
        query_id = f"q{len(self.queries) + 1}"
        self.queries[query_id] = {
            "query": query,
            "expected_doc_ids": expected_doc_ids,
            "metadata": metadata or {},
            "added": datetime.now().isoformat()
        }
        self._save()
        
    def get_queries(self) -> List[Dict[str, Any]]:
        """Get all queries with metadata."""
        return [
            {"query_id": qid, **data}
            for qid, data in self.queries.items()
        ]
        
class EvaluationTracker:
    """Tracker for system evaluation metrics."""
    
    def __init__(
        self,
        golden_set: GoldenSet,
        output_dir: str = "data/eval"
    ):
        """Initialize tracker."""
        self.golden_set = golden_set
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(component="eval_tracker")
        
        # Track current run
        self.current_results: List[QueryResult] = []
        
    def add_result(
        self,
        query_id: str,
        query: str,
        expected_doc_ids: List[str],
        actual_results: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add query result for evaluation.
        
        Args:
            query_id: Query identifier
            query: Search query
            expected_doc_ids: Expected document IDs
            actual_results: Retrieved results
            metadata: Optional result metadata
        """
        self.current_results.append(
            QueryResult(
                query_id=query_id,
                query=query,
                expected_doc_ids=expected_doc_ids,
                actual_results=actual_results,
                metadata=metadata or {}
            )
        )
        
    def calculate_metrics(
        self,
        k: int = 10
    ) -> Dict[str, float]:
        """
        Calculate evaluation metrics.
        
        Args:
            k: Cut-off for metrics
            
        Returns:
            Dict of metric scores
        """
        if not self.current_results:
            return {}
            
        ndcg_scores = []
        hit_scores = []
        diversity_scores = []
        
        for result in self.current_results:
            # Get actual IDs
            actual_ids = [
                r.get("id", "")
                for r in result.actual_results
            ]
            
            # Calculate relevance scores (1 if in expected, 0 if not)
            relevance = [
                1 if doc_id in result.expected_doc_ids else 0
                for doc_id in actual_ids
            ]
            
            # Calculate metrics
            ndcg_scores.append(
                EvaluationMetrics.ndcg_at_k(relevance, k)
            )
            
            hit_scores.append(
                EvaluationMetrics.hits_at_k(
                    actual_ids,
                    result.expected_doc_ids,
                    k
                )
            )
            
            diversity_scores.append(
                EvaluationMetrics.section_diversity(
                    result.actual_results[:k]
                )
            )
            
        return {
            f"ndcg@{k}": float(np.mean(ndcg_scores)),
            f"hit@{k}": float(np.mean(hit_scores)),
            "diversity": float(np.mean(diversity_scores))
        }
        
    def save_run(
        self,
        run_id: Optional[str] = None
    ) -> None:
        """
        Save evaluation run results.
        
        Args:
            run_id: Optional run identifier
        """
        if not self.current_results:
            return
            
        # Generate run ID if not provided
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        try:
            # Calculate metrics
            metrics = {
                k: self.calculate_metrics(k)
                for k in [5, 10]
            }
            
            # Prepare run data
            run_data = {
                "run_id": run_id,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "results": [
                    {
                        "query_id": r.query_id,
                        "query": r.query,
                        "expected_doc_ids": r.expected_doc_ids,
                        "actual_results": r.actual_results,
                        "metadata": r.metadata
                    }
                    for r in self.current_results
                ]
            }
            
            # Save to file
            output_file = self.output_dir / f"eval_run_{run_id}.json"
            with open(output_file, 'w') as f:
                json.dump(run_data, f, indent=2)
                
            self.logger.info(
                "eval_run_saved",
                run_id=run_id,
                metrics=metrics
            )
            
            # Clear current results
            self.current_results = []
            
        except Exception as e:
            self.logger.error(
                "eval_save_failed",
                run_id=run_id,
                error=str(e)
            )
            
    def get_latest_metrics(
        self,
        n_runs: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get metrics from recent runs.
        
        Args:
            n_runs: Number of runs to retrieve
            
        Returns:
            List of run metrics
        """
        try:
            # Get evaluation files
            eval_files = sorted(
                self.output_dir.glob("eval_run_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[:n_runs]
            
            metrics = []
            for file in eval_files:
                with open(file) as f:
                    run_data = json.load(f)
                    metrics.append({
                        "run_id": run_data["run_id"],
                        "timestamp": run_data["timestamp"],
                        "metrics": run_data["metrics"]
                    })
                    
            return metrics
            
        except Exception as e:
            self.logger.error(
                "metrics_load_failed",
                error=str(e)
            )
            return []