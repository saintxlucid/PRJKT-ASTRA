"""
Fusion methods for combining results from multiple retrievers.
"""
from typing import List, Dict, Optional, Set
import numpy as np
from .document import Document, SearchResults

def rrf_fusion(
    result_sets: List[SearchResults],
    k: int = 60,
    bias: float = 0.5,
) -> List[Document]:
    """
    Combine multiple result sets using Reciprocal Rank Fusion.
    
    RRF score for a document d is sum of 1/(rank + bias) across all retrievers.
    Documents not returned by a retriever are assigned rank infinity.
    
    Args:
        result_sets: List of search results from different retrievers
        k: Number of results to return
        bias: Constant to prevent division by zero and control scoring
        
    Returns:
        List of documents sorted by RRF score
    """
    # Track all unique documents and their ranks
    doc_scores: Dict[str, float] = {}
    doc_lookup: Dict[str, Document] = {}
    
    # Process each result set
    for results in result_sets:
        for rank, doc in enumerate(results.documents):
            # Create unique ID from content (could be improved with proper doc IDs)
            doc_id = f"{doc.content[:100]}_{doc.source_id or ''}"
            
            # Add RRF score: 1 / (rank + bias)
            rrf_score = 1.0 / (rank + bias)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + rrf_score
            
            # Keep track of document for later retrieval
            if doc_id not in doc_lookup:
                doc_lookup[doc_id] = doc
    
    # Sort by RRF score
    sorted_doc_ids = sorted(
        doc_scores.keys(),
        key=lambda x: doc_scores[x],
        reverse=True
    )
    
    # Return top k documents
    results = []
    for doc_id in sorted_doc_ids[:k]:
        doc = doc_lookup[doc_id]
        doc.score = doc_scores[doc_id]  # Store fusion score
        results.append(doc)
    
    return results

def interpolation_fusion(
    result_sets: List[SearchResults],
    weights: Optional[List[float]] = None,
    k: int = 60,
    min_retrievers: int = 1,
) -> List[Document]:
    """
    Combine multiple result sets using score interpolation.
    
    Args:
        result_sets: List of search results from different retrievers
        weights: Weight for each retriever (default: equal weights)
        k: Number of results to return
        min_retrievers: Minimum number of retrievers that must return a document
        
    Returns:
        List of documents sorted by interpolated score
    """
    if not result_sets:
        return []
    
    if weights is None:
        weights = [1.0 / len(result_sets)] * len(result_sets)
    elif len(weights) != len(result_sets):
        raise ValueError("Number of weights must match number of result sets")
    
    # Track documents and their scores
    doc_scores: Dict[str, float] = {}
    doc_counts: Dict[str, int] = {}
    doc_lookup: Dict[str, Document] = {}
    
    # Process each result set
    for results, weight in zip(result_sets, weights):
        # Normalize scores to [0, 1] range
        scores = np.array([d.score or 0.0 for d in results.documents])
        if len(scores) > 0:
            min_score = scores.min()
            max_score = scores.max()
            score_range = max_score - min_score
            if score_range > 0:
                scores = (scores - min_score) / score_range
        
        # Accumulate weighted scores
        for doc, norm_score in zip(results.documents, scores):
            doc_id = f"{doc.content[:100]}_{doc.source_id or ''}"
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + (norm_score * weight)
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
            if doc_id not in doc_lookup:
                doc_lookup[doc_id] = doc
    
    # Filter by minimum retriever count
    valid_docs = {
        doc_id: score
        for doc_id, score in doc_scores.items()
        if doc_counts[doc_id] >= min_retrievers
    }
    
    # Sort by interpolated score
    sorted_doc_ids = sorted(
        valid_docs.keys(),
        key=lambda x: valid_docs[x],
        reverse=True
    )
    
    # Return top k documents
    results = []
    for doc_id in sorted_doc_ids[:k]:
        doc = doc_lookup[doc_id]
        doc.score = valid_docs[doc_id]  # Store fusion score
        results.append(doc)
    
    return results