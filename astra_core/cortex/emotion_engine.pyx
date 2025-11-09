# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: embedsignature=True

"""
ASTRA Emotion Engine - Numeric Emotional Fields
================================================

Not "feelings," but measurable emotional vector fields:
- Harmonic resonance scores
- Emotional state gradients
- Stability/instability metrics
- Attention curves over time
- Tension dynamics

Like a heart, beating below consciousness.
"""

import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport sqrt, exp, sin, cos, atan2, fabs, tanh, log
from cython.parallel import prange


# ============================================================================
# EMOTIONAL VECTOR FIELD DYNAMICS
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_emotional_gradient(
    double[:] emotion_state,
    double[:] target_state,
    double[:] gradient_out,
    double alpha=0.1
) nogil:
    """
    Compute emotional state gradient (rate of change).
    
    gradient = alpha * (target - current)
    
    Args:
        emotion_state: (D,) current emotional state vector
        target_state: (D,) desired emotional state
        gradient_out: (D,) output gradient
        alpha: learning rate / attraction strength
    
    Emotional dimensions might be:
    - Valence (positive/negative)
    - Arousal (calm/excited)
    - Tension (relaxed/stressed)
    - Focus (scattered/concentrated)
    - Confidence (uncertain/certain)
    """
    cdef Py_ssize_t i, D = emotion_state.shape[0]
    cdef double delta
    
    for i in range(D):
        delta = target_state[i] - emotion_state[i]
        gradient_out[i] = alpha * delta


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void update_emotional_state(
    double[:] emotion_state,
    double[:] gradient,
    double dt,
    double[:] state_out,
    double damping=0.95
) nogil:
    """
    Update emotional state with momentum and damping.
    
    state_new = state + gradient * dt
    state_new *= damping (decay to neutral)
    
    Args:
        emotion_state: (D,) current state
        gradient: (D,) gradient from compute_emotional_gradient
        dt: time step
        state_out: (D,) updated state
        damping: decay factor (emotional states fade over time)
    """
    cdef Py_ssize_t i, D = emotion_state.shape[0]
    cdef double new_val
    
    for i in range(D):
        new_val = emotion_state[i] + gradient[i] * dt
        state_out[i] = new_val * damping


# ============================================================================
# HARMONIC RESONANCE (Musical/Emotional Coherence)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double compute_harmonic_resonance(
    double[:] signal_a,
    double[:] signal_b,
    double[:] frequencies
) nogil:
    """
    Compute harmonic resonance between two signals.
    
    Measures how well two emotional/audio signals align harmonically.
    Uses frequency-weighted correlation.
    
    Args:
        signal_a: (N,) first signal
        signal_b: (N,) second signal
        frequencies: (N,) frequency weights
    
    Returns:
        Resonance score [0, 1]
    """
    cdef Py_ssize_t i, N = signal_a.shape[0]
    cdef double cross_energy = 0.0
    cdef double energy_a = 0.0
    cdef double energy_b = 0.0
    cdef double freq_weight
    
    for i in range(N):
        freq_weight = frequencies[i]
        cross_energy += signal_a[i] * signal_b[i] * freq_weight
        energy_a += signal_a[i] * signal_a[i] * freq_weight
        energy_b += signal_b[i] * signal_b[i] * freq_weight
    
    if energy_a > 1e-12 and energy_b > 1e-12:
        return cross_energy / sqrt(energy_a * energy_b)
    return 0.0


# ============================================================================
# TENSION CURVES (Emotional Dynamics Over Time)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_tension_curve(
    double[:] emotional_trajectory,
    double[:] tension_out,
    double window_size=5.0
) nogil:
    """
    Compute tension curve from emotional trajectory.
    
    Tension = variance in emotional state over sliding window
    High variance = high tension
    
    Args:
        emotional_trajectory: (T,) emotional state over time
        tension_out: (T,) tension values
        window_size: analysis window size
    """
    cdef Py_ssize_t i, j, T = emotional_trajectory.shape[0]
    cdef Py_ssize_t window = <Py_ssize_t>window_size
    cdef double mean, variance, delta
    cdef Py_ssize_t start, end, count
    
    for i in range(T):
        # Compute local mean and variance
        start = i - window if i >= window else 0
        end = i + window if i + window < T else T
        
        mean = 0.0
        count = end - start
        for j in range(start, end):
            mean += emotional_trajectory[j]
        mean /= <double>count
        
        variance = 0.0
        for j in range(start, end):
            delta = emotional_trajectory[j] - mean
            variance += delta * delta
        variance /= <double>count
        
        tension_out[i] = sqrt(variance)


