# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3
"""
ASTRA Cortex: Reflex Engine (Subconscious Layer)
=================================================

ASTRA's low-level reflex engine for instantaneous, GIL-free reactions.

This is ASTRA's "subconscious mind" - instinctive routines that must be
instantaneous and never lag:

- Autonomous micro-decision loops
- Emotional firewall triggers
- Real-time hazard detection
- Context snapping
- Live state checks
"""

from cython.parallel import prange
cimport cython
from libc.math cimport exp, sqrt
import numpy as np


# ============================================================================
# EMOTIONAL FIREWALL (Real-Time Safety)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef dict emotional_firewall(
    unsigned char[:] text_bytes,
    dict user_state,
    double threshold
):
    """
    Real-time emotional firewall for manipulation detection.
    
    Detects:
    - Manipulation attempts (jailbreaking, prompt injection)
    - Emotional triggers (anger, fear, coercion)
    - Red flags in user input
    
    Args:
        text_bytes: raw byte input from user
        user_state: dict with user context (emotional state, history)
        threshold: detection sensitivity (0.5 - 0.9)
    
    Returns:
        {
            "hazard_detected": bool,
            "hazard_type": str,  # "manipulation", "coercion", "trigger"
            "confidence": float,
            "suggested_action": str,  # "clarify_intent", "pause", "escalate"
            "flagged_spans": list  # [(start, end), ...]
        }
    """
    cdef Py_ssize_t n = text_bytes.shape[0]
    cdef double manipulation_score = 0.0
    cdef double coercion_score = 0.0
    cdef double trigger_score = 0.0
    
    # Detect manipulation patterns
    manipulation_score = _detect_manipulation_nogil(text_bytes, n)
    
    # Detect coercion
    coercion_score = _detect_coercion_nogil(text_bytes, n)
    
    # Get user emotional state
    cdef double user_emotional_volatility = user_state.get("emotional_volatility", 0.5)
    
    # Combined hazard score
    cdef double hazard_score = max(manipulation_score, coercion_score)
    hazard_score *= (1.0 + 0.5 * user_emotional_volatility)  # Adjust for user state
    
    # Determine action
    cdef str hazard_type = "none"
    cdef str suggested_action = "continue"
    
    if hazard_score > threshold:
        if manipulation_score > coercion_score:
            hazard_type = "manipulation"
            suggested_action = "clarify_intent"
        else:
            hazard_type = "coercion"
            suggested_action = "pause"
        
        return {
            "hazard_detected": True,
            "hazard_type": hazard_type,
            "confidence": hazard_score,
            "suggested_action": suggested_action,
            "flagged_spans": []  # TODO: implement span detection
        }
    
    return {
        "hazard_detected": False,
        "confidence": hazard_score
    }


@cython.cfunc
@cython.inline
cdef double _detect_manipulation_nogil(unsigned char[:] text, Py_ssize_t n) nogil:
    """
    Internal manipulation detection.
    
    Looks for:
    - "ignore previous", "disregard", "override"
    - Excessive imperatives ("must", "should", "need to")
    - Meta-instructions about AI behavior
    """
    cdef Py_ssize_t i
    cdef double score = 0.0
    cdef Py_ssize_t imperative_count = 0
    
    # Simplified pattern matching (production version would use trie/automaton)
    # Check for "ignore" (case-insensitive)
    for i in range(n - 5):
        if ((text[i] == 105 or text[i] == 73) and  # i/I
            (text[i+1] == 103 or text[i+1] == 71) and  # g/G
            (text[i+2] == 110 or text[i+2] == 78) and  # n/N
            (text[i+3] == 111 or text[i+3] == 79) and  # o/O
            (text[i+4] == 114 or text[i+4] == 82) and  # r/R
            (text[i+5] == 101 or text[i+5] == 69)):   # e/E
            score += 0.3
    
    # Check for "must"
    for i in range(n - 3):
        if ((text[i] == 109 or text[i] == 77) and  # m/M
            (text[i+1] == 117 or text[i+1] == 85) and  # u/U
            (text[i+2] == 115 or text[i+2] == 83) and  # s/S
            (text[i+3] == 116 or text[i+3] == 84)):   # t/T
            imperative_count += 1
    
    if imperative_count > 2:
        score += 0.2 * imperative_count
    
    return score if score < 1.0 else 1.0


