"""
Category-aware routing and retrieval parameter lookup.
"""
import yaml
from typing import Dict, Any, List


def load_categories(path: str = 'categories.yaml') -> Dict[str, Any]:
    """Load category configuration."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)['categories']


def route_categories(query: str, max_k: int = 2, categories: Dict[str, Any] = None) -> List[str]:
    """Route query to relevant categories based on keyword matching."""
    if categories is None:
        categories = load_categories()
    
    q = query.lower()
    scores = []
    
    for name, cfg in categories.items():
        kws = cfg.get('keywords', [])
        score = sum(1 for k in kws if k.lower() in q)
        scores.append((name, score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    chosen = [n for (n, s) in scores if s > 0][:max_k]
    
    if not chosen:
        # Default fallback
        chosen = ['ai_engineering']
    
    return chosen


def retriever_params(category: str, categories: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get retrieval parameters for a category."""
    if categories is None:
        categories = load_categories()
    
    return categories.get(category, {}).get('retriever', {
        'bm25_k': 50,
        'vec_k': 50,
        'top_k': 10,
        'mix_alpha': 0.5
    })