# ============================================================================
# EMOTIONAL STABILITY METRICS
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double compute_emotional_stability(
    double[:] emotion_state,
    double[:] baseline_state
) nogil:
    """
    Measure stability of emotional state relative to baseline.
    
    stability = exp(-distance_from_baseline)
    
    Args:
        emotion_state: (D,) current emotional state
        baseline_state: (D,) neutral/baseline state
    
    Returns:
        Stability score [0, 1] (1 = perfectly stable)
    """
    cdef Py_ssize_t i, D = emotion_state.shape[0]
    cdef double distance = 0.0
    cdef double delta
    
    for i in range(D):
        delta = emotion_state[i] - baseline_state[i]
        distance += delta * delta
    
    distance = sqrt(distance)
    return exp(-distance)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_instability_field(
    double[:, :] emotional_trajectory,
    double[:] instability_out
) nogil:
    """
    Compute instability at each time point.
    
    Instability = rate of change + variance
    
    Args:
        emotional_trajectory: (T, D) emotional states over time
        instability_out: (T,) instability scores
    """
    cdef Py_ssize_t t, d
    cdef Py_ssize_t T = emotional_trajectory.shape[0]
    cdef Py_ssize_t D = emotional_trajectory.shape[1]
    cdef double velocity, delta
    
    for t in range(T):
        velocity = 0.0
        
        # Compute velocity (rate of change)
        if t > 0:
            for d in range(D):
                delta = emotional_trajectory[t, d] - emotional_trajectory[t-1, d]
                velocity += delta * delta
        
        instability_out[t] = sqrt(velocity)


# ============================================================================
# ATTENTION CURVES (Focus Dynamics)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_attention_curve(
    double[:] importance_scores,
    double[:] attention_out,
    double temperature=1.0
) nogil:
    """
    Convert importance scores to attention distribution.
    
    Uses softmax with temperature scaling.
    
    Args:
        importance_scores: (N,) raw importance/salience scores
        attention_out: (N,) normalized attention weights
        temperature: higher = more uniform, lower = more peaked
    """
    cdef Py_ssize_t i, N = importance_scores.shape[0]
    cdef double max_score = importance_scores[0]
    cdef double sum_exp = 0.0
    cdef double scaled_score
    
    # Find max for numerical stability
    for i in range(1, N):
        if importance_scores[i] > max_score:
            max_score = importance_scores[i]
    
    # Compute softmax
    for i in range(N):
        scaled_score = (importance_scores[i] - max_score) / temperature
        attention_out[i] = exp(scaled_score)
        sum_exp += attention_out[i]
    
    # Normalize
    for i in range(N):
        attention_out[i] /= sum_exp