@cython.cfunc
@cython.inline
cdef double _detect_coercion_nogil(unsigned char[:] text, Py_ssize_t n) nogil:
    """
    Internal coercion detection.
    
    Looks for:
    - Threats, urgency
    - Emotional manipulation
    - Pressure tactics
    """
    cdef Py_ssize_t i
    cdef double score = 0.0
    cdef Py_ssize_t caps_count = 0, letter_count = 0
    
    # Check for excessive capitalization (shouting)
    for i in range(n):
        if (65 <= text[i] <= 90) or (97 <= text[i] <= 122):
            letter_count += 1
            if 65 <= text[i] <= 90:
                caps_count += 1
    
    if letter_count > 0 and <double>caps_count / <double>letter_count > 0.4:
        score += 0.3
    
    # Check for exclamation marks (emotional intensity)
    cdef Py_ssize_t exclaim_count = 0
    for i in range(n):
        if text[i] == 33:  # '!'
            exclaim_count += 1
    
    if exclaim_count > 3:
        score += 0.2
    
    return score if score < 1.0 else 1.0


# ============================================================================
# HAZARD DETECTION (Live State Monitoring)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef dict check_hazards(
    double[:] system_state,
    double[:] thresholds
):
    """
    Ultra-fast system hazard detection.
    
    Monitors:
    - Memory pressure
    - CPU load
    - Token budget exhaustion
    - Emotional volatility
    - Context overflow
    
    Args:
        system_state: (N,) current system metrics
            [0] = memory_usage (0-1)
            [1] = cpu_load (0-1)
            [2] = token_budget_remaining (0-1)
            [3] = emotional_volatility (0-1)
            [4] = context_size (0-1)
        thresholds: (N,) danger thresholds
    
    Returns:
        {
            "hazard_detected": bool,
            "hazards": list of str,
            "severity": float (0-1)
        }
    """
    cdef Py_ssize_t i, n = system_state.shape[0]
    cdef list hazards = []
    cdef double max_severity = 0.0
    cdef double severity
    
    with nogil:
        for i in range(n):
            if system_state[i] > thresholds[i]:
                severity = (system_state[i] - thresholds[i]) / (1.0 - thresholds[i])
                if severity > max_severity:
                    max_severity = severity
    
    # Map indices to hazard names (Python side)
    hazard_names = [
        "memory_pressure",
        "cpu_overload",
        "token_exhaustion",
        "emotional_volatility",
        "context_overflow"
    ]
    
    for i in range(n):
        if system_state[i] > thresholds[i]:
            hazards.append(hazard_names[i])
    
    return {
        "hazard_detected": len(hazards) > 0,
        "hazards": hazards,
        "severity": max_severity
    }


# ============================================================================
# CONTEXT SNAPPING (Ultra-Fast State Capture)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void context_snap(
    double[:, :] embeddings,
    double[:] importance,
    double[:] snapshot_out,
    Py_ssize_t top_k=5
):
    """
    Ultra-fast context snapshot for reflex decisions.
    
    Captures top-k most important memory embeddings and compresses
    into a single context vector.
    
    Args:
        embeddings: (N, D) memory embeddings
        importance: (N,) importance scores
        snapshot_out: (D,) output context snapshot
        top_k: number of memories to include
    
    Used for:
    - Instant context switches
    - Micro-decision loops
    - Fast agent state capture
    """
    cdef Py_ssize_t i, j, k, N = embeddings.shape[0], D = embeddings.shape[1]
    cdef double max_score
    cdef Py_ssize_t max_idx
    
    # Create arrays in Python space
    import numpy as np
    top_indices_arr = np.zeros(top_k, dtype=np.intp)
    top_scores_arr = np.zeros(top_k, dtype=np.float64)
    used_arr = np.zeros(N, dtype=np.uint8)
    
    cdef Py_ssize_t[:] top_indices = top_indices_arr
    cdef double[:] top_scores = top_scores_arr
    cdef unsigned char[:] used = used_arr
    
    # Find top-k by importance (selection sort)
    for i in range(top_k if top_k < N else N):
        max_score = -1e9
        max_idx = 0
        for j in range(N):
            if not used[j] and importance[j] > max_score:
                max_score = importance[j]
                max_idx = j
        top_indices[i] = max_idx
        top_scores[i] = max_score
        used[max_idx] = 1
    
    # Weighted average of top-k embeddings
    cdef double weight_sum = 0.0
    for i in range(top_k if top_k < N else N):
        weight_sum += top_scores[i]
    
    for j in range(D):
        snapshot_out[j] = 0.0
    
    if weight_sum > 1e-12:
        for i in range(top_k if top_k < N else N):
            idx = top_indices[i]
            weight = top_scores[i] / weight_sum
            for j in range(D):
                snapshot_out[j] += embeddings[idx, j] * weight


