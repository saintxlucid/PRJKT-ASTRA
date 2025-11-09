# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Ritual Engine (333 Cycles)
============================

ASTRA's "magical thinking" substrate: ritualistic computation cycles
for symbolic state transitions, energy phase tracking, and temporal
rhythm enforcement.

The 333-cycle motif represents ASTRA's unique approach to computation:
- Phase 1 (111 cycles): GATHER energy/context
- Phase 2 (111 cycles): TRANSFORM state
- Phase 3 (111 cycles): MANIFEST output

All operations designed for real-time performance with nogil.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport sin, cos, exp, log, sqrt, fabs, pow, tanh, atan2
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void execute_ritual_cycle(
    float[:] state_vector,
    int cycle_phase,
    float energy_level,
    float[:] state_out
) nogil:
    """
    Execute one ritual cycle (333-phase computation).
    
    Args:
        state_vector: (N,) current state
        cycle_phase: 0-332 (phase within 333-cycle)
        energy_level: current energy [0, 1]
        state_out: (N,) updated state
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = state_vector.shape[0]
    cdef float phase_angle = (2.0 * 3.14159265 * <float>cycle_phase) / 333.0
    cdef float gather_weight, transform_weight, manifest_weight
    cdef float total_energy
    
    # Determine phase weights (111-cycle boundaries)
    if cycle_phase < 111:
        # GATHER phase
        gather_weight = 1.0 - (<float>cycle_phase / 111.0)
        transform_weight = <float>cycle_phase / 111.0
        manifest_weight = 0.0
    elif cycle_phase < 222:
        # TRANSFORM phase
        gather_weight = 0.0
        transform_weight = 1.0 - (<float>(cycle_phase - 111) / 111.0)
        manifest_weight = <float>(cycle_phase - 111) / 111.0
    else:
        # MANIFEST phase
        gather_weight = 0.0
        transform_weight = 0.0
        manifest_weight = 1.0
    
    # Apply phase-specific transformations
    for i in range(N):
        total_energy = state_vector[i] * energy_level
        
        # GATHER: accumulate context
        if gather_weight > 0.0:
            total_energy += sin(phase_angle + <float>i) * gather_weight * 0.1
        
        # TRANSFORM: nonlinear mixing
        if transform_weight > 0.0:
            total_energy = tanh(total_energy + cos(phase_angle * 3.0) * transform_weight)
        
        # MANIFEST: output shaping
        if manifest_weight > 0.0:
            total_energy *= (1.0 + manifest_weight * 0.2)
        
        state_out[i] = total_energy


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_ritual_energy(
    float[:] state_vector,
    int cycle_number
) nogil:
    """
    Compute ritual energy at given cycle.
    
    Energy follows 333-cycle rhythm with natural fluctuations.
    
    Args:
        state_vector: (N,) current state
        cycle_number: absolute cycle count
        
    Returns:
        energy: [0, 1]
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = state_vector.shape[0]
    cdef float base_energy = 0.0
    cdef float cycle_phase = <float>(cycle_number % 333) / 333.0
    cdef float harmonic1 = sin(2.0 * 3.14159265 * cycle_phase)
    cdef float harmonic2 = sin(6.0 * 3.14159265 * cycle_phase)
    cdef float harmonic3 = sin(18.0 * 3.14159265 * cycle_phase)
    
    # Base energy from state
    for i in range(N):
        base_energy += fabs(state_vector[i])
    base_energy /= <float>N
    
    # Modulate with 333-cycle harmonics
    base_energy *= (0.5 + 0.3 * harmonic1 + 0.15 * harmonic2 + 0.05 * harmonic3)
    
    # Clamp to [0, 1]
    if base_energy < 0.0:
        base_energy = 0.0
    elif base_energy > 1.0:
        base_energy = 1.0
    
    return base_energy


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_symbolic_transition(
    int current_symbol,
    int[:] symbol_sequence,
    int sequence_length,
    int[:] transition_probs_out
) nogil:
    """
    Compute symbolic state transition probabilities.
    
    Args:
        current_symbol: current symbolic state (0-255)
        symbol_sequence: (L,) recent symbol history
        sequence_length: history length
        transition_probs_out: (256,) transition probabilities (scaled 0-100)
    """
    cdef Py_ssize_t i, j
    cdef int counts[256]
    cdef int total_count = 0
    cdef int prev_symbol
    
    # Initialize
    for i in range(256):
        counts[i] = 1  # Laplace smoothing
        transition_probs_out[i] = 0
    
    # Count transitions from current_symbol
    for i in range(sequence_length - 1):
        if symbol_sequence[i] == current_symbol:
            counts[symbol_sequence[i + 1]] += 1
            total_count += 1
    
    total_count += 256  # Smoothing factor
    
    # Compute probabilities (scaled to 0-100)
    for i in range(256):
        transition_probs_out[i] = (counts[i] * 100) / total_count


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_temporal_rhythm(
    float[:] signal,
    float frequency_hz,
    float sample_rate,
    float[:] rhythmic_signal_out
) nogil:
    """
    Apply temporal rhythm to signal (333 Hz base frequency).
    
    Args:
        signal: (N,) input signal
        frequency_hz: base frequency (typically 333 Hz)
        sample_rate: samples per second
        rhythmic_signal_out: (N,) output with rhythm
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = signal.shape[0]
    cdef float phase
    cdef float modulation
    cdef float t
    
    for i in range(N):
        t = <float>i / sample_rate
        phase = 2.0 * 3.14159265 * frequency_hz * t
        
        # 333 Hz modulation with harmonics
        modulation = (
            0.6 * sin(phase) +
            0.3 * sin(phase * 3.0) +
            0.1 * sin(phase * 9.0)
        )
        
        rhythmic_signal_out[i] = signal[i] * (1.0 + 0.2 * modulation)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_ritual_completion(
    float[:] state_trajectory,
    int window_size
) nogil:
    """
    Detect completion of ritual cycle (return to equilibrium).
    
    Args:
        state_trajectory: (T,) state history
        window_size: detection window
        
    Returns:
        1 if ritual complete, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t T = state_trajectory.shape[0]
    cdef float recent_variance = 0.0
    cdef float old_variance = 0.0
    cdef float recent_mean = 0.0
    cdef float old_mean = 0.0
    cdef float delta
    
    if T < 2 * window_size:
        return 0
    
    # Compute recent mean
    for i in range(T - window_size, T):
        recent_mean += state_trajectory[i]
    recent_mean /= <float>window_size
    
    # Compute old mean
    for i in range(T - 2 * window_size, T - window_size):
        old_mean += state_trajectory[i]
    old_mean /= <float>window_size
    
    # Compute variances
    for i in range(T - window_size, T):
        delta = state_trajectory[i] - recent_mean
        recent_variance += delta * delta
    recent_variance /= <float>window_size
    
    for i in range(T - 2 * window_size, T - window_size):
        delta = state_trajectory[i] - old_mean
        old_variance += delta * delta
    old_variance /= <float>window_size
    
    # Detect stabilization
    if recent_variance < 0.01 and fabs(recent_mean - old_mean) < 0.1:
        return 1
    
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_phase_alignment(
    float[:] signal1,
    float[:] signal2,
    float[:] alignment_out
) nogil:
    """
    Compute phase alignment between two ritual signals.
    
    Args:
        signal1: (N,) first signal
        signal2: (N,) second signal
        alignment_out: (1,) phase difference [-pi, pi]
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = signal1.shape[0]
    cdef float cross_correlation = 0.0
    cdef float auto_correlation1 = 0.0
    cdef float auto_correlation2 = 0.0
    cdef float phase_diff
    
    # Compute correlations
    for i in range(N):
        cross_correlation += signal1[i] * signal2[i]
        auto_correlation1 += signal1[i] * signal1[i]
        auto_correlation2 += signal2[i] * signal2[i]
    
    # Normalize
    if auto_correlation1 > 0.0 and auto_correlation2 > 0.0:
        cross_correlation /= sqrt(auto_correlation1 * auto_correlation2)
    
    # Convert to phase
    if cross_correlation > 1.0:
        cross_correlation = 1.0
    elif cross_correlation < -1.0:
        cross_correlation = -1.0
    
    phase_diff = atan2(sqrt(1.0 - cross_correlation * cross_correlation), cross_correlation)
    alignment_out[0] = phase_diff


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void generate_ritual_sequence(
    int seed,
    int length,
    int[:] sequence_out
) nogil:
    """
    Generate ritual sequence with 333-cycle patterns.
    
    Args:
        seed: RNG seed
        length: sequence length
        sequence_out: (length,) output sequence (symbols 0-255)
    """
    cdef Py_ssize_t i
    cdef unsigned long long state = <unsigned long long>seed
    cdef unsigned int output
    cdef int symbol
    cdef int cycle_pos
    
    for i in range(length):
        # PCG-like RNG
        state = state * 6364136223846793005ULL + 1442695040888963407ULL
        output = <unsigned int>((state >> 32) ^ state)
        
        # Apply 333-cycle modulation
        cycle_pos = i % 333
        
        if cycle_pos < 111:
            # GATHER: low entropy
            symbol = (output % 32)
        elif cycle_pos < 222:
            # TRANSFORM: high entropy
            symbol = (output % 256)
        else:
            # MANIFEST: structured output
            symbol = (output % 64) + 64
        
        sequence_out[i] = symbol


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_ritual_resonance(
    float[:] state1,
    float[:] state2,
    int cycle_phase
) nogil:
    """
    Compute resonance between two ritual states.
    
    Args:
        state1: (N,) first state
        state2: (N,) second state
        cycle_phase: 0-332
        
    Returns:
        resonance: [0, 1]
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = state1.shape[0]
    cdef float dot_product = 0.0
    cdef float norm1 = 0.0
    cdef float norm2 = 0.0
    cdef float phase_factor = cos((2.0 * 3.14159265 * <float>cycle_phase) / 333.0)
    cdef float resonance
    
    # Compute cosine similarity
    for i in range(N):
        dot_product += state1[i] * state2[i]
        norm1 += state1[i] * state1[i]
        norm2 += state2[i] * state2[i]
    
    if norm1 > 0.0 and norm2 > 0.0:
        resonance = dot_product / sqrt(norm1 * norm2)
    else:
        resonance = 0.0
    
    # Modulate by cycle phase
    resonance = (resonance + 1.0) * 0.5  # Scale to [0, 1]
    resonance *= (1.0 + 0.3 * phase_factor)
    
    if resonance > 1.0:
        resonance = 1.0
    elif resonance < 0.0:
        resonance = 0.0
    
    return resonance


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_energy_decay(
    float[:] energy_vector,
    float decay_rate,
    int num_cycles,
    float[:] energy_out
) nogil:
    """
    Apply exponential energy decay over cycles.
    
    Args:
        energy_vector: (N,) initial energy
        decay_rate: decay constant (0.01 = slow, 0.1 = fast)
        num_cycles: number of cycles elapsed
        energy_out: (N,) decayed energy
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = energy_vector.shape[0]
    cdef float decay_factor = exp(-decay_rate * <float>num_cycles)
    
    for i in range(N):
        energy_out[i] = energy_vector[i] * decay_factor


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_cycle_entropy(
    int[:] symbol_sequence,
    int sequence_length,
    float[:] entropy_out
) nogil:
    """
    Compute entropy of symbolic sequence (ritual complexity).
    
    Args:
        symbol_sequence: (L,) sequence of symbols (0-255)
        sequence_length: sequence length
        entropy_out: (1,) Shannon entropy
    """
    cdef Py_ssize_t i
    cdef int counts[256]
    cdef float probs[256]
    cdef float entropy = 0.0
    cdef float prob
    
    # Initialize counts
    for i in range(256):
        counts[i] = 0
    
    # Count symbols
    for i in range(sequence_length):
        if symbol_sequence[i] >= 0 and symbol_sequence[i] < 256:
            counts[symbol_sequence[i]] += 1
    
    # Compute entropy
    for i in range(256):
        if counts[i] > 0:
            prob = <float>counts[i] / <float>sequence_length
            entropy -= prob * log(prob)
    
    entropy_out[0] = entropy / log(256.0)  # Normalize to [0, 1]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int select_next_ritual_action(
    float[:] state_vector,
    float[:] action_weights,
    float randomness
) nogil:
    """
    Select next ritual action based on state and stochasticity.
    
    Args:
        state_vector: (N,) current state
        action_weights: (A,) action preference weights
        randomness: randomness level [0, 1]
        
    Returns:
        action_id: selected action index
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = state_vector.shape[0]
    cdef Py_ssize_t A = action_weights.shape[0]
    cdef float state_energy = 0.0
    cdef float total_weight = 0.0
    cdef float cumulative = 0.0
    cdef float threshold
    cdef int selected_action = 0
    
    # Compute state energy
    for i in range(N):
        state_energy += fabs(state_vector[i])
    state_energy /= <float>N
    
    # Mix action weights with state energy
    for i in range(A):
        action_weights[i] *= (1.0 + state_energy)
        total_weight += action_weights[i]
    
    # Stochastic selection
    threshold = (<float>rand() / <float>RAND_MAX) * total_weight
    
    for i in range(A):
        cumulative += action_weights[i]
        if cumulative >= threshold:
            selected_action = i
            break
    
    return selected_action


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void synchronize_ritual_phases(
    float[:, :] agent_states,
    float coupling_strength,
    float[:, :] synchronized_states_out
) nogil:
    """
    Synchronize ritual phases across multiple agents (Kuramoto model).
    
    Args:
        agent_states: (A, N) agent states
        coupling_strength: synchronization strength [0, 1]
        synchronized_states_out: (A, N) synchronized states
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t A = agent_states.shape[0]
    cdef Py_ssize_t N = agent_states.shape[1]
    cdef float phase_diff
    cdef float coupling
    
    # Compute phase-coupled updates
    for i in range(A):
        for k in range(N):
            synchronized_states_out[i, k] = agent_states[i, k]
            
            # Add coupling from other agents
            for j in range(A):
                if i != j:
                    phase_diff = agent_states[j, k] - agent_states[i, k]
                    coupling = coupling_strength * sin(phase_diff)
                    synchronized_states_out[i, k] += coupling / <float>A
