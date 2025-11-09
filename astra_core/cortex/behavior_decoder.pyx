# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🔮 ASTRA Behavior Decoder — Social Oracle (Cython Acceleration)

Real-time behavior pattern recognition at C-speed:
- Sentiment trajectories
- Emotional state detection
- Social signal processing
- Deception indicators
- Engagement metrics
- Communication style analysis

Think of this as ASTRA's "social cognition module" for human interaction understanding.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, tanh, pow
from libc.string cimport memset

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_sentiment_trajectory(
    float[:] sentiment_scores,
    int window_size,
    float[:] trajectory_out
) nogil:
    """
    Compute smoothed sentiment trajectory over time.
    
    Uses exponential moving average for smoothing.
    
    Args:
        sentiment_scores: (T,) raw sentiment scores (-1 to +1)
        window_size: smoothing window size
        trajectory_out: (T,) smoothed trajectory
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = sentiment_scores.shape[0]
    cdef float alpha = 2.0 / (<float>window_size + 1.0)
    cdef float ema = 0.0
    
    if T == 0:
        return
    
    # Initialize with first value
    ema = sentiment_scores[0]
    trajectory_out[0] = ema
    
    # Exponential moving average
    for t in range(1, T):
        ema = alpha * sentiment_scores[t] + (1.0 - alpha) * ema
        trajectory_out[t] = ema


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_emotional_shifts(
    float[:] sentiment_trajectory,
    float threshold,
    int[:] shift_points_out,
    int max_shifts
) nogil:
    """
    Detect significant emotional state changes.
    
    Marks points where sentiment gradient exceeds threshold.
    
    Args:
        sentiment_trajectory: (T,) smoothed sentiment trajectory
        threshold: minimum shift magnitude to detect
        shift_points_out: (max_shifts,) output shift indices (-1 = empty)
        max_shifts: maximum shifts to track
    """
    cdef Py_ssize_t t, shift_count = 0
    cdef Py_ssize_t T = sentiment_trajectory.shape[0]
    cdef float gradient
    
    # Initialize output
    for t in range(max_shifts):
        shift_points_out[t] = -1
    
    # Detect shifts
    for t in range(1, T):
        gradient = sentiment_trajectory[t] - sentiment_trajectory[t - 1]
        
        if fabs(gradient) > threshold and shift_count < max_shifts:
            shift_points_out[shift_count] = t
            shift_count += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_engagement_score(
    float[:] response_times,
    float[:] message_lengths,
    float[:] sentiment_scores
) nogil:
    """
    Compute overall engagement metric from conversation features.
    
    High engagement:
    - Fast responses
    - Longer messages
    - Positive/active sentiment
    
    Args:
        response_times: (T,) response time in seconds
        message_lengths: (T,) character/token counts
        sentiment_scores: (T,) sentiment (-1 to +1)
        
    Returns:
        engagement_score: 0-1 (higher = more engaged)
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = response_times.shape[0]
    cdef float time_score = 0.0
    cdef float length_score = 0.0
    cdef float sentiment_score = 0.0
    cdef float avg_time, avg_length, avg_sentiment
    
    if T == 0:
        return 0.0
    
    # Compute averages
    for t in range(T):
        time_score += response_times[t]
        length_score += message_lengths[t]
        sentiment_score += sentiment_scores[t]
    
    avg_time = time_score / <float>T
    avg_length = length_score / <float>T
    avg_sentiment = sentiment_score / <float>T
    
    # Normalize components
    # Fast response (< 5s ideal, > 30s poor)
    time_score = 1.0 - (avg_time - 5.0) / 25.0
    if time_score < 0.0:
        time_score = 0.0
    elif time_score > 1.0:
        time_score = 1.0
    
    # Longer messages (50+ chars good, < 10 poor)
    length_score = (avg_length - 10.0) / 40.0
    if length_score < 0.0:
        length_score = 0.0
    elif length_score > 1.0:
        length_score = 1.0
    
    # Positive sentiment
    sentiment_score = (avg_sentiment + 1.0) / 2.0  # Map [-1,1] to [0,1]
    
    # Weighted combination
    return 0.4 * time_score + 0.3 * length_score + 0.3 * sentiment_score


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_deception_indicators(
    float[:] baseline_features,
    float[:] current_features,
    float[:] deviation_out
) nogil:
    """
    Compute behavioral deviation from baseline (potential deception).
    
    Features might include:
    - Response time variance
    - Sentence complexity
    - Hedge word frequency
    - Self-reference rate
    
    Large deviations → potential deception/stress.
    
    Args:
        baseline_features: (D,) baseline behavioral features
        current_features: (D,) current behavioral features
        deviation_out: (D,) normalized deviations
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = baseline_features.shape[0]
    cdef float baseline_std, deviation, z_score
    
    for i in range(D):
        # Simple deviation (could add more sophisticated anomaly detection)
        deviation = current_features[i] - baseline_features[i]
        
        # Normalize by baseline magnitude (avoid div by zero)
        if fabs(baseline_features[i]) > 0.001:
            deviation_out[i] = deviation / fabs(baseline_features[i])
        else:
            deviation_out[i] = deviation


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void analyze_communication_style(
    float[:] feature_vector,
    float[:] style_scores_out
) nogil:
    """
    Classify communication style from linguistic features.
    
    Styles:
    - Assertive (direct, confident)
    - Analytical (logical, detailed)
    - Expressive (emotional, colorful)
    - Cooperative (agreeable, supportive)
    
    Args:
        feature_vector: (D,) linguistic feature vector
        style_scores_out: (4,) [assertive, analytical, expressive, cooperative]
    """
    cdef float assertive, analytical, expressive, cooperative
    cdef float total
    
    # Example feature mapping (simplified)
    # Real implementation would use trained weights
    
    # Assertive: short sentences, imperative mood, low hedging
    assertive = feature_vector[0] * 0.7 + feature_vector[1] * 0.3
    
    # Analytical: complex sentences, technical vocab, high precision
    analytical = feature_vector[2] * 0.6 + feature_vector[3] * 0.4
    
    # Expressive: emotional words, exclamations, figurative language
    expressive = feature_vector[4] * 0.8 + feature_vector[5] * 0.2
    
    # Cooperative: agreeable language, questions, inclusive pronouns
    cooperative = feature_vector[6] * 0.5 + feature_vector[7] * 0.5
    
    # Softmax normalization
    total = exp(assertive) + exp(analytical) + exp(expressive) + exp(cooperative)
    
    style_scores_out[0] = exp(assertive) / total
    style_scores_out[1] = exp(analytical) / total
    style_scores_out[2] = exp(expressive) / total
    style_scores_out[3] = exp(cooperative) / total


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_attention_pattern(
    float[:] gaze_durations,
    float[:] topic_relevance,
    float[:] attention_weights_out
) nogil:
    """
    Compute attention distribution over conversation topics.
    
    Combines explicit attention (gaze) with topic relevance.
    
    Args:
        gaze_durations: (T,) time spent on each topic (seconds)
        topic_relevance: (T,) semantic relevance scores
        attention_weights_out: (T,) normalized attention weights
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = gaze_durations.shape[0]
    cdef float total_weight = 0.0
    
    # Compute combined weights
    for t in range(T):
        attention_weights_out[t] = gaze_durations[t] * topic_relevance[t]
        total_weight += attention_weights_out[t]
    
    # Normalize
    if total_weight > 0.0:
        for t in range(T):
            attention_weights_out[t] /= total_weight


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_rapport_score(
    float[:] sentiment_alignment,
    float[:] turn_taking_balance,
    float[:] linguistic_mirroring
) nogil:
    """
    Compute rapport level from interaction dynamics.
    
    High rapport:
    - Aligned sentiment trajectories
    - Balanced turn-taking
    - Linguistic mirroring (similar vocabulary/style)
    
    Args:
        sentiment_alignment: (T,) sentiment similarity over time
        turn_taking_balance: (T,) balance scores (0.5 = perfect balance)
        linguistic_mirroring: (T,) vocabulary overlap scores
        
    Returns:
        rapport_score: 0-1 (higher = better rapport)
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = sentiment_alignment.shape[0]
    cdef float avg_alignment = 0.0
    cdef float avg_balance = 0.0
    cdef float avg_mirroring = 0.0
    
    if T == 0:
        return 0.0
    
    for t in range(T):
        avg_alignment += sentiment_alignment[t]
        # Penalize imbalance (deviation from 0.5)
        avg_balance += 1.0 - 2.0 * fabs(turn_taking_balance[t] - 0.5)
        avg_mirroring += linguistic_mirroring[t]
    
    avg_alignment /= <float>T
    avg_balance /= <float>T
    avg_mirroring /= <float>T
    
    # Weighted combination
    return 0.4 * avg_alignment + 0.3 * avg_balance + 0.3 * avg_mirroring


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_power_dynamics(
    int[:] speaker_turns,
    float[:] interruption_rates,
    float[:] dominance_scores_out
) nogil:
    """
    Detect power/dominance dynamics in conversation.
    
    Dominance indicators:
    - More speaking turns
    - Higher interruption rate
    - Longer turn duration
    
    Args:
        speaker_turns: (num_speakers,) turn counts
        interruption_rates: (num_speakers,) interruption frequency
        dominance_scores_out: (num_speakers,) dominance scores
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_speakers = speaker_turns.shape[0]
    cdef int total_turns = 0
    cdef float total_score = 0.0
    
    # Compute total turns
    for i in range(num_speakers):
        total_turns += speaker_turns[i]
    
    # Compute dominance scores
    for i in range(num_speakers):
        if total_turns > 0:
            # Turn share
            dominance_scores_out[i] = (<float>speaker_turns[i] / <float>total_turns)
            # Boost from interruptions
            dominance_scores_out[i] += 0.3 * interruption_rates[i]
        else:
            dominance_scores_out[i] = 0.0
        
        total_score += dominance_scores_out[i]
    
    # Normalize
    if total_score > 0.0:
        for i in range(num_speakers):
            dominance_scores_out[i] /= total_score


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_interest_decay(
    float[:] engagement_trajectory,
    float decay_rate,
    float[:] interest_curve_out
) nogil:
    """
    Model interest decay over time (attention span modeling).
    
    Interest naturally decays unless engagement events re-boost it.
    
    Args:
        engagement_trajectory: (T,) engagement events (spikes boost interest)
        decay_rate: exponential decay rate per timestep
        interest_curve_out: (T,) predicted interest level
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = engagement_trajectory.shape[0]
    cdef float interest = 1.0  # Start at max interest
    
    for t in range(T):
        # Decay
        interest *= (1.0 - decay_rate)
        
        # Boost from engagement
        interest += engagement_trajectory[t]
        
        # Clamp to [0, 1]
        if interest > 1.0:
            interest = 1.0
        elif interest < 0.0:
            interest = 0.0
        
        interest_curve_out[t] = interest


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void extract_behavioral_signature(
    float[:] response_times,
    float[:] message_lengths,
    float[:] sentiment_scores,
    float[:] linguistic_features,
    float[:] signature_out
) nogil:
    """
    Extract compact behavioral signature (fingerprint) from interaction.
    
    Signature = [avg_response_time, std_response_time,
                 avg_message_length, std_message_length,
                 avg_sentiment, sentiment_volatility,
                 linguistic_complexity, style_marker]
    
    Args:
        response_times: (T,) response times
        message_lengths: (T,) message lengths
        sentiment_scores: (T,) sentiments
        linguistic_features: (D,) linguistic feature averages
        signature_out: (8,) compact signature
    """
    cdef Py_ssize_t t
    cdef Py_ssize_t T = response_times.shape[0]
    cdef float mean_time = 0.0, var_time = 0.0
    cdef float mean_length = 0.0, var_length = 0.0
    cdef float mean_sentiment = 0.0, var_sentiment = 0.0
    cdef float delta
    
    if T == 0:
        return
    
    # Compute means
    for t in range(T):
        mean_time += response_times[t]
        mean_length += message_lengths[t]
        mean_sentiment += sentiment_scores[t]
    
    mean_time /= <float>T
    mean_length /= <float>T
    mean_sentiment /= <float>T
    
    # Compute variances
    for t in range(T):
        delta = response_times[t] - mean_time
        var_time += delta * delta
        
        delta = message_lengths[t] - mean_length
        var_length += delta * delta
        
        delta = sentiment_scores[t] - mean_sentiment
        var_sentiment += delta * delta
    
    var_time = sqrt(var_time / <float>T)
    var_length = sqrt(var_length / <float>T)
    var_sentiment = sqrt(var_sentiment / <float>T)
    
    # Build signature
    signature_out[0] = mean_time
    signature_out[1] = var_time
    signature_out[2] = mean_length
    signature_out[3] = var_length
    signature_out[4] = mean_sentiment
    signature_out[5] = var_sentiment
    signature_out[6] = linguistic_features[0]  # Complexity
    signature_out[7] = linguistic_features[1]  # Style marker