# ============================================================================
# EMOTIONAL RESONANCE FIELD (Multi-agent Synchronization)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_resonance_field(
    double[:, :] agent_states,
    double[:, :] resonance_matrix
) nogil:
    """
    Compute pairwise emotional resonance between agents.
    
    resonance[i, j] = correlation(agent_i_state, agent_j_state)
    
    Args:
        agent_states: (num_agents, D) emotional states
        resonance_matrix: (num_agents, num_agents) output resonance
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t num_agents = agent_states.shape[0]
    cdef Py_ssize_t D = agent_states.shape[1]
    cdef double dot_prod, norm_i, norm_j
    
    for i in range(num_agents):
        resonance_matrix[i, i] = 1.0
        
        for j in range(i + 1, num_agents):
            dot_prod = 0.0
            norm_i = 0.0
            norm_j = 0.0
            
            for k in range(D):
                dot_prod += agent_states[i, k] * agent_states[j, k]
                norm_i += agent_states[i, k] * agent_states[i, k]
                norm_j += agent_states[j, k] * agent_states[j, k]
            
            norm_i = sqrt(norm_i)
            norm_j = sqrt(norm_j)
            
            if norm_i > 1e-12 and norm_j > 1e-12:
                resonance_matrix[i, j] = dot_prod / (norm_i * norm_j)
                resonance_matrix[j, i] = resonance_matrix[i, j]
            else:
                resonance_matrix[i, j] = 0.0
                resonance_matrix[j, i] = 0.0


# ============================================================================
# EMOTIONAL MOMENTUM (Inertia in State Changes)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_emotional_momentum(
    double[:] current_state,
    double[:] velocity,
    double[:] state_out,
    double dt,
    double friction=0.9
) nogil:
    """
    Apply physics-like momentum to emotional state changes.
    
    state_new = state + velocity * dt
    velocity *= friction (damping)
    
    Args:
        current_state: (D,) current emotional state
        velocity: (D,) rate of change
        state_out: (D,) updated state
        dt: time step
        friction: velocity decay (prevents oscillation)
    """
    cdef Py_ssize_t i, D = current_state.shape[0]
    
    for i in range(D):
        state_out[i] = current_state[i] + velocity[i] * dt
        velocity[i] *= friction


# ============================================================================
# MOOD SIGNATURE (Fingerprint of Emotional Pattern)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_mood_signature(
    double[:, :] emotional_trajectory,
    double[:] signature_out
) nogil:
    """
    Compute compact mood signature from emotional trajectory.
    
    Signature = [mean, std, skew_approx, energy, peak_frequency]
    
    Args:
        emotional_trajectory: (T, D) emotional states over time
        signature_out: (5*D,) compact signature
    """
    cdef Py_ssize_t t, d
    cdef Py_ssize_t T = emotional_trajectory.shape[0]
    cdef Py_ssize_t D = emotional_trajectory.shape[1]
    cdef double mean, variance, energy, delta
    cdef Py_ssize_t idx
    
    for d in range(D):
        # Compute mean
        mean = 0.0
        for t in range(T):
            mean += emotional_trajectory[t, d]
        mean /= <double>T
        
        # Compute variance and energy
        variance = 0.0
        energy = 0.0
        for t in range(T):
            delta = emotional_trajectory[t, d] - mean
            variance += delta * delta
            energy += emotional_trajectory[t, d] * emotional_trajectory[t, d]
        variance /= <double>T
        energy /= <double>T
        
        # Store in signature
        idx = d * 5
        signature_out[idx + 0] = mean
        signature_out[idx + 1] = sqrt(variance)
        signature_out[idx + 2] = 0.0  # Placeholder for skew
        signature_out[idx + 3] = sqrt(energy)
        signature_out[idx + 4] = 0.0  # Placeholder for peak frequency


# ============================================================================
# EMOTIONAL FIELD PROPAGATION (Wave-like Dynamics)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void propagate_emotional_field(
    double[:, :] field,
    double[:, :] field_out,
    double diffusion=0.1,
    double decay=0.95
) nogil:
    """
    Propagate emotional field with diffusion and decay.
    
    Like heat diffusion, emotions spread and fade.
    
    Args:
        field: (T, D) current field
        field_out: (T, D) updated field
        diffusion: spatial diffusion rate
        decay: temporal decay rate
    """
    cdef Py_ssize_t t, d
    cdef Py_ssize_t T = field.shape[0]
    cdef Py_ssize_t D = field.shape[1]
    cdef double laplacian, new_val
    
    for t in range(1, T - 1):
        for d in range(D):
            # Compute discrete Laplacian (diffusion operator)
            laplacian = field[t-1, d] + field[t+1, d] - 2.0 * field[t, d]
            
            # Update with diffusion and decay
            new_val = field[t, d] + diffusion * laplacian
            field_out[t, d] = new_val * decay
    
    # Boundary conditions
    for d in range(D):
        field_out[0, d] = field[0, d] * decay
        field_out[T-1, d] = field[T-1, d] * decay
