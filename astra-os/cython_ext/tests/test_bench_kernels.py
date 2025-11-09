from typing import Any, cast

import numpy as np
import pytest

try:  # prefer extension, fallback if unavailable
    from astra_cykernels.kernels import batched_cosine  # type: ignore
    HAS_EXT = True
except Exception:
    HAS_EXT = False
    from astra_cykernels.fallback import batched_cosine  # type: ignore

@pytest.mark.skipif(not HAS_EXT, reason="Cython extension not built; using fallback")
def test_batched_cosine_perf(benchmark: Any) -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(2048, 256)).astype(np.float32)
    B = rng.normal(size=(2048, 256)).astype(np.float32)

    def run() -> np.ndarray:
        return cast(np.ndarray, batched_cosine(A, B))

    res = benchmark(run)
    assert res.shape == (A.shape[0],)
    assert np.isfinite(res).all()


def test_batched_cosine_correctness() -> None:
    rng = np.random.default_rng(0)
    A = rng.normal(size=(8, 4)).astype(np.float32)
    B = rng.normal(size=(8, 4)).astype(np.float32)

    res = batched_cosine(A, B)

    # Naive cosine to validate
    def naive_cos(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    expected = np.array([naive_cos(A[i], B[i]) for i in range(8)], dtype=np.float32)
    assert np.allclose(res, expected, atol=1e-4)
