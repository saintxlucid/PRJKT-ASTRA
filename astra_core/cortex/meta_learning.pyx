# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Meta-Learning Kernel
=====================

Few-shot learning primitives, gradient-based meta-learning (MAML),
and task embedding generation at C-speed.

Key operations:
- Task similarity computation
- Prototypical networks
- MAML inner/outer loop utilities
- Task embedding
- Support set selection
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_prototypes(
    float[:, :] support_features,
    int[:] support_labels,
    int num_classes,
    float[:, :] prototypes_out
) nogil:
    """
    Compute class prototypes (mean of support examples per class).
    
    Args:
        support_features: (N, D) support set features
        support_labels: (N,) class labels
        num_classes: number of classes
        prototypes_out: (C, D) class prototypes
    """
    cdef Py_ssize_t i, k, c
    cdef Py_ssize_t N = support_features.shape[0]
    cdef Py_ssize_t D = support_features.shape[1]
    cdef int counts[256]
    
    # Initialize
    for c in range(256):
        counts[c] = 0
    for c in range(num_classes):
        for k in range(D):
            prototypes_out[c, k] = 0.0
    
    # Sum features per class
    for i in range(N):
        c = support_labels[i]
        if c < num_classes:
            for k in range(D):
                prototypes_out[c, k] += support_features[i, k]
            counts[c] += 1
    
    # Average
    for c in range(num_classes):
        if counts[c] > 0:
            for k in range(D):
                prototypes_out[c, k] /= <float>counts[c]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void classify_by_prototype(
    float[:, :] query_features,
    float[:, :] prototypes,
    int num_classes,
    int[:] predictions_out
) nogil:
    """
    Classify queries using nearest prototype (prototypical networks).
    
    Args:
        query_features: (M, D) query set features
        prototypes: (C, D) class prototypes
        num_classes: number of classes
        predictions_out: (M,) predicted class labels
    """
    cdef Py_ssize_t i, c, k
    cdef Py_ssize_t M = query_features.shape[0]
    cdef Py_ssize_t D = query_features.shape[1]
    cdef float min_distance, distance, delta
    cdef int best_class
    
    for i in range(M):
        min_distance = 1e9
        best_class = 0
        
        for c in range(num_classes):
            distance = 0.0
            for k in range(D):
                delta = query_features[i, k] - prototypes[c, k]
                distance += delta * delta
            distance = sqrt(distance)
            
            if distance < min_distance:
                min_distance = distance
                best_class = c
        
        predictions_out[i] = best_class


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_task_embedding(
    float[:, :] task_features,
    int num_examples,
    float[:] embedding_out
) nogil:
    """
    Compute task embedding (mean feature vector).
    
    Args:
        task_features: (N, D) features from task examples
        num_examples: number of examples
        embedding_out: (D,) task embedding
    """
    cdef Py_ssize_t i, k
    cdef Py_ssize_t D = task_features.shape[1]
    
    # Initialize
    for k in range(D):
        embedding_out[k] = 0.0
    
    # Sum
    for i in range(num_examples):
        for k in range(D):
            embedding_out[k] += task_features[i, k]
    
    # Average
    for k in range(D):
        embedding_out[k] /= <float>num_examples


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_task_similarity(
    float[:] task_embedding1,
    float[:] task_embedding2
) nogil:
    """
    Compute similarity between two tasks (cosine similarity).
    
    Args:
        task_embedding1: (D,) first task embedding
        task_embedding2: (D,) second task embedding
        
    Returns:
        similarity: [0, 1]
    """
    cdef Py_ssize_t k
    cdef Py_ssize_t D = task_embedding1.shape[0]
    cdef float dot = 0.0
    cdef float norm1 = 0.0
    cdef float norm2 = 0.0
    
    for k in range(D):
        dot += task_embedding1[k] * task_embedding2[k]
        norm1 += task_embedding1[k] * task_embedding1[k]
        norm2 += task_embedding2[k] * task_embedding2[k]
    
    if norm1 > 0.0 and norm2 > 0.0:
        return dot / sqrt(norm1 * norm2)
    return 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_maml_inner_update(
    float[:, :] weights,
    float[:, :] gradients,
    float inner_lr,
    float[:, :] updated_weights_out
) nogil:
    """
    MAML inner loop: apply gradient update.
    
    Args:
        weights: (M, N) model weights
        gradients: (M, N) task-specific gradients
        inner_lr: inner learning rate
        updated_weights_out: (M, N) updated weights
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = weights.shape[0]
    cdef Py_ssize_t N = weights.shape[1]
    
    for i in range(M):
        for j in range(N):
            updated_weights_out[i, j] = weights[i, j] - inner_lr * gradients[i, j]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_meta_gradient(
    float[:, :] base_weights,
    float[:, :] adapted_weights,
    float meta_lr,
    float[:, :] meta_gradient_out
) nogil:
    """
    Compute meta-gradient (outer loop gradient in MAML).
    
    Args:
        base_weights: (M, N) pre-adaptation weights
        adapted_weights: (M, N) post-adaptation weights
        meta_lr: meta learning rate
        meta_gradient_out: (M, N) meta-gradient
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t M = base_weights.shape[0]
    cdef Py_ssize_t N = base_weights.shape[1]
    
    for i in range(M):
        for j in range(N):
            meta_gradient_out[i, j] = (adapted_weights[i, j] - base_weights[i, j]) / meta_lr


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void select_informative_support_examples(
    float[:, :] candidate_features,
    int[:] candidate_labels,
    int num_candidates,
    int shots_per_class,
    int num_classes,
    int[:] selected_indices_out
) nogil:
    """
    Select most informative support examples (diversity-based).
    
    Args:
        candidate_features: (N, D) candidate features
        candidate_labels: (N,) candidate labels
        num_candidates: number of candidates
        shots_per_class: k-shot
        num_classes: number of classes
        selected_indices_out: (C*k,) selected example indices
    """
    cdef Py_ssize_t i, j, k, c
    cdef Py_ssize_t D = candidate_features.shape[1]
    cdef int selected[1000]
    cdef float max_distance, distance, delta
    cdef int best_idx
    cdef int output_idx = 0
    
    # Initialize
    for i in range(1000):
        selected[i] = 0
    
    # Select for each class
    for c in range(num_classes):
        # Find first example of this class
        for i in range(num_candidates):
            if candidate_labels[i] == c and selected[i] == 0:
                selected[i] = 1
                selected_indices_out[output_idx] = i
                output_idx += 1
                break
        
        # Select remaining shots greedily (maximize diversity)
        for k in range(1, shots_per_class):
            max_distance = -1.0
            best_idx = -1
            
            for i in range(num_candidates):
                if candidate_labels[i] == c and selected[i] == 0:
                    # Compute min distance to selected examples
                    distance = 1e9
                    for j in range(output_idx):
                        delta = 0.0
                        for k in range(D):
                            delta += (candidate_features[i, k] - \
                                      candidate_features[selected_indices_out[j], k]) ** 2
                        delta = sqrt(delta)
                        if delta < distance:
                            distance = delta
                    
                    if distance > max_distance:
                        max_distance = distance
                        best_idx = i
            
            if best_idx >= 0:
                selected[best_idx] = 1
                selected_indices_out[output_idx] = best_idx
                output_idx += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_adaptation_loss(
    float[:] predictions,
    float[:] targets,
    int num_examples,
    float[:] loss_out
) nogil:
    """
    Compute task-specific adaptation loss (MSE).
    
    Args:
        predictions: (N,) model predictions
        targets: (N,) ground truth targets
        num_examples: number of examples
        loss_out: (1,) loss value
    """
    cdef Py_ssize_t i
    cdef float total_loss = 0.0
    cdef float error
    
    for i in range(num_examples):
        error = predictions[i] - targets[i]
        total_loss += error * error
    
    loss_out[0] = total_loss / <float>num_examples


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_episode_difficulty(
    float[:] support_features_variance,
    float[:] query_features_variance,
    int num_features,
    float[:] difficulty_out
) nogil:
    """
    Estimate episode difficulty (feature variance ratio).
    
    Args:
        support_features_variance: (D,) variance in support set
        query_features_variance: (D,) variance in query set
        num_features: feature dimensionality
        difficulty_out: (1,) difficulty score [0, inf]
    """
    cdef Py_ssize_t k
    cdef float variance_ratio = 0.0
    
    for k in range(num_features):
        if support_features_variance[k] > 1e-6:
            variance_ratio += query_features_variance[k] / support_features_variance[k]
    
    difficulty_out[0] = variance_ratio / <float>num_features


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_task_specific_normalization(
    float[:, :] features,
    int num_examples,
    float[:, :] normalized_features_out
) nogil:
    """
    Apply task-specific feature normalization (z-score).
    
    Args:
        features: (N, D) raw features
        num_examples: number of examples
        normalized_features_out: (N, D) normalized features
    """
    cdef Py_ssize_t i, k
    cdef Py_ssize_t D = features.shape[1]
    cdef float mean, std, delta
    
    for k in range(D):
        # Compute mean
        mean = 0.0
        for i in range(num_examples):
            mean += features[i, k]
        mean /= <float>num_examples
        
        # Compute std
        std = 0.0
        for i in range(num_examples):
            delta = features[i, k] - mean
            std += delta * delta
        std = sqrt(std / <float>num_examples)
        
        # Normalize
        if std > 1e-6:
            for i in range(num_examples):
                normalized_features_out[i, k] = (features[i, k] - mean) / std
        else:
            for i in range(num_examples):
                normalized_features_out[i, k] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_cross_task_transfer(
    float[:] source_task_performance,
    float[:] target_task_performance,
    int num_models,
    float[:] transfer_score_out
) nogil:
    """
    Measure transfer learning effectiveness (correlation).
    
    Args:
        source_task_performance: (M,) performance on source task
        target_task_performance: (M,) performance on target task
        num_models: number of models tested
        transfer_score_out: (1,) transfer correlation [-1, 1]
    """
    cdef Py_ssize_t i
    cdef float mean_source = 0.0
    cdef float mean_target = 0.0
    cdef float std_source = 0.0
    cdef float std_target = 0.0
    cdef float correlation = 0.0
    cdef float delta_source, delta_target
    
    # Compute means
    for i in range(num_models):
        mean_source += source_task_performance[i]
        mean_target += target_task_performance[i]
    mean_source /= <float>num_models
    mean_target /= <float>num_models
    
    # Compute stds
    for i in range(num_models):
        delta_source = source_task_performance[i] - mean_source
        delta_target = target_task_performance[i] - mean_target
        std_source += delta_source * delta_source
        std_target += delta_target * delta_target
    std_source = sqrt(std_source / <float>num_models)
    std_target = sqrt(std_target / <float>num_models)
    
    # Compute correlation
    if std_source > 1e-6 and std_target > 1e-6:
        for i in range(num_models):
            correlation += ((source_task_performance[i] - mean_source) / std_source) * \
                          ((target_task_performance[i] - mean_target) / std_target)
        transfer_score_out[0] = correlation / <float>num_models
    else:
        transfer_score_out[0] = 0.0
