# cython: language_level=3
"""
Common C type definitions and inline functions for ASTRA Cortex.
"""

cdef extern from "math.h" nogil:
    double sqrt(double x)
    double exp(double x)
    double log(double x)
    double fabs(double x)
    double fmax(double a, double b)
    double fmin(double a, double b)

# Shared inline functions for common operations
cdef inline double vec_dot(double[:] a, double[:] b, Py_ssize_t n) nogil:
    """Compute dot product of two vectors."""
    cdef Py_ssize_t i
    cdef double s = 0.0
    for i in range(n):
        s += a[i] * b[i]
    return s

cdef inline double vec_norm(double[:] a, Py_ssize_t n) nogil:
    """Compute L2 norm of a vector."""
    cdef Py_ssize_t i
    cdef double s = 0.0
    for i in range(n):
        s += a[i] * a[i]
    return sqrt(s)

cdef inline double vec_l2_dist(double[:] a, double[:] b, Py_ssize_t n) nogil:
    """Compute L2 distance between two vectors."""
    cdef Py_ssize_t i
    cdef double s = 0.0, d
    for i in range(n):
        d = a[i] - b[i]
        s += d * d
    return sqrt(s)