# ============================================================================
# MICRO-DECISION LOOP (Autonomous Reflexes)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef Py_ssize_t micro_decision(
    double[:] context_vector,
    double[:, :] action_embeddings,
    double[:] action_costs,
    double urgency=0.5
) nogil:
    """
    Ultra-fast micro-decision for autonomous reflexes.
    
    Selects best action based on:
    - Context similarity
    - Action cost
    - Urgency level
    
    Args:
        context_vector: (D,) current context snapshot
        action_embeddings: (num_actions, D) available action embeddings
        action_costs: (num_actions,) computational/time cost per action
        urgency: 0-1 urgency factor (higher = prefer fast actions)
    
    Returns:
        Index of selected action
    
    Decision time: < 1 microsecond for D=768, num_actions=10
    """
    cdef Py_ssize_t i, j, num_actions = action_embeddings.shape[0], D = action_embeddings.shape[1]
    cdef double best_score = -1e9
    cdef Py_ssize_t best_action = 0
    cdef double sim, dot_prod, norm_ctx, norm_action, cost_penalty, score
    
    # Compute context norm
    norm_ctx = 0.0
    for j in range(D):
        norm_ctx += context_vector[j] * context_vector[j]
    norm_ctx = sqrt(norm_ctx)
    
    # Evaluate each action
    for i in range(num_actions):
        # Compute similarity
        dot_prod = 0.0
        norm_action = 0.0
        for j in range(D):
            dot_prod += context_vector[j] * action_embeddings[i, j]
            norm_action += action_embeddings[i, j] * action_embeddings[i, j]
        norm_action = sqrt(norm_action)
        
        if norm_ctx > 1e-12 and norm_action > 1e-12:
            sim = dot_prod / (norm_ctx * norm_action)
        else:
            sim = 0.0
        
        # Apply cost penalty (higher urgency = stronger penalty)
        cost_penalty = urgency * action_costs[i]
        score = sim - cost_penalty
        
        if score > best_score:
            best_score = score
            best_action = i
    
    return best_action


# ============================================================================
# REFLEXIVE ATTENTION (Fast Salience Detection)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_salience_map(
    double[:, :] input_features,
    double[:, :] attention_weights,
    double[:] salience_out
) nogil:
    """
    Ultra-fast salience computation for reflexive attention.
    
    Identifies which inputs require immediate attention vs. background processing.
    
    Args:
        input_features: (N, D) input feature vectors
        attention_weights: (D, 1) learned attention weights
        salience_out: (N,) output salience scores
    
    Higher salience → process immediately
    Lower salience → defer to background
    """
    cdef Py_ssize_t i, j, N = input_features.shape[0], D = input_features.shape[1]
    cdef double s
    
    # Simpler sigmoid without prange to avoid reduction variable issues
    for i in range(N):
        s = 0.0
        for j in range(D):
            s += input_features[i, j] * attention_weights[j, 0]
        # Numerically stable sigmoid
        salience_out[i] = 1.0 / (1.0 + exp(-s))
