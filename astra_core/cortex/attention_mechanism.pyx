# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Real-Time Attention Mechanism
===============================

Efficient attention computation for transformer-like architectures,
optimized for real-time inference at C-speed.

Key operations:
- Scaled dot-product attention
- Multi-head attention
- Sparse attention patterns
- Flash attention approximations
- Causal masking

All operations nogil for maximum performance.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, tanh
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_attention_scores(
    float[:, :] queries,
    float[:, :] keys,
    float scale,
    float[:, :] scores_out
) nogil:
    """
    Compute scaled dot-product attention scores.
    
    Args:
        queries: (N, D) query vectors
        keys: (M, D) key vectors
        scale: scaling factor (1/sqrt(D))
        scores_out: (N, M) attention scores
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef float dot_product
    
    for i in range(N):
        for j in range(M):
            dot_product = 0.0
            for k in range(D):
                dot_product += queries[i, k] * keys[j, k]
            scores_out[i, j] = dot_product * scale


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_softmax_attention(
    float[:, :] scores,
    float[:, :] probs_out
) nogil:
    """
    Apply softmax to attention scores.
    
    Args:
        scores: (N, M) raw attention scores
        probs_out: (N, M) attention probabilities
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = scores.shape[0]
    cdef Py_ssize_t M = scores.shape[1]
    cdef float max_score, sum_exp, score
    
    for i in range(N):
        # Find max for numerical stability
        max_score = scores[i, 0]
        for j in range(1, M):
            if scores[i, j] > max_score:
                max_score = scores[i, j]
        
        # Compute exp and sum
        sum_exp = 0.0
        for j in range(M):
            score = exp(scores[i, j] - max_score)
            probs_out[i, j] = score
            sum_exp += score
        
        # Normalize
        for j in range(M):
            probs_out[i, j] /= sum_exp


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_attention_output(
    float[:, :] attention_probs,
    float[:, :] values,
    float[:, :] output
) nogil:
    """
    Compute weighted sum of values using attention probabilities.
    
    Args:
        attention_probs: (N, M) attention weights
        values: (M, D) value vectors
        output: (N, D) attention output
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = attention_probs.shape[0]
    cdef Py_ssize_t M = attention_probs.shape[1]
    cdef Py_ssize_t D = values.shape[1]
    
    # Initialize output
    for i in range(N):
        for k in range(D):
            output[i, k] = 0.0
    
    # Weighted sum
    for i in range(N):
        for j in range(M):
            for k in range(D):
                output[i, k] += attention_probs[i, j] * values[j, k]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_causal_mask(
    float[:, :] scores,
    float mask_value
) nogil:
    """
    Apply causal mask (prevent attending to future positions).
    
    Args:
        scores: (N, M) attention scores (modified in-place)
        mask_value: value for masked positions (e.g., -1e9)
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = scores.shape[0]
    cdef Py_ssize_t M = scores.shape[1]
    
    for i in range(N):
        for j in range(M):
            if j > i:
                scores[i, j] = mask_value


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_multi_head_attention(
    float[:, :] queries,
    float[:, :] keys,
    float[:, :] values,
    int num_heads,
    float[:, :] output
) nogil:
    """
    Multi-head attention (simplified, single-head implementation).
    
    Args:
        queries: (N, D) queries
        keys: (M, D) keys
        values: (M, D) values
        num_heads: number of attention heads
        output: (N, D) multi-head output
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef int head_dim = D / num_heads
    cdef float scale = 1.0 / sqrt(<float>head_dim)
    cdef float scores[256][256]  # Max 256x256 attention
    cdef float probs[256][256]
    cdef float dot_product, max_score, sum_exp
    
    # Simplified: treat as single head (full implementation would split heads)
    # Compute scores
    for i in range(N):
        if i >= 256:
            break
        for j in range(M):
            if j >= 256:
                break
            dot_product = 0.0
            for k in range(D):
                dot_product += queries[i, k] * keys[j, k]
            scores[i][j] = dot_product * scale
    
    # Softmax
    for i in range(N):
        if i >= 256:
            break
        max_score = scores[i][0]
        for j in range(1, M):
            if j >= 256:
                break
            if scores[i][j] > max_score:
                max_score = scores[i][j]
        
        sum_exp = 0.0
        for j in range(M):
            if j >= 256:
                break
            probs[i][j] = exp(scores[i][j] - max_score)
            sum_exp += probs[i][j]
        
        for j in range(M):
            if j >= 256:
                break
            probs[i][j] /= sum_exp
    
    # Weighted sum
    for i in range(N):
        for k in range(D):
            output[i, k] = 0.0
            for j in range(M):
                if i < 256 and j < 256:
                    output[i, k] += probs[i][j] * values[j, k]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_sparse_attention(
    float[:, :] queries,
    float[:, :] keys,
    int[:, :] sparsity_pattern,
    float scale,
    float[:, :] scores_out
) nogil:
    """
    Compute sparse attention (only non-zero pattern positions).
    
    Args:
        queries: (N, D) queries
        keys: (M, D) keys
        sparsity_pattern: (N, M) 1 if attend, 0 if mask
        scale: scaling factor
        scores_out: (N, M) attention scores
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef float dot_product
    
    for i in range(N):
        for j in range(M):
            if sparsity_pattern[i, j] == 1:
                dot_product = 0.0
                for k in range(D):
                    dot_product += queries[i, k] * keys[j, k]
                scores_out[i, j] = dot_product * scale
            else:
                scores_out[i, j] = -1e9  # Masked


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_local_attention_window(
    float[:, :] queries,
    float[:, :] keys,
    int window_size,
    float scale,
    float[:, :] scores_out
) nogil:
    """
    Compute local windowed attention (attend to nearby positions only).
    
    Args:
        queries: (N, D) queries
        keys: (M, D) keys
        window_size: attention window radius
        scale: scaling factor
        scores_out: (N, M) attention scores
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef float dot_product
    cdef int distance
    
    for i in range(N):
        for j in range(M):
            distance = j - i
            if distance < 0:
                distance = -distance
            
            if distance <= window_size:
                dot_product = 0.0
                for k in range(D):
                    dot_product += queries[i, k] * keys[j, k]
                scores_out[i, j] = dot_product * scale
            else:
                scores_out[i, j] = -1e9  # Outside window


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_cross_attention(
    float[:, :] queries,
    float[:, :] encoder_keys,
    float[:, :] encoder_values,
    float scale,
    float[:, :] output
) nogil:
    """
    Compute cross-attention (decoder attending to encoder).
    
    Args:
        queries: (N, D) decoder queries
        encoder_keys: (M, D) encoder keys
        encoder_values: (M, D) encoder values
        scale: scaling factor
        output: (N, D) cross-attention output
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = encoder_keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef float scores[256][256]
    cdef float probs[256][256]
    cdef float dot_product, max_score, sum_exp
    
    # Compute scores
    for i in range(N):
        if i >= 256:
            break
        for j in range(M):
            if j >= 256:
                break
            dot_product = 0.0
            for k in range(D):
                dot_product += queries[i, k] * encoder_keys[j, k]
            scores[i][j] = dot_product * scale
    
    # Softmax
    for i in range(N):
        if i >= 256:
            break
        max_score = scores[i][0]
        for j in range(1, M):
            if j >= 256:
                break
            if scores[i][j] > max_score:
                max_score = scores[i][j]
        
        sum_exp = 0.0
        for j in range(M):
            if j >= 256:
                break
            probs[i][j] = exp(scores[i][j] - max_score)
            sum_exp += probs[i][j]
        
        for j in range(M):
            if j >= 256:
                break
            probs[i][j] /= sum_exp
    
    # Weighted sum
    for i in range(N):
        for k in range(D):
            output[i, k] = 0.0
            for j in range(M):
                if i < 256 and j < 256:
                    output[i, k] += probs[i][j] * encoder_values[j, k]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_attention_entropy(
    float[:, :] attention_probs,
    float[:] entropy_out
) nogil:
    """
    Compute entropy of attention distribution (uncertainty measure).
    
    Args:
        attention_probs: (N, M) attention probabilities
        entropy_out: (N,) entropy per query [0, log(M)]
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = attention_probs.shape[0]
    cdef Py_ssize_t M = attention_probs.shape[1]
    cdef float entropy, prob
    
    for i in range(N):
        entropy = 0.0
        for j in range(M):
            prob = attention_probs[i, j]
            if prob > 1e-8:
                entropy -= prob * log(prob)
        entropy_out[i] = entropy


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_relative_position_bias(
    int[:] positions,
    int max_distance,
    float[:] bias_values,
    float[:, :] bias_matrix_out
) nogil:
    """
    Compute relative position bias for attention.
    
    Args:
        positions: (N,) position indices
        max_distance: maximum relative distance
        bias_values: (2*max_distance+1,) learned bias values
        bias_matrix_out: (N, N) position bias matrix
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t N = positions.shape[0]
    cdef int rel_pos, bias_idx
    
    for i in range(N):
        for j in range(N):
            rel_pos = positions[j] - positions[i]
            
            # Clamp to valid range
            if rel_pos < -max_distance:
                bias_idx = 0
            elif rel_pos > max_distance:
                bias_idx = 2 * max_distance
            else:
                bias_idx = rel_pos + max_distance
            
            bias_matrix_out[i, j] = bias_values[bias_idx]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_flash_attention_approximation(
    float[:, :] queries,
    float[:, :] keys,
    float[:, :] values,
    int block_size,
    float[:, :] output
) nogil:
    """
    Flash attention approximation (block-wise computation).
    
    Args:
        queries: (N, D) queries
        keys: (M, D) keys
        values: (M, D) values
        block_size: block size for tiling
        output: (N, D) attention output
    """
    cdef Py_ssize_t i, j, k, bi, bj
    cdef Py_ssize_t N = queries.shape[0]
    cdef Py_ssize_t M = keys.shape[0]
    cdef Py_ssize_t D = queries.shape[1]
    cdef int num_blocks_q = (N + block_size - 1) / block_size
    cdef int num_blocks_k = (M + block_size - 1) / block_size
    cdef float scores[64][64]  # Max 64x64 block
    cdef float probs[64][64]
    cdef float dot_product, max_score, sum_exp
    cdef int q_start, q_end, k_start, k_end
    cdef int block_q_size, block_k_size
    
    # Initialize output
    for i in range(N):
        for k in range(D):
            output[i, k] = 0.0
    
    # Process blocks
    for bi in range(num_blocks_q):
        q_start = bi * block_size
        q_end = q_start + block_size
        if q_end > N:
            q_end = N
        block_q_size = q_end - q_start
        
        for bj in range(num_blocks_k):
            k_start = bj * block_size
            k_end = k_start + block_size
            if k_end > M:
                k_end = M
            block_k_size = k_end - k_start
            
            # Compute block scores
            for i in range(block_q_size):
                if i >= 64:
                    break
                for j in range(block_k_size):
                    if j >= 64:
                        break
                    dot_product = 0.0
                    for k in range(D):
                        dot_product += queries[q_start + i, k] * keys[k_start + j, k]
                    scores[i][j] = dot_product / sqrt(<float>D)
            
            # Softmax within block
            for i in range(block_q_size):
                if i >= 64:
                    break
                max_score = scores[i][0]
                for j in range(1, block_k_size):
                    if j >= 64:
                        break
                    if scores[i][j] > max_score:
                        max_score = scores[i][j]
                
                sum_exp = 0.0
                for j in range(block_k_size):
                    if j >= 64:
                        break
                    probs[i][j] = exp(scores[i][j] - max_score)
                    sum_exp += probs[i][j]
                
                for j in range(block_k_size):
                    if j >= 64:
                        break
                    probs[i][j] /= sum_exp
            
            # Accumulate output
            for i in range(block_q_size):
                for k in range(D):
                    for j in range(block_k_size):
                        if i < 64 and j < 64:
                            output[q_start + i, k] += probs[i][j] * values[k_start + j, k]
