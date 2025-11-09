# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3
"""
ASTRA Cortex: Routing & Scoring Kernels
========================================

Neural routing operations for multi-agent orchestration:
- Stable softmax with temperature
- Layer normalization
- Gating functions
- Expert selection scoring
"""

from cython.parallel import prange
cimport cython
from libc.math cimport exp, log, sqrt
import numpy as np


# ============================================================================
# STABLE SOFTMAX (Temperature-Scaled)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void softmax_rows(double[:, :] X, double[:, :] out, double temperature=1.0) nogil:
    """
    Stable softmax over rows with optional temperature scaling.
    
    out[i, j] = exp((X[i, j] - max_i) / T) / sum_j(exp((X[i, j] - max_i) / T))
    
    Args:
        X: (M, N) input logits
        out: (M, N) output probabilities (pre-allocated)
        temperature: scaling factor (higher = more uniform, lower = more peaked)
    
    Used for:
    - Agent selection in orchestration
    - Attention weights
    - Expert routing in MoE
    """
    cdef Py_ssize_t i, j, M = X.shape[0], N = X.shape[1]
    cdef double maxv, s, t, inv_temp = 1.0 / temperature
    
    for i in prange(M, nogil=True, schedule='static', num_threads=8):
        # Find max for numerical stability
        maxv = X[i, 0]
        for j in range(1, N):
            if X[i, j] > maxv:
                maxv = X[i, j]
        
        # Compute exp and sum
        s = 0.0
        for j in range(N):
            t = (X[i, j] - maxv) * inv_temp
            out[i, j] = exp(t)
            s += out[i, j]
        
        # Normalize
        for j in range(N):
            out[i, j] /= s


# ============================================================================
# LOG-SUM-EXP (Stable)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void logsumexp_rows(double[:, :] X, double[:] out) nogil:
    """
    Stable log-sum-exp over rows: out[i] = log(sum_j(exp(X[i, j])))
    
    Used for:
    - Partition function computation
    - Marginal likelihood
    - Routing score normalization
    """
    cdef Py_ssize_t i, j, M = X.shape[0], N = X.shape[1]
    cdef double maxv, s
    
    for i in range(M):
        maxv = X[i, 0]
        for j in range(1, N):
            if X[i, j] > maxv:
                maxv = X[i, j]
        
        s = 0.0
        for j in range(N):
            s += exp(X[i, j] - maxv)
        
        out[i] = log(s) + maxv


# ============================================================================
# LAYER NORMALIZATION
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void layernorm_rows(
    double[:, :] X,
    double[:, :] out,
    double eps=1e-5
) nogil:
    """
    Layer normalization over feature dimension (rows).
    
    out[i, j] = (X[i, j] - mean_i) / sqrt(var_i + eps)
    
    Args:
        X: (M, D) input features
        out: (M, D) normalized output
        eps: small constant for numerical stability
    
    Used for:
    - Stabilizing agent embeddings
    - Pre-routing normalization
    - Feature scaling
    """
    cdef Py_ssize_t i, j, M = X.shape[0], D = X.shape[1]
    cdef double mean, var, std, inv_std
    cdef double D_inv = 1.0 / <double>D
    
    for i in range(M):
        # Compute mean
        mean = 0.0
        for j in range(D):
            mean += X[i, j]
        mean = mean * D_inv
        
        # Compute variance
        var = 0.0
        for j in range(D):
            var += (X[i, j] - mean) * (X[i, j] - mean)
        var = var * D_inv
        
        # Normalize
        std = sqrt(var + eps)
        inv_std = 1.0 / std
        for j in range(D):
            out[i, j] = (X[i, j] - mean) * inv_std


# ============================================================================
# TEMPERATURE SCALING
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void temperature_scale(
    double[:, :] logits,
    double[:, :] out,
    double temperature
) nogil:
    """
    Apply temperature scaling to logits: out = logits / temperature
    
    Higher temperature → flatter distribution (more exploration)
    Lower temperature → peaked distribution (more exploitation)
    """
    cdef Py_ssize_t i, j, M = logits.shape[0], N = logits.shape[1]
    cdef double inv_temp = 1.0 / temperature
    
    for i in prange(M, nogil=True, schedule='static', num_threads=8):
        for j in range(N):
            out[i, j] = logits[i, j] * inv_temp


