# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Neural Architecture Search (NAS) Primitives
============================================

High-performance primitives for automated neural architecture optimization,
hyperparameter tuning, and model compression at C-speed.

Key operations:
- Grid/random/Bayesian hyperparameter search
- Layer pruning and quantization
- Early stopping and validation curve analysis
- Architecture encoding/decoding
- Performance prediction

All operations optimized for rapid iteration during NAS.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, pow, tanh, sin
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void sample_hyperparameters_random(
    float[:] param_mins,
    float[:] param_maxs,
    int[:] param_log_scale,
    float[:] samples_out
) nogil:
    """
    Sample hyperparameters from uniform/log-uniform distributions.
    
    Args:
        param_mins: (N,) minimum values
        param_maxs: (N,) maximum values
        param_log_scale: (N,) 1 if log-scale, 0 if linear
        samples_out: (N,) sampled values
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = param_mins.shape[0]
    cdef float u, log_min, log_max
    
    for i in range(N):
        u = <float>rand() / <float>RAND_MAX
        
        if param_log_scale[i]:
            # Log-uniform sampling
            log_min = log(param_mins[i])
            log_max = log(param_maxs[i])
            samples_out[i] = exp(log_min + u * (log_max - log_min))
        else:
            # Linear uniform sampling
            samples_out[i] = param_mins[i] + u * (param_maxs[i] - param_mins[i])


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_layer_importance(
    float[:, :] weights,
    float[:] importance_out
) nogil:
    """
    Compute layer importance for pruning (L1 norm of weights).
    
    Args:
        weights: (M, N) layer weights
        importance_out: (M,) importance scores
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = weights.shape[0]
    cdef Py_ssize_t N = weights.shape[1]
    cdef float norm
    
    for i in range(M):
        norm = 0.0
        for j in range(N):
            norm += fabs(weights[i, j])
        importance_out[i] = norm / <float>N


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void prune_weights_magnitude(
    float[:, :] weights,
    float pruning_ratio,
    float[:, :] pruned_weights_out
) nogil:
    """
    Prune weights by magnitude (zero out smallest weights).
    
    Args:
        weights: (M, N) original weights
        pruning_ratio: fraction to prune [0, 1]
        pruned_weights_out: (M, N) pruned weights
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = weights.shape[0]
    cdef Py_ssize_t N = weights.shape[1]
    cdef float threshold = 0.0
    cdef float sorted_vals[10000]  # Max 10k weights for threshold
    cdef int total_weights = M * N
    cdef int prune_count = <int>(pruning_ratio * <float>total_weights)
    cdef int idx = 0
    
    # Collect absolute values
    for i in range(M):
        for j in range(N):
            if idx < 10000:
                sorted_vals[idx] = fabs(weights[i, j])
                idx += 1
    
    # Simple selection: approximate threshold (for demo)
    if prune_count < idx:
        threshold = sorted_vals[prune_count] if prune_count > 0 else 0.0
    
    # Prune
    for i in range(M):
        for j in range(N):
            if fabs(weights[i, j]) <= threshold:
                pruned_weights_out[i, j] = 0.0
            else:
                pruned_weights_out[i, j] = weights[i, j]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void quantize_weights(
    float[:, :] weights,
    int num_bits,
    float[:, :] quantized_weights_out
) nogil:
    """
    Quantize weights to fixed-point representation.
    
    Args:
        weights: (M, N) original weights
        num_bits: quantization bits (e.g., 8 for int8)
        quantized_weights_out: (M, N) quantized weights
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = weights.shape[0]
    cdef Py_ssize_t N = weights.shape[1]
    cdef float w_min = 1e9
    cdef float w_max = -1e9
    cdef float scale, zero_point
    cdef int quantized_val
    cdef int max_val = (1 << num_bits) - 1
    
    # Find range
    for i in range(M):
        for j in range(N):
            if weights[i, j] < w_min:
                w_min = weights[i, j]
            if weights[i, j] > w_max:
                w_max = weights[i, j]
    
    # Compute scale
    if w_max > w_min:
        scale = (w_max - w_min) / <float>max_val
    else:
        scale = 1.0
    
    zero_point = w_min
    
    # Quantize
    for i in range(M):
        for j in range(N):
            quantized_val = <int>((weights[i, j] - zero_point) / scale)
            if quantized_val < 0:
                quantized_val = 0
            elif quantized_val > max_val:
                quantized_val = max_val
            quantized_weights_out[i, j] = <float>quantized_val * scale + zero_point


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_early_stopping(
    float[:] validation_losses,
    int patience,
    float min_delta
) nogil:
    """
    Detect if training should stop early (no improvement).
    
    Args:
        validation_losses: (T,) validation loss history
        patience: epochs to wait
        min_delta: minimum improvement threshold
        
    Returns:
        1 if should stop, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t T = validation_losses.shape[0]
    cdef float best_loss
    cdef int no_improvement_count = 0
    
    if T < patience + 1:
        return 0
    
    best_loss = validation_losses[T - patience - 1]
    
    for i in range(T - patience, T):
        if validation_losses[i] < best_loss - min_delta:
            return 0  # Found improvement
    
    return 1  # No improvement for patience epochs


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_architecture_complexity(
    int[:] layer_sizes,
    int num_layers
) nogil:
    """
    Compute architecture complexity (total parameters).
    
    Args:
        layer_sizes: (L,) neurons per layer
        num_layers: number of layers
        
    Returns:
        complexity: total parameters
    """
    cdef Py_ssize_t i
    cdef float total_params = 0.0
    
    for i in range(num_layers - 1):
        total_params += <float>(layer_sizes[i] * layer_sizes[i + 1])
    
    return total_params


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void encode_architecture(
    int[:] layer_sizes,
    int[:] activation_types,
    float[:] dropout_rates,
    int num_layers,
    float[:] encoding_out
) nogil:
    """
    Encode architecture to fixed-size vector.
    
    Args:
        layer_sizes: (L,) neurons per layer
        activation_types: (L,) activation function IDs
        dropout_rates: (L,) dropout rates
        num_layers: number of layers
        encoding_out: (3*L,) flattened encoding
    """
    cdef Py_ssize_t i
    cdef int idx = 0
    
    for i in range(num_layers):
        encoding_out[idx] = <float>layer_sizes[i] / 1024.0  # Normalize
        idx += 1
    
    for i in range(num_layers):
        encoding_out[idx] = <float>activation_types[i] / 10.0
        idx += 1
    
    for i in range(num_layers):
        encoding_out[idx] = dropout_rates[i]
        idx += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void predict_performance_linear(
    float[:] architecture_encoding,
    float[:] coefficients,
    float bias,
    float[:] predicted_metric_out
) nogil:
    """
    Predict architecture performance using linear model.
    
    Args:
        architecture_encoding: (D,) architecture features
        coefficients: (D,) learned coefficients
        bias: learned bias
        predicted_metric_out: (1,) predicted metric (e.g., accuracy)
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = architecture_encoding.shape[0]
    cdef float prediction = bias
    
    for i in range(D):
        prediction += architecture_encoding[i] * coefficients[i]
    
    predicted_metric_out[0] = prediction


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_gradient_importance(
    float[:, :] gradients,
    float[:] importance_out
) nogil:
    """
    Compute gradient-based importance for layer selection.
    
    Args:
        gradients: (M, N) gradient matrix
        importance_out: (M,) importance scores (L2 norm)
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = gradients.shape[0]
    cdef Py_ssize_t N = gradients.shape[1]
    cdef float norm_sq
    
    for i in range(M):
        norm_sq = 0.0
        for j in range(N):
            norm_sq += gradients[i, j] * gradients[i, j]
        importance_out[i] = sqrt(norm_sq)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_knowledge_distillation(
    float[:] teacher_logits,
    float[:] student_logits,
    float temperature,
    float[:] distillation_loss_out
) nogil:
    """
    Compute knowledge distillation loss (soft targets).
    
    Args:
        teacher_logits: (C,) teacher predictions
        student_logits: (C,) student predictions
        temperature: softmax temperature
        distillation_loss_out: (1,) KL divergence loss
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t C = teacher_logits.shape[0]
    cdef float teacher_probs[1000]
    cdef float student_probs[1000]
    cdef float teacher_sum = 0.0
    cdef float student_sum = 0.0
    cdef float loss = 0.0
    cdef float temp_inv = 1.0 / temperature
    
    # Softmax with temperature
    for i in range(C):
        if i < 1000:
            teacher_probs[i] = exp(teacher_logits[i] * temp_inv)
            student_probs[i] = exp(student_logits[i] * temp_inv)
            teacher_sum += teacher_probs[i]
            student_sum += student_probs[i]
    
    # Normalize
    for i in range(C):
        if i < 1000:
            teacher_probs[i] /= teacher_sum
            student_probs[i] /= student_sum
    
    # KL divergence
    for i in range(C):
        if i < 1000 and teacher_probs[i] > 1e-8:
            loss += teacher_probs[i] * log(teacher_probs[i] / (student_probs[i] + 1e-8))
    
    distillation_loss_out[0] = loss


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void optimize_learning_rate_schedule(
    float initial_lr,
    int current_epoch,
    int total_epochs,
    int schedule_type,
    float[:] lr_out
) nogil:
    """
    Compute learning rate with scheduling.
    
    Args:
        initial_lr: starting learning rate
        current_epoch: current epoch
        total_epochs: total training epochs
        schedule_type: 0=constant, 1=linear decay, 2=cosine, 3=exponential
        lr_out: (1,) computed learning rate
    """
    cdef float progress = <float>current_epoch / <float>total_epochs
    cdef float lr = initial_lr
    
    if schedule_type == 1:
        # Linear decay
        lr = initial_lr * (1.0 - progress)
    elif schedule_type == 2:
        # Cosine annealing
        lr = 0.5 * initial_lr * (1.0 + sin(3.14159265 * (1.0 - progress)))
    elif schedule_type == 3:
        # Exponential decay
        lr = initial_lr * exp(-3.0 * progress)
    
    if lr < 1e-8:
        lr = 1e-8
    
    lr_out[0] = lr


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_architecture_similarity(
    float[:] encoding1,
    float[:] encoding2,
    float[:] similarity_out
) nogil:
    """
    Compute similarity between two architectures (cosine).
    
    Args:
        encoding1: (D,) first architecture
        encoding2: (D,) second architecture
        similarity_out: (1,) similarity [0, 1]
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = encoding1.shape[0]
    cdef float dot = 0.0
    cdef float norm1 = 0.0
    cdef float norm2 = 0.0
    
    for i in range(D):
        dot += encoding1[i] * encoding2[i]
        norm1 += encoding1[i] * encoding1[i]
        norm2 += encoding2[i] * encoding2[i]
    
    if norm1 > 0.0 and norm2 > 0.0:
        similarity_out[0] = dot / sqrt(norm1 * norm2)
    else:
        similarity_out[0] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void select_best_architectures(
    float[:] performance_scores,
    int num_to_select,
    int[:] selected_indices_out
) nogil:
    """
    Select top-k architectures by performance.
    
    Args:
        performance_scores: (N,) performance metrics
        num_to_select: k
        selected_indices_out: (k,) indices of best architectures
    """
    cdef Py_ssize_t i, j, best_idx
    cdef Py_ssize_t N = performance_scores.shape[0]
    cdef float best_score
    cdef int selected[1000]
    
    # Initialize
    for i in range(1000):
        selected[i] = 0
    
    # Greedy selection
    for i in range(num_to_select):
        best_score = -1e9
        best_idx = 0
        
        for j in range(N):
            if selected[j] == 0 and performance_scores[j] > best_score:
                best_score = performance_scores[j]
                best_idx = j
        
        selected[best_idx] = 1
        selected_indices_out[i] = best_idx
