"""
Fusion layer: weighted + attention-gate cross-category combination.
Includes simple bandit learning for weight updates.
"""
import json
import os
import numpy as np
from typing import List, Dict, Any


WEIGHTS_PATH = './fusion_weights.json'


def _load_weights(categories: List[str]) -> Dict[str, float]:
    """Load fusion weights (uniform init on first run)."""
    if os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH, 'r') as f:
            w = json.load(f)
    else:
        w = {c: 1.0 / len(categories) for c in categories}
        with open(WEIGHTS_PATH, 'w') as f:
            json.dump(w, f, indent=2)
    
    for c in categories:
        w.setdefault(c, 1.0 / len(categories))
    
    return w


def attention_gate(query: str, categories: List[str]) -> Dict[str, float]:
    """Compute per-category attention weights based on query content."""
    w = {c: 1.0 for c in categories}
    
    q_lower = query.lower()
    
    # Simple heuristic: boost categories with relevant keywords
    if 'windows' in q_lower or 'service' in q_lower:
        w = {c: (1.5 if c == 'operations_systems' else 1.0) for c in categories}
    
    if 'lyrics' in q_lower or 'melody' in q_lower or 'music' in q_lower:
        w = {c: (1.5 if c == 'music_film' else 1.0) for c in categories}
    
    if 'vector' in q_lower or 'embedding' in q_lower or 'python' in q_lower:
        w = {c: (1.5 if c == 'ai_engineering' else 1.0) for c in categories}
    
    if 'meditation' in q_lower or 'focus' in q_lower or 'spiritual' in q_lower:
        w = {c: (1.5 if c == 'cognition_spirit' else 1.0) for c in categories}
    
    # Normalize
    s = sum(w.values())
    return {k: v / s for k, v in w.items()}


def fuse(query: str, candidates_by_cat: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Fuse results from multiple categories using weighted + attention-gate combination."""
    cats = list(candidates_by_cat.keys())
    
    # Global learned weights
    Wg = _load_weights(cats)
    
    # Per-query attention weights
    Wa = attention_gate(query, cats)
    
    # Combine and fuse
    fused = []
    for c, hits in candidates_by_cat.items():
        w = 0.5 * Wg.get(c, 0.25) + 0.5 * Wa.get(c, 0.25)
        for h in hits:
            hh = dict(h)
            hh['score'] = float(h.get('score', 0.0) * w)
            hh['category'] = c
            fused.append(hh)
    
    fused.sort(key=lambda x: x['score'], reverse=True)
    return fused


def bandit_update(feedback: Dict[str, Any]):
    """Simple bandit update to fusion weights based on feedback."""
    cats = list(_load_weights([]).keys())
    W = _load_weights(cats)
    
    cat = feedback.get('category')
    r = float(feedback.get('reward', 0.0))
    
    if cat not in W:
        return
    
    # Simple epsilon-greedy-like update
    W[cat] = max(0.01, min(2.0, W[cat] + 0.1 * (r - 0.5)))
    
    # Normalize
    s = sum(W.values())
    W = {k: v / s for k, v in W.items()}
    
    with open(WEIGHTS_PATH, 'w') as f:
        json.dump(W, f, indent=2)
