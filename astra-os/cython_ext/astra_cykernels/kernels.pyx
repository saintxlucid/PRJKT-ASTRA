# cython: language_level=3
# distutils: define_macros=NPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION
# cython: boundscheck=False, wraparound=False, cdivision=True, nonecheck=False, initializedcheck=False

import numpy as np
cimport numpy as cnp

from cython.parallel import prange

ctypedef cnp.float32_t f32

cdef inline f32 _max_f32(f32 a, f32 b) nogil:
    return a if a > b else b

cpdef cnp.ndarray[f32, ndim=2] batched_cosine(
    cnp.ndarray[f32, ndim=2] a,
    cnp.ndarray[f32, ndim=2] b,
    bint assume_normalized=True,
):
    """
    Compute cosine similarity matrix between two 2D arrays a (n,d) and b (m,d).
    If assume_normalized=False, rows are L2-normalized before dot.
    Returns (n, m) float32 matrix.
    """
    cdef Py_ssize_t n = a.shape[0]
    cdef Py_ssize_t m = b.shape[0]
    cdef Py_ssize_t d = a.shape[1]
    if b.shape[1] != d:
        raise ValueError("a and b must have same feature dimension")

    cdef cnp.ndarray[f32, ndim=2] a2 = a
    cdef cnp.ndarray[f32, ndim=2] b2 = b

    if not assume_normalized:
        # normalize in-place copies to avoid mutating inputs
        a2 = np.array(a, dtype=np.float32, copy=True)
        b2 = np.array(b, dtype=np.float32, copy=True)
        cdef Py_ssize_t i, j
        cdef f32 s, v
        # normalize rows of a2
        for i in range(n):
            s = 0.0
            for j in range(d):
                v = a2[i, j]
                s += v * v
            s = <f32>np.sqrt(s) if s > 0 else 1.0
            for j in range(d):
                a2[i, j] = a2[i, j] / s
        # normalize rows of b2
        for i in range(m):
            s = 0.0
            for j in range(d):
                v = b2[i, j]
                s += v * v
            s = <f32>np.sqrt(s) if s > 0 else 1.0
            for j in range(d):
                b2[i, j] = b2[i, j] / s

    cdef cnp.ndarray[f32, ndim=2] out = np.empty((n, m), dtype=np.float32)
    cdef Py_ssize_t i2, j2, k
    cdef f32 acc

    for i2 in prange(n, nogil=True, schedule='static'):
        for j2 in range(m):
            acc = 0.0
            for k in range(d):
                acc += a2[i2, k] * b2[j2, k]
            out[i2, j2] = acc
    return out

cpdef cnp.ndarray[f32, ndim=1] ewma_stream(
    cnp.ndarray[f32, ndim=1] x,
    float alpha=0.2,
):
    cdef Py_ssize_t n = x.shape[0]
    cdef cnp.ndarray[f32, ndim=1] out = np.empty(n, dtype=np.float32)
    cdef f32 s = 0.0
    cdef Py_ssize_t i
    cdef f32 a = <f32>alpha
    for i in range(n):
        s = a * x[i] + (1.0 - a) * s
        out[i] = s
    return out
