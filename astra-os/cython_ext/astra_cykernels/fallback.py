from __future__ import annotations
import numpy as np

_EPS = 1e-12

def batched_cosine(a: np.ndarray, b: np.ndarray, assume_normalized: bool = True) -> np.ndarray:
    """
    Compute cosine similarity matrix between two 2D arrays a (n,d) and b (m,d).
    If assume_normalized=False, rows are L2-normalized before dot.
    Returns (n, m) float32 matrix.
    """
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D")
    if a.shape[1] != b.shape[1]:
        raise ValueError("a and b must have same feature dimension")
    a = a.astype(np.float32, copy=False)
    b = b.astype(np.float32, copy=False)
    if not assume_normalized:
        a_norm = np.linalg.norm(a, axis=1, keepdims=True)
        b_norm = np.linalg.norm(b, axis=1, keepdims=True)
        a = a / np.maximum(a_norm, _EPS)
        b = b / np.maximum(b_norm, _EPS)
    return (a @ b.T).astype(np.float32, copy=False)


def ewma_stream(x: np.ndarray, alpha: float = 0.2) -> np.ndarray:
    """Simple EWMA for 1D array."""
    if x.ndim != 1:
        raise ValueError("x must be 1D")
    out = np.empty_like(x, dtype=np.float32)
    s = np.float32(0.0)
    a = np.float32(alpha)
    for i in range(x.shape[0]):
        s = a * np.float32(x[i]) + (np.float32(1.0) - a) * s
        out[i] = s
    return out
