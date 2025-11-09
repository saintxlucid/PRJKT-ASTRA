# ASTRA Cython Extension (scaffold)

This directory contains an optional Cython-based performance layer for hot-path operations.

Modules (initial):
- `astra_cykernels.kernels` – batched cosine similarity + EWMA stream
- Python fallback provided when extension is unavailable

Enable at runtime (optional):
- Set environment variable `ASTRA_ENABLE_CYTHON=1` to prefer compiled kernels where available.

## Build (Windows PowerShell)

```powershell
python -m pip install --upgrade pip
python -m pip install cython numpy
cd astra-os/cython_ext
python setup.py build_ext --inplace
```

This will produce a platform-specific extension (e.g., `.pyd`) under `astra_cykernels/`.

## Use

```python
try:
    from astra_cykernels.kernels import batched_cosine, ewma_stream
except Exception:
    from astra_cykernels.fallback import batched_cosine, ewma_stream
```

## Notes
- OpenMP is attempted where supported. If the build fails, remove OpenMP flags in `setup.py` and rebuild.
- This scaffold is additive and does not change existing Python packaging.
