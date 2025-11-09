# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🧬 ASTRA Evolution Kernel — Genetic Neural Style Iteration (Cython Acceleration)

Model merging and evolution at C-speed:
- Weight interpolation (SLERP, linear, spherical)
- LoRA mutation strategies
- Genetic crossover for model breeding
- Fitness evaluation for model selection
- Population-based training acceleration
- Neural architecture search primitives

Think of this as ASTRA's "genetic laboratory" for evolving better models.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, sin, cos, acos, pow
from libc.stdlib cimport rand, RAND_MAX, srand
from libc.string cimport memcpy

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void linear_interpolate_weights(
    float[:] weights_a,
    float[:] weights_b,
    float alpha,
    float[:] weights_out
) nogil:
    """
    Linear interpolation between two weight vectors.
    
    weights_out = (1 - alpha) * weights_a + alpha * weights_b
    
    Args:
        weights_a: (D,) first weight vector
        weights_b: (D,) second weight vector
        alpha: interpolation factor (0=A, 1=B)
        weights_out: (D,) interpolated weights
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = weights_a.shape[0]
    cdef float beta = 1.0 - alpha
    
    for i in range(D):
        weights_out[i] = beta * weights_a[i] + alpha * weights_b[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void slerp_interpolate_weights(
    float[:] weights_a,
    float[:] weights_b,
    float alpha,
    float[:] weights_out
) nogil:
    """
    Spherical linear interpolation (SLERP) between weight vectors.
    
    Better than linear for preserving magnitude in embedding spaces.
    
    Args:
        weights_a: (D,) first weight vector
        weights_b: (D,) second weight vector
        alpha: interpolation factor (0=A, 1=B)
        weights_out: (D,) interpolated weights
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = weights_a.shape[0]
    cdef float dot = 0.0
    cdef float norm_a = 0.0, norm_b = 0.0
    cdef float cos_omega, sin_omega, omega
    cdef float scale_a, scale_b
    
    # Compute norms and dot product
    for i in range(D):
        norm_a += weights_a[i] * weights_a[i]
        norm_b += weights_b[i] * weights_b[i]
        dot += weights_a[i] * weights_b[i]
    
    norm_a = sqrt(norm_a)
    norm_b = sqrt(norm_b)
    
    if norm_a < 1e-8 or norm_b < 1e-8:
        # Degenerate case: fallback to linear
        linear_interpolate_weights(weights_a, weights_b, alpha, weights_out)
        return
    
    # Normalize dot product
    cos_omega = dot / (norm_a * norm_b)
    
    # Clamp to avoid numerical issues
    if cos_omega < -1.0:
        cos_omega = -1.0
    elif cos_omega > 1.0:
        cos_omega = 1.0
    
    omega = acos(cos_omega)
    sin_omega = sin(omega)
    
    if fabs(sin_omega) < 1e-6:
        # Nearly parallel: fallback to linear
        linear_interpolate_weights(weights_a, weights_b, alpha, weights_out)
        return
    
    # SLERP formula
    scale_a = sin((1.0 - alpha) * omega) / sin_omega
    scale_b = sin(alpha * omega) / sin_omega
    
    for i in range(D):
        weights_out[i] = scale_a * weights_a[i] + scale_b * weights_b[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void mutate_weights_gaussian(
    float[:] weights,
    float mutation_rate,
    float mutation_strength,
    float[:] weights_out
) nogil:
    """
    Apply Gaussian mutation to weights (for evolutionary algorithms).
    
    Each weight has `mutation_rate` probability of being mutated.
    Mutations are drawn from N(0, mutation_strength).
    
    Args:
        weights: (D,) original weights
        mutation_rate: probability of mutating each weight (0-1)
        mutation_strength: standard deviation of mutation
        weights_out: (D,) mutated weights
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = weights.shape[0]
    cdef float rand_val, mutation
    
    for i in range(D):
        weights_out[i] = weights[i]
        
        rand_val = <float>rand() / <float>RAND_MAX
        if rand_val < mutation_rate:
            # Box-Muller transform for Gaussian noise
            rand_val = <float>rand() / <float>RAND_MAX
            mutation = sqrt(-2.0 * log(rand_val + 1e-10)) * sin(6.28318530718 * <float>rand() / <float>RAND_MAX)
            weights_out[i] += mutation_strength * mutation


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void crossover_uniform(
    float[:] parent_a,
    float[:] parent_b,
    float crossover_rate,
    float[:] child_out
) nogil:
    """
    Uniform crossover: randomly select each gene from parent A or B.
    
    Args:
        parent_a: (D,) first parent weights
        parent_b: (D,) second parent weights
        crossover_rate: probability of selecting from parent_b
        child_out: (D,) child weights
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = parent_a.shape[0]
    cdef float rand_val
    
    for i in range(D):
        rand_val = <float>rand() / <float>RAND_MAX
        if rand_val < crossover_rate:
            child_out[i] = parent_b[i]
        else:
            child_out[i] = parent_a[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void crossover_single_point(
    float[:] parent_a,
    float[:] parent_b,
    int crossover_point,
    float[:] child_out
) nogil:
    """
    Single-point crossover: split at random point, combine parents.
    
    Args:
        parent_a: (D,) first parent weights
        parent_b: (D,) second parent weights
        crossover_point: split index
        child_out: (D,) child weights
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = parent_a.shape[0]
    
    for i in range(D):
        if i < crossover_point:
            child_out[i] = parent_a[i]
        else:
            child_out[i] = parent_b[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_model_distance(
    float[:] weights_a,
    float[:] weights_b,
    int distance_type=2
) nogil:
    """
    Compute distance between two weight vectors.
    
    distance_type:
    - 1: L1 (Manhattan)
    - 2: L2 (Euclidean)
    - 3: Cosine distance
    
    Args:
        weights_a: (D,) first weight vector
        weights_b: (D,) second weight vector
        distance_type: type of distance metric
        
    Returns:
        distance: scalar distance
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = weights_a.shape[0]
    cdef float dist = 0.0
    cdef float dot = 0.0
    cdef float norm_a = 0.0, norm_b = 0.0
    cdef float diff
    
    if distance_type == 1:
        # L1 distance
        for i in range(D):
            diff = weights_a[i] - weights_b[i]
            dist += fabs(diff)
        return dist
    
    elif distance_type == 2:
        # L2 distance
        for i in range(D):
            diff = weights_a[i] - weights_b[i]
            dist += diff * diff
        return sqrt(dist)
    
    elif distance_type == 3:
        # Cosine distance
        for i in range(D):
            dot += weights_a[i] * weights_b[i]
            norm_a += weights_a[i] * weights_a[i]
            norm_b += weights_b[i] * weights_b[i]
        
        norm_a = sqrt(norm_a)
        norm_b = sqrt(norm_b)
        
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 1.0  # Maximum distance
        
        return 1.0 - (dot / (norm_a * norm_b))
    
    return 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_fitness_scores(
    float[:, :] population_weights,
    float[:] target_weights,
    float[:] fitness_out,
    int distance_type=2
) nogil:
    """
    Compute fitness scores for population (inverse distance to target).
    
    Args:
        population_weights: (pop_size, D) population weight vectors
        target_weights: (D,) target weight vector
        fitness_out: (pop_size,) fitness scores (higher = better)
        distance_type: distance metric type
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t pop_size = population_weights.shape[0]
    cdef float dist, max_fitness = 0.0
    
    # Compute raw fitness (inverse distance)
    for i in range(pop_size):
        dist = compute_model_distance(population_weights[i, :], target_weights, distance_type)
        fitness_out[i] = 1.0 / (1.0 + dist)  # Inverse distance
        
        if fitness_out[i] > max_fitness:
            max_fitness = fitness_out[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int tournament_selection(
    float[:] fitness_scores,
    int tournament_size
) nogil:
    """
    Tournament selection: select best from random tournament.
    
    Args:
        fitness_scores: (pop_size,) fitness scores
        tournament_size: number of candidates in tournament
        
    Returns:
        selected_idx: index of selected individual
    """
    cdef Py_ssize_t i, idx
    cdef Py_ssize_t pop_size = fitness_scores.shape[0]
    cdef float best_fitness = -1e9
    cdef int best_idx = 0
    
    for i in range(tournament_size):
        idx = rand() % pop_size
        if fitness_scores[idx] > best_fitness:
            best_fitness = fitness_scores[idx]
            best_idx = idx
    
    return best_idx


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void roulette_wheel_selection(
    float[:] fitness_scores,
    int num_selections,
    int[:] selected_indices_out
) nogil:
    """
    Roulette wheel selection: probabilistic selection based on fitness.
    
    Args:
        fitness_scores: (pop_size,) fitness scores
        num_selections: number of individuals to select
        selected_indices_out: (num_selections,) output indices
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t pop_size = fitness_scores.shape[0]
    cdef float total_fitness = 0.0
    cdef float rand_val, cumsum
    
    # Compute total fitness
    for i in range(pop_size):
        total_fitness += fitness_scores[i]
    
    # Select individuals
    for i in range(num_selections):
        rand_val = (<float>rand() / <float>RAND_MAX) * total_fitness
        cumsum = 0.0
        
        for j in range(pop_size):
            cumsum += fitness_scores[j]
            if cumsum >= rand_val:
                selected_indices_out[i] = j
                break


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void adaptive_mutation_rate(
    float[:] fitness_scores,
    float base_mutation_rate,
    float[:] mutation_rates_out
) nogil:
    """
    Adaptive mutation: increase mutation for low-fitness individuals.
    
    Args:
        fitness_scores: (pop_size,) fitness scores
        base_mutation_rate: baseline mutation rate
        mutation_rates_out: (pop_size,) adapted mutation rates
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t pop_size = fitness_scores.shape[0]
    cdef float max_fitness = 0.0
    cdef float fitness_ratio
    
    # Find max fitness
    for i in range(pop_size):
        if fitness_scores[i] > max_fitness:
            max_fitness = fitness_scores[i]
    
    # Adapt mutation rates
    for i in range(pop_size):
        if max_fitness > 0.0:
            fitness_ratio = fitness_scores[i] / max_fitness
            # Low fitness → high mutation
            mutation_rates_out[i] = base_mutation_rate * (2.0 - fitness_ratio)
        else:
            mutation_rates_out[i] = base_mutation_rate


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void elitism_selection(
    float[:] fitness_scores,
    int num_elite,
    int[:] elite_indices_out
) nogil:
    """
    Select top N individuals (elitism).
    
    Args:
        fitness_scores: (pop_size,) fitness scores
        num_elite: number of elite individuals to select
        elite_indices_out: (num_elite,) output indices
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t pop_size = fitness_scores.shape[0]
    cdef float elite_fitness
    cdef int elite_idx
    cdef int used[1024]  # Assume max pop_size = 1024
    
    # Initialize used flags
    for i in range(1024):
        used[i] = 0
    
    # Select top k
    for k in range(num_elite):
        elite_fitness = -1e9
        elite_idx = 0
        
        for i in range(pop_size):
            if used[i] == 0 and fitness_scores[i] > elite_fitness:
                elite_fitness = fitness_scores[i]
                elite_idx = i
        
        elite_indices_out[k] = elite_idx
        used[elite_idx] = 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_diversity_metric(
    float[:, :] population_weights,
    float[:] diversity_out
) nogil:
    """
    Compute population diversity (average pairwise distance).
    
    Args:
        population_weights: (pop_size, D) population weights
        diversity_out: (1,) output diversity score
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t pop_size = population_weights.shape[0]
    cdef float total_distance = 0.0
    cdef int num_pairs = 0
    
    # Compute average pairwise distance
    for i in range(pop_size):
        for j in range(i + 1, pop_size):
            total_distance += compute_model_distance(
                population_weights[i, :],
                population_weights[j, :],
                2  # L2 distance
            )
            num_pairs += 1
    
    if num_pairs > 0:
        diversity_out[0] = total_distance / <float>num_pairs
    else:
        diversity_out[0] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_lora_delta(
    float[:] base_weights,
    float[:] lora_a,
    float[:] lora_b,
    float alpha,
    float[:] weights_out
) nogil:
    """
    Apply LoRA (Low-Rank Adaptation) delta to base weights.
    
    weights_out = base_weights + alpha * (lora_a @ lora_b)
    
    Args:
        base_weights: (D,) base model weights
        lora_a: (r,) LoRA matrix A (low-rank)
        lora_b: (r,) LoRA matrix B (low-rank)
        alpha: LoRA scaling factor
        weights_out: (D,) output weights
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t D = base_weights.shape[0]
    cdef Py_ssize_t r = lora_a.shape[0]
    cdef float delta
    
    # Copy base weights
    for i in range(D):
        weights_out[i] = base_weights[i]
    
    # Add LoRA delta (simplified: assumes flattened matrices)
    # In practice, this would be matrix multiplication
    for i in range(D):
        delta = 0.0
        for j in range(r):
            delta += lora_a[j] * lora_b[j]  # Simplified
        weights_out[i] += alpha * delta / <float>r


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void merge_lora_adapters(
    float[:] lora_a1,
    float[:] lora_b1,
    float[:] lora_a2,
    float[:] lora_b2,
    float weight1,
    float weight2,
    float[:] lora_a_out,
    float[:] lora_b_out
) nogil:
    """
    Merge two LoRA adapters with weighted combination.
    
    Args:
        lora_a1, lora_b1: (r,) first LoRA adapter
        lora_a2, lora_b2: (r,) second LoRA adapter
        weight1, weight2: mixing weights
        lora_a_out, lora_b_out: (r,) merged adapter
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t r = lora_a1.shape[0]
    
    for i in range(r):
        lora_a_out[i] = weight1 * lora_a1[i] + weight2 * lora_a2[i]
        lora_b_out[i] = weight1 * lora_b1[i] + weight2 * lora_b2[i]