# ============================================================================
# GATING FUNCTION (Sigmoid/Tanh variants)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void gating_sigmoid(double[:, :] X, double[:, :] out) nogil:
    """
    Sigmoid gating: out[i, j] = 1 / (1 + exp(-X[i, j]))
    
    Used for:
    - Expert gating in MoE
    - Attention masking
    - Feature selection
    """
    cdef Py_ssize_t i, j, M = X.shape[0], N = X.shape[1]
    
    for i in prange(M, nogil=True, schedule='static', num_threads=8):
        for j in range(N):
            out[i, j] = 1.0 / (1.0 + exp(-X[i, j]))


# ============================================================================
# TOP-K EXPERTS SELECTION
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void select_topk_experts(
    double[:, :] scores,
    Py_ssize_t k,
    Py_ssize_t[:, :] selected_experts,
    double[:, :] selected_scores
):
    """
    Select top-k experts per sample based on routing scores.
    
    Args:
        scores: (batch_size, num_experts) routing scores
        k: number of experts to select per sample
        selected_experts: (batch_size, k) output expert indices
        selected_scores: (batch_size, k) output expert scores
    
    Used in ASTRA's multi-agent orchestration for dynamic expert routing.
    """
    cdef Py_ssize_t batch_size = scores.shape[0]
    cdef Py_ssize_t num_experts = scores.shape[1]
    cdef Py_ssize_t i, j, m, max_idx
    cdef double max_score, temp_score
    cdef Py_ssize_t temp_idx
    
    # Create used mask in Python space
    import numpy as np
    used_arr = np.zeros(num_experts, dtype=np.uint8)
    cdef unsigned char[:] used = used_arr
    
    for i in range(batch_size):
        # Reset used mask
        for j in range(num_experts):
            used[j] = 0
        
        # Select k experts
        for j in range(k):
            max_score = -1e9
            max_idx = 0
            
            # Find max unused expert
            for m in range(num_experts):
                if not used[m] and scores[i, m] > max_score:
                    max_score = scores[i, m]
                    max_idx = m
            
            selected_experts[i, j] = max_idx
            selected_scores[i, j] = max_score
            used[max_idx] = 1


# ============================================================================
# AGENT CONFIDENCE SCORING (ASTRA-specific)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_agent_confidence(
    double[:, :] embeddings,
    double[:, :] task_embedding,
    double[:] past_performance,
    double[:] out_confidence,
    double alpha=0.7
) nogil:
    """
    Compute agent confidence scores for task routing.
    
    Combines:
    - Semantic similarity (embedding · task_embedding)
    - Historical performance (past success rate)
    
    confidence = alpha * similarity + (1 - alpha) * past_performance
    
    Args:
        embeddings: (num_agents, D) agent capability embeddings
        task_embedding: (1, D) current task embedding
        past_performance: (num_agents,) historical success rates [0, 1]
        out_confidence: (num_agents,) output confidence scores
        alpha: weight for similarity vs. history
    """
    cdef Py_ssize_t i, j, num_agents = embeddings.shape[0], D = embeddings.shape[1]
    cdef double sim, norm_agent, norm_task, dot_prod
    cdef double beta = 1.0 - alpha
    
    # Compute task embedding norm
    norm_task = 0.0
    for j in range(D):
        norm_task += task_embedding[0, j] * task_embedding[0, j]
    norm_task = sqrt(norm_task)
    
    for i in range(num_agents):
        # Compute cosine similarity
        dot_prod = 0.0
        norm_agent = 0.0
        for j in range(D):
            dot_prod += embeddings[i, j] * task_embedding[0, j]
            norm_agent += embeddings[i, j] * embeddings[i, j]
        norm_agent = sqrt(norm_agent)
        
        sim = 0.0
        if norm_agent > 1e-12 and norm_task > 1e-12:
            sim = dot_prod / (norm_agent * norm_task)
        else:
            sim = 0.0
        
        # Combine with past performance
        out_confidence[i] = alpha * sim + beta * past_performance[i]
