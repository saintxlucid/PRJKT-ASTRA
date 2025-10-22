"""
Post-retrieval optimizers: dedup, adjacent packing, diversity, citation paths.
"""
import hashlib
from typing import List, Dict, Any
from collections import Counter


def _key(hit: Dict[str, Any]) -> tuple:
    """Key for deduplication."""
    return (hit['doc_id'], hit['chunk_id'])


def dedupe_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate hits by text hash."""
    seen = set()
    out = []
    for h in hits:
        k = (_key(h), hashlib.sha256(h['text'].encode('utf-8', 'ignore')).hexdigest())
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
    return out


def _is_adjacent(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two chunks are adjacent (same doc, consecutive chunk IDs)."""
    if a['doc_id'] != b['doc_id']:
        return False
    try:
        # Extract numeric part from chunk_id (format: "00000", "00001", etc.)
        ai = int(a['chunk_id'][-5:])
        bi = int(b['chunk_id'][-5:])
        return abs(ai - bi) == 1
    except Exception:
        return False


def _merge(buf: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge adjacent chunks into one."""
    if len(buf) == 1:
        return buf[0]
    
    m = dict(buf[0])
    m['text'] = '\n'.join(x['text'] for x in buf)
    m['chunk_id'] = f"{buf[0]['chunk_id']}-{buf[-1]['chunk_id']}"
    m['score'] = max(x.get('score', 0) for x in buf)
    return m


def pack_adjacent(hits: List[Dict[str, Any]], max_span: int = 2) -> List[Dict[str, Any]]:
    """Pack adjacent chunks together to reduce fragmentation."""
    if not hits:
        return hits
    
    hits = sorted(hits, key=lambda x: (x['doc_id'], x['chunk_id']))
    out, buf = [], []
    
    for h in hits:
        if not buf:
            buf = [h]
            continue
        
        if _is_adjacent(buf[-1], h) and len(buf) < max_span + 1:
            buf.append(h)
        else:
            out.append(_merge(buf))
            buf = [h]
    
    if buf:
        out.append(_merge(buf))
    
    return out


def enforce_diversity(hits: List[Dict[str, Any]], cap_ratio: float = 0.6) -> List[Dict[str, Any]]:
    """Cap single document to prevent over-concentration."""
    if not hits:
        return hits
    
    total = len(hits)
    cap = max(1, int(total * cap_ratio))
    out = []
    seen = {}
    
    for h in hits:
        cnt = seen.get(h['doc_id'], 0)
        if cnt >= cap:
            continue
        out.append(h)
        seen[h['doc_id']] = cnt + 1
    
    return out


def cite_path(hit: Dict[str, Any]) -> str:
    """Extract citation path from hit."""
    if hit.get('path'):
        return hit['path']
    return f"{hit.get('uri', '')}#{hit.get('header', '')}"
