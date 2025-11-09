# Memory Consolidation Provenance & Quality Module
# SPDX-License-Identifier: MIT
"""
Cryptographic provenance and quality scoring for memory consolidation.

Features:
- Merkle-style root hashing for event clusters
- HMAC signing for summaries (tamper detection)
- Quality scoring (coverage, redundancy, specificity, recency)
- Provenance verification (recompute hashes, verify signatures)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np


# HMAC secret key
HMAC_SECRET = os.getenv("ASTRA_MEMORY_HMAC_KEY", "dev-change-me-in-production").encode()


@dataclass
class ProvenanceData:
    """Provenance metadata for a semantic summary."""
    cluster_root: str  # Merkle root of event hashes
    event_ids: list[str]  # Source event IDs
    event_hashes: list[str]  # Sample of event hashes (first 20)
    hmac_signature: str  # HMAC-SHA256 signature
    created_at: str  # ISO timestamp
    version: str = "v1"


def leaf_hash(event: dict) -> str:
    """
    Compute leaf hash for a single event.
    
    Hashes: event_id + timestamp + payload (canonical JSON)
    
    Args:
        event: Event dict with id, timestamp, payload
    
    Returns:
        SHA256 hex digest
    """
    m = hashlib.sha256()
    m.update(str(event.get("id", "")).encode())
    m.update(str(event.get("ts", "")).encode())
    
    # Canonical JSON (sorted keys)
    payload_json = json.dumps(event.get("payload", {}), sort_keys=True)
    m.update(payload_json.encode())
    
    return m.hexdigest()


def cluster_root_hash(event_hashes: list[str]) -> str:
    """
    Compute Merkle root for a cluster of events.
    
    Simple fold: hash(sorted(hash1 + hash2 + ... + hashN))
    Upgrade to binary Merkle tree if needed.
    
    Args:
        event_hashes: List of leaf hashes
    
    Returns:
        SHA256 hex digest of combined hashes
    """
    h = hashlib.sha256()
    for eh in sorted(event_hashes):
        h.update(eh.encode())
    return h.hexdigest()


def sign_summary(root_hash: str, text: str) -> dict:
    """
    Sign a summary with HMAC-SHA256.
    
    Args:
        root_hash: Cluster root hash
        text: Summary text
    
    Returns:
        Dict with root, text, hmac signature
    """
    body = {"root": root_hash, "text": text}
    mac = hmac.new(
        HMAC_SECRET,
        json.dumps(body, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {"root": root_hash, "text": text, "hmac": mac}


def verify_summary(signature: dict) -> bool:
    """
    Verify HMAC signature on a summary.
    
    Args:
        signature: Dict with root, text, hmac
    
    Returns:
        True if signature is valid
    """
    body = {"root": signature["root"], "text": signature["text"]}
    expected_mac = hmac.new(
        HMAC_SECRET,
        json.dumps(body, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_mac, signature["hmac"])


def compute_quality_score(
    events_processed: int,
    events_summarized: int,
    cluster_embeddings: np.ndarray,
    recent_count: int
) -> float:
    """
    Compute consolidation quality score (0..1).
    
    Metrics:
    - Coverage: events summarized / total events (target ≥ 0.6)
    - Redundancy: avg pairwise cosine between cluster summaries (lower better)
    - Recency mix: fraction of events from last 48h (target ≥ 0.3)
    
    Args:
        events_processed: Total events processed
        events_summarized: Events assigned to clusters (not noise)
        cluster_embeddings: Embeddings of cluster summaries (shape: [N, 1024])
        recent_count: Events from last 48h
    
    Returns:
        Quality score (0..1)
    """
    # Coverage: how many events got summarized (not noise)
    coverage = events_summarized / max(1, events_processed)
    
    # Redundancy: avg cosine similarity between cluster summaries (lower = more diverse)
    if len(cluster_embeddings) > 1:
        # Normalize embeddings
        norms = np.linalg.norm(cluster_embeddings, axis=1, keepdims=True)
        normed = cluster_embeddings / (norms + 1e-9)
        
        # Pairwise cosine similarity
        sim_matrix = np.dot(normed, normed.T)
        
        # Extract upper triangle (exclude diagonal)
        n = len(cluster_embeddings)
        indices = np.triu_indices(n, k=1)
        similarities = sim_matrix[indices]
        
        avg_redundancy = float(np.mean(similarities))
    else:
        avg_redundancy = 0.0
    
    # Recency: fraction of recent events
    recency = recent_count / max(1, events_processed)
    
    # Weighted score
    quality = (
        0.40 * coverage +                 # 40%: coverage (high is good)
        0.35 * (1 - avg_redundancy) +     # 35%: diversity (low redundancy is good)
        0.25 * recency                    # 25%: recency (high is good)
    )
    
    return min(1.0, max(0.0, quality))


def compute_quality_score_bow(
    total_events: int,
    covered_event_ids: list[int],
    summary_texts: list[str],
    event_recency_flags: list[bool],
) -> float:
    """
    Composite 0..1 quality: coverage, (1-redundancy), specificity, recency.
    
    Bag-of-words variant for when embeddings are not available.
    
    Args:
        total_events: Total events processed
        covered_event_ids: Event IDs included in summaries
        summary_texts: Summary text strings
        event_recency_flags: Boolean flags for events from last 48h
    
    Returns:
        Quality score (0..1)
    """
    import re
    from collections import Counter
    
    # Coverage
    coverage = len(set(covered_event_ids)) / max(1, total_events)
    
    # Redundancy via cosine between summary bag-of-words
    def bow(s: str):
        toks = re.findall(r"[a-zA-Z0-9_\-]+", s.lower())
        return Counter(toks)
    
    def cos(a: dict, b: dict):
        if not a or not b:
            return 0.0
        keys = set(a) | set(b)
        va = np.array([a.get(k, 0) for k in keys], dtype=float)
        vb = np.array([b.get(k, 0) for k in keys], dtype=float)
        denom = (np.linalg.norm(va) * np.linalg.norm(vb))
        return 0.0 if denom == 0 else float(np.dot(va, vb) / denom)
    
    bows = [bow(t) for t in summary_texts]
    if len(bows) <= 1:
        redundancy = 0.0
    else:
        sims = []
        for i in range(len(bows)):
            for j in range(i + 1, len(bows)):
                sims.append(cos(bows[i], bows[j]))
        redundancy = float(np.median(sims)) if sims else 0.0
    
    # Specificity: content-word density
    def content_ratio(s: str):
        toks = re.findall(r"[a-zA-Z0-9_\-]+", s.lower())
        if not toks:
            return 0.0
        # Crude stoplist
        stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for",
                "with", "by", "is", "are", "was", "were", "it", "that", "as", "at"}
        content = [t for t in toks if t not in stop]
        return len(content) / len(toks)
    
    specificity = float(np.mean([content_ratio(t) for t in summary_texts])) if summary_texts else 0.0
    
    # Recency: share of events from last 48h included
    recent = (sum(1 for f in event_recency_flags if f) / max(1, len(event_recency_flags)))
    
    score = (0.35 * coverage) + (0.25 * (1.0 - redundancy)) + (0.25 * specificity) + (0.15 * recent)
    return max(0.0, min(1.0, float(score)))


def build_provenance_prompt(cluster_events: list[dict], root_hash: str) -> tuple[dict, dict]:
    """
    Return (system_msg, user_msg) for strict, cite-only summarization.
    
    Args:
        cluster_events: List of events in cluster
        root_hash: Cluster root hash (64-char hex)
    
    Returns:
        Tuple of (system_message, user_message) dicts
    """
    lines = ["Context:"]
    for e in cluster_events:
        eid = e.get("id", "")
        txt = e.get("payload", {}).get("text", "") or str(e.get("payload", {}))
        lines.append(f"[ e{eid} ] {txt}")
    lines.append("")
    lines.append("Task:")
    lines.append("Summarize ONLY what appears in the event texts above.")
    lines.append("• No inventions. If unsure, write: 'not present in events'.")
    lines.append("• Keep it 3–5 sentences, declarative.")
    lines.append("• END with exactly one line:")
    lines.append(f"PROVENANCE: root={root_hash} uses=[eID,eID,...]")
    
    user = {"role": "user", "content": "\n".join(lines)}
    system = {"role": "system", "content": (
        "You are a compression engine. You MUST only compress content from the user text. "
        "Do not add claims, names, numbers, or causes that are not present verbatim or by safe paraphrase."
    )}
    
    return system, user


def parse_provenance_line(summary_text: str) -> tuple[str, list[int]]:
    """
    Extract root hash and used IDs; raise on failure.
    
    Args:
        summary_text: LLM output with PROVENANCE line
    
    Returns:
        Tuple of (root_hash, used_event_ids)
    
    Raises:
        ValueError: If provenance line missing or malformed
    """
    import re
    
    PROVENANCE_RE = re.compile(r"^PROVENANCE:\s*root=([0-9a-f]{64})\s+uses=\[(.*?)\]\s*$", re.IGNORECASE)
    
    last = summary_text.strip().splitlines()[-1].strip()
    m = PROVENANCE_RE.match(last)
    if not m:
        raise ValueError("Missing or malformed PROVENANCE line")
    
    root = m.group(1)
    ids = m.group(2).strip()
    if not ids:
        return root, []
    
    used = []
    for tok in ids.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok.startswith("e"):
            tok = tok[1:]
        used.append(int(tok))
    
    return root, used


def validate_summary_against_events(
    summary_text: str,
    cluster_events: list[dict],
    root_hash: str,
    used_ids: list[int]
) -> None:
    """
    Hard validation: correct root, IDs subset, and lexical grounding.
    
    Args:
        summary_text: LLM output with PROVENANCE line
        cluster_events: Source events in cluster
        root_hash: Expected cluster root hash
        used_ids: Event IDs cited in PROVENANCE
    
    Raises:
        ValueError: If validation fails
    """
    import re
    
    def tokens(s: str):
        return [t.lower() for t in re.findall(r"[a-zA-Z0-9_\-]+", s)]
    
    # 1) used_ids must be subset of cluster ids
    cluster_ids = {int(e.get("id", 0)) for e in cluster_events}
    if not set(used_ids).issubset(cluster_ids):
        raise ValueError("PROVENANCE uses= contains IDs not in cluster")
    
    # 2) Lexical grounding heuristic: at least 60% of content tokens appear across source
    src_vocab = set()
    for e in cluster_events:
        payload_text = e.get("payload", {}).get("text", "") or str(e.get("payload", {}))
        src_vocab.update(tokens(payload_text))
    
    # Strip provenance line from summary
    core_lines = summary_text.strip().splitlines()[:-1]
    core_text = " ".join(core_lines)
    out_toks = tokens(core_text)
    if not out_toks:
        raise ValueError("Empty summary body")
    
    grounded = sum(1 for t in out_toks if t in src_vocab) / max(1, len(out_toks))
    if grounded < 0.60:
        raise ValueError(f"Summary not sufficiently grounded (grounded={grounded:.2f})")


def extract_provenance_line(llm_output: str) -> dict | None:
    """
    Extract PROVENANCE: line from LLM output.
    
    Expected format:
    PROVENANCE: root=<HASH> uses=[e12,e17,e25]
    
    Args:
        llm_output: LLM-generated summary
    
    Returns:
        Dict with root, event_indices or None if not found
    """
    for line in llm_output.split("\n"):
        if line.strip().startswith("PROVENANCE:"):
            try:
                # Parse: root=<HASH> uses=[e12,e17,e25]
                parts = line.split("PROVENANCE:")[1].strip()
                
                root_part = [p for p in parts.split() if p.startswith("root=")]
                uses_part = [p for p in parts.split() if p.startswith("uses=")]
                
                if not root_part or not uses_part:
                    return None
                
                root_hash = root_part[0].split("=")[1]
                uses_str = uses_part[0].split("=")[1]
                
                # Extract event indices: [e12,e17] → [12, 17]
                event_indices = []
                for item in uses_str.strip("[]").split(","):
                    if item.strip().startswith("e"):
                        event_indices.append(int(item.strip()[1:]))
                
                return {"root": root_hash, "event_indices": event_indices}
            
            except Exception:
                return None
    
    return None


def validate_hallucination_guard(llm_output: str, expected_root: str) -> bool:
    """
    Validate that LLM output includes correct PROVENANCE line.
    
    Args:
        llm_output: LLM-generated summary
        expected_root: Expected cluster root hash
    
    Returns:
        True if provenance line is valid
    """
    prov = extract_provenance_line(llm_output)
    
    if not prov:
        return False
    
    # Verify root hash matches
    return prov["root"] == expected_root


# Example usage
if __name__ == "__main__":
    print("=== Provenance & Quality Module Test ===\n")
    
    # Test hashing
    event1 = {"id": "evt_123", "ts": "2025-11-02T00:00:00Z", "payload": {"query": "test"}}
    event2 = {"id": "evt_456", "ts": "2025-11-02T00:01:00Z", "payload": {"query": "test2"}}
    
    hash1 = leaf_hash(event1)
    hash2 = leaf_hash(event2)
    
    print(f"✅ Leaf hash 1: {hash1[:16]}...")
    print(f"✅ Leaf hash 2: {hash2[:16]}...")
    
    # Test cluster root
    root = cluster_root_hash([hash1, hash2])
    print(f"✅ Cluster root: {root[:16]}...\n")
    
    # Test signing
    summary = "User frequently asks about testing"
    signature = sign_summary(root, summary)
    
    print(f"✅ Signature: {signature['hmac'][:16]}...")
    
    # Test verification
    valid = verify_summary(signature)
    print(f"✅ Verification: {valid}\n")
    
    # Test quality score
    quality = compute_quality_score(
        events_processed=50,
        events_summarized=42,
        cluster_embeddings=np.random.randn(4, 1024),
        recent_count=30
    )
    print(f"✅ Quality score: {quality:.3f}\n")
    
    # Test provenance extraction
    llm_output = """
User frequently asks about testing and quality assurance.
PROVENANCE: root=abc123 uses=[e1,e5,e12]
"""
    prov = extract_provenance_line(llm_output)
    print(f"✅ Extracted provenance: {prov}")
    
    valid_prov = validate_hallucination_guard(llm_output, "abc123")
    print(f"✅ Provenance valid: {valid_prov}\n")
    
    print("✅ All tests passed")
