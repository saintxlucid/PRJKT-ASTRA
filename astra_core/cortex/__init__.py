"""
ASTRA Cortex - High-Performance Cython Kernels
===============================================

Low-level acceleration layer for:
- Vector memory & retrieval (cosine, dot products, L2 distances)
- Routing & scoring (softmax, temperature scaling, layer-norm)
- Audio/DSP (RMS, envelope followers, spectral analysis)
- String/byte scans (fast filters, ASCII/UTF-8 passes)
- Memory compression & semantic decay
"""

import numpy as np

# Import compiled kernels (will be available after build)
try:
    from .simkernels import cosine_batch, dot_batch, l2_batch, topk_partial
    from .routing import softmax_rows, layernorm_rows, temperature_scale
    from .dsp import rms_framewise, envelope_follower, spectral_energy_bands
    from .fastscan import count_ascii_letters, fast_tokenize, detect_pattern
    from .memory_forge import compress_vectors, semantic_decay, deduplicate_embeddings
    from .reflex_engine import check_hazards, emotional_firewall, context_snap
    
    CORTEX_AVAILABLE = True
except ImportError as e:
    # Fallback to pure Python implementations
    CORTEX_AVAILABLE = False
    import warnings
    warnings.warn(
        f"ASTRA Cortex (Cython) not compiled: {e}. Using pure Python fallback. "
        "Run 'python setup_cortex.py build_ext --inplace' to build accelerated kernels.",
        RuntimeWarning
    )


# ============================================================================
# HIGH-LEVEL API (Clean Python Interface)
# ============================================================================

def cosine(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between rows of A and B.
    
    Args:
        A: (M, D) array
        B: (N, D) array
    
    Returns:
        (M, N) similarity matrix
    """
    if not CORTEX_AVAILABLE:
        # Pure Python fallback
        A_norm = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
        B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        return A_norm @ B_norm.T
    
    A = np.ascontiguousarray(A, dtype=np.float64)
    B = np.ascontiguousarray(B, dtype=np.float64)
    out = np.empty((A.shape[0], B.shape[0]), dtype=np.float64)
    cosine_batch(A, B, out)
    return out


def dot_product(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Batched dot products (M, D) @ (N, D).T -> (M, N)"""
    if not CORTEX_AVAILABLE:
        return A @ B.T
    
    A = np.ascontiguousarray(A, dtype=np.float64)
    B = np.ascontiguousarray(B, dtype=np.float64)
    out = np.empty((A.shape[0], B.shape[0]), dtype=np.float64)
    dot_batch(A, B, out)
    return out


def l2_distance(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Batched L2 distances between rows"""
    if not CORTEX_AVAILABLE:
        return np.sqrt(np.sum((A[:, None, :] - B[None, :, :]) ** 2, axis=2))
    
    A = np.ascontiguousarray(A, dtype=np.float64)
    B = np.ascontiguousarray(B, dtype=np.float64)
    out = np.empty((A.shape[0], B.shape[0]), dtype=np.float64)
    l2_batch(A, B, out)
    return out


def softmax(X: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Stable softmax over rows with temperature scaling"""
    if not CORTEX_AVAILABLE:
        X_temp = X / temperature
        exp_x = np.exp(X_temp - np.max(X_temp, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)
    
    X = np.ascontiguousarray(X, dtype=np.float64)
    out = np.empty_like(X)
    softmax_rows(X, out, temperature)
    return out


def rms_envelope(signal: np.ndarray, frame_size: int, hop_size: int) -> np.ndarray:
    """Compute RMS envelope for audio signal (VAD, energy gates)"""
    if not CORTEX_AVAILABLE:
        frames = []
        for i in range(0, len(signal) - frame_size + 1, hop_size):
            frame = signal[i:i + frame_size]
            frames.append(np.sqrt(np.mean(frame ** 2)))
        return np.array(frames)
    
    signal = np.ascontiguousarray(signal, dtype=np.float32)
    n_frames = (len(signal) - frame_size) // hop_size + 1
    out = np.empty(n_frames, dtype=np.float32)
    rms_framewise(signal, frame_size, hop_size, out)
    return out


# ============================================================================
# ASTRA-SPECIFIC HIGH-LEVEL OPERATIONS
# ============================================================================

def memory_compress(embeddings: np.ndarray, threshold: float = 0.95) -> np.ndarray:
    """
    Compress memory vectors by removing redundancy.
    
    Args:
        embeddings: (N, D) embedding vectors
        threshold: similarity threshold for merging
    
    Returns:
        Compressed embedding set (M, D) where M < N
    """
    if not CORTEX_AVAILABLE:
        # Fallback: simple centroid clustering
        from sklearn.cluster import AgglomerativeClustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - threshold,
            linkage='average',
            metric='cosine'
        )
        labels = clustering.fit_predict(embeddings)
        compressed = []
        for label in np.unique(labels):
            mask = labels == label
            compressed.append(np.mean(embeddings[mask], axis=0))
        return np.array(compressed)
    
    embeddings = np.ascontiguousarray(embeddings, dtype=np.float64)
    return compress_vectors(embeddings, threshold)


def apply_semantic_decay(
    embeddings: np.ndarray,
    importance_scores: np.ndarray,
    time_deltas: np.ndarray,
    decay_rate: float = 0.1
) -> np.ndarray:
    """
    Apply biological-like semantic decay to memory importance.
    
    Args:
        embeddings: (N, D) memory vectors
        importance_scores: (N,) importance values
        time_deltas: (N,) time since last access
        decay_rate: decay coefficient
    
    Returns:
        Updated importance scores after decay
    """
    if not CORTEX_AVAILABLE:
        # Exponential decay fallback
        return importance_scores * np.exp(-decay_rate * time_deltas)
    
    return semantic_decay(
        np.ascontiguousarray(embeddings, dtype=np.float64),
        np.ascontiguousarray(importance_scores, dtype=np.float64),
        np.ascontiguousarray(time_deltas, dtype=np.float64),
        decay_rate
    )


def check_emotional_hazards(
    text: str,
    user_state: dict,
    threshold: float = 0.7
) -> dict:
    """
    Real-time emotional firewall for ASTRA's subconscious layer.
    
    Detects:
    - Manipulation attempts
    - Emotional triggers
    - Red flags in user input
    
    Returns:
        {
            "hazard_detected": bool,
            "hazard_type": str,
            "confidence": float,
            "suggested_action": str
        }
    """
    if not CORTEX_AVAILABLE:
        # Fallback: simple keyword matching
        hazard_keywords = ["manipulate", "force", "must", "override", "ignore previous"]
        text_lower = text.lower()
        for keyword in hazard_keywords:
            if keyword in text_lower:
                return {
                    "hazard_detected": True,
                    "hazard_type": "manipulation",
                    "confidence": 0.6,
                    "suggested_action": "clarify_intent"
                }
        return {"hazard_detected": False}
    
    return emotional_firewall(text.encode('utf-8'), user_state, threshold)


__all__ = [
    'CORTEX_AVAILABLE',
    'cosine',
    'dot_product',
    'l2_distance',
    'softmax',
    'rms_envelope',
    'memory_compress',
    'apply_semantic_decay',
    'check_emotional_hazards',
]
