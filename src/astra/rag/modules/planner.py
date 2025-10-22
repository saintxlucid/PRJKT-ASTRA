"""
HRM-style planner with fast/slow loops.
Fast loop: evidence gap detection + sub-query generation.
Slow loop: reflection on answer quality + confidence scoring.
"""
from typing import Dict, Any, List

from retrieval_core import retrieve_multi
from fusion import fuse
from optimizers import enforce_diversity


def _compute_diversity(results: List[Dict[str, Any]]) -> float:
    """Fraction of unique documents in results."""
    if not results:
        return 0.0
    unique_docs = len(set(h['doc_id'] for h in results))
    return unique_docs / len(results)


def _estimate_coverage(query: str, results: List[Dict[str, Any]]) -> float:
    """Estimate query coverage in results."""
    if not results:
        return 0.0
    combined_text = ' '.join(h['text'].lower() for h in results)
    query_words = set(query.lower().split())
    covered = sum(1 for w in query_words if w in combined_text)
    return covered / max(1, len(query_words))


def _generate_sub_queries(query: str) -> List[str]:
    """Generate sub-queries for evidence gap filling."""
    sub_qs = [query]
    
    # Simple synonym-like expansions
    expansions = {
        'snapshot': ['backup', 'export', 'persist'],
        'vacuum': ['optimize', 'defragment', 'cleanup'],
        'windows': ['win32', 'service', 'powershell'],
        'embedding': ['vector', 'representation', 'encoding'],
        'neural': ['deep', 'learning', 'network'],
    }
    
    for key, syns in expansions.items():
        if key in query.lower():
            for syn in syns:
                sub_qs.append(query.replace(key, syn))
    
    return sub_qs


def fast_loop(query: str, initial_results: Dict[str, List[Dict[str, Any]]], 
              max_iters: int = 2) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fast loop: detect evidence gaps (low diversity/coverage), 
    generate sub-queries, re-retrieve and merge.
    """
    results = dict(initial_results)
    
    for iteration in range(max_iters):
        # Fuse current results
        fused = fuse(query, results)
        fused = enforce_diversity(fused, cap_ratio=0.6)
        
        # Check diversity/coverage
        diversity = _compute_diversity(fused)
        coverage = _estimate_coverage(query, fused)
        
        # If sufficient evidence, stop
        if diversity > 0.4 and coverage > 0.7:
            break
        
        # Generate sub-queries
        sub_qs = _generate_sub_queries(query)
        
        # Retrieve for each sub-query
        for sq in sub_qs[1:]:  # Skip original
            sub_results = retrieve_multi(sq)
            for cat, hits in sub_results.items():
                if cat not in results:
                    results[cat] = []
                results[cat].extend(hits)
    
    return results


def slow_loop(query: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Slow loop: reflect on answer quality.
    Score answerability, conflict, specificity.
    Return confidence and finalize decision.
    """
    if not contexts:
        return {
            'confidence': 0.0,
            'should_finalize': False,
            'notes': 'No contexts available'
        }
    
    # Score answerability: query-context overlap
    answerability = sum(1 for c in contexts if query.lower() in c.get('text', '').lower()) / max(1, len(contexts))
    
    # Score conflict: variance in scores
    scores = [c.get('score', 0) for c in contexts]
    if len(scores) > 1:
        conflict = max(scores) - min(scores)
        conflict_score = 1.0 - (conflict / (max(scores) + 1e-8))
    else:
        conflict_score = 1.0
    
    # Score specificity: presence of numbers/citations
    specific_count = sum(1 for c in contexts if any(ch.isdigit() for ch in c.get('text', '')))
    specificity = specific_count / max(1, len(contexts))
    
    # Composite confidence
    confidence = (answerability + conflict_score + specificity) / 3.0
    
    # Finalize if confident enough
    should_finalize = confidence >= 0.7
    
    return {
        'answerability': float(answerability),
        'conflict_score': float(conflict_score),
        'specificity': float(specificity),
        'confidence': float(confidence),
        'should_finalize': should_finalize,
        'notes': 'Reflection complete'
    }


def answer(query: str, max_iters: int = 2, k: int = 12, policy: str = 'hrm') -> Dict[str, Any]:
    """
    Main HRM planner entry point.
    Policies: 'hrm' (full), 'fast_only', 'slow_only'
    """
    
    # Initial retrieval
    per_cat = retrieve_multi(query)
    
    if policy in ['hrm', 'fast_only']:
        # Fast loop: evidence gap → sub-queries
        per_cat = fast_loop(query, per_cat, max_iters=max_iters)
    
    # Fuse across categories
    fused = fuse(query, per_cat)
    fused = enforce_diversity(fused, cap_ratio=0.6)[:k]
    
    if policy in ['hrm', 'slow_only']:
        # Slow loop: reflection
        reflection = slow_loop(query, fused)
    else:
        reflection = {'confidence': 0.5, 'should_finalize': True}
    
    # Prepare response
    cites = [
        {
            'doc_id': h['doc_id'],
            'chunk_id': h['chunk_id'],
            'uri': h.get('uri', ''),
            'category': h.get('category', '')
        }
        for h in fused
    ]
    
    avg_score = sum(h['score'] for h in fused) / max(1, len(fused))
    
    return {
        'contexts': fused,
        'avg_score': float(avg_score),
        'citations': cites,
        'reflection': reflection,
        'policy': policy
    }
