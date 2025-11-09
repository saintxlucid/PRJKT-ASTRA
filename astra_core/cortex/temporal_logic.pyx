# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: nonecheck=False
# cython: cdivision=True

"""
Temporal Logic Engine
======================

Event sequence analysis, causal reasoning, and time-series pattern matching
at C-speed for ASTRA's temporal cognition.

Key operations:
- Temporal pattern detection
- Causal inference
- Event prediction
- Sequence alignment
- Anomaly detection in time series
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, sin, cos
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_temporal_pattern(
    int[:] event_sequence,
    int[:] pattern,
    int sequence_length,
    int pattern_length
) nogil:
    """
    Detect if pattern occurs in event sequence.
    
    Args:
        event_sequence: (T,) sequence of event IDs
        pattern: (P,) pattern to find
        sequence_length: length of sequence
        pattern_length: length of pattern
        
    Returns:
        index: first occurrence index, or -1 if not found
    """
    cdef Py_ssize_t i, j
    cdef int match
    
    for i in range(sequence_length - pattern_length + 1):
        match = 1
        for j in range(pattern_length):
            if event_sequence[i + j] != pattern[j]:
                match = 0
                break
        if match:
            return i
    
    return -1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_temporal_causality(
    float[:] event_times1,
    float[:] event_times2,
    int num_events1,
    int num_events2,
    float time_window,
    float[:] causality_score_out
) nogil:
    """
    Compute causal relationship strength (does event1 predict event2?).
    
    Args:
        event_times1: (N1,) timestamps of first event type
        event_times2: (N2,) timestamps of second event type
        num_events1: count of first events
        num_events2: count of second events
        time_window: max lag for causality
        causality_score_out: (1,) causality strength [0, 1]
    """
    cdef Py_ssize_t i, j
    cdef int preceded_count = 0
    cdef float time_diff
    
    for i in range(num_events1):
        for j in range(num_events2):
            time_diff = event_times2[j] - event_times1[i]
            if time_diff > 0.0 and time_diff <= time_window:
                preceded_count += 1
                break  # Count each event1 only once
    
    if num_events1 > 0:
        causality_score_out[0] = <float>preceded_count / <float>num_events1
    else:
        causality_score_out[0] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void predict_next_event(
    int[:] event_history,
    int history_length,
    int num_event_types,
    float[:] prediction_probs_out
) nogil:
    """
    Predict next event based on history (simple Markov model).
    
    Args:
        event_history: (T,) past event IDs
        history_length: length of history
        num_event_types: number of possible event types
        prediction_probs_out: (K,) probabilities for each event type
    """
    cdef Py_ssize_t i, k
    cdef int counts[256]
    cdef int total_count = 0
    cdef int prev_event
    
    # Initialize
    for k in range(256):
        counts[k] = 1  # Laplace smoothing
    
    # Count transitions from most recent event
    if history_length >= 2:
        prev_event = event_history[history_length - 1]
        
        for i in range(history_length - 1):
            if event_history[i] == prev_event:
                if event_history[i + 1] < 256:
                    counts[event_history[i + 1]] += 1
                    total_count += 1
    
    total_count += num_event_types  # Smoothing
    
    # Compute probabilities
    for k in range(num_event_types):
        prediction_probs_out[k] = <float>counts[k] / <float>total_count


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_sequence_similarity(
    int[:] sequence1,
    int[:] sequence2,
    int length1,
    int length2
) nogil:
    """
    Compute edit distance-based similarity between sequences.
    
    Args:
        sequence1: (N1,) first sequence
        sequence2: (N2,) second sequence
        length1: length of first sequence
        length2: length of second sequence
        
    Returns:
        similarity: [0, 1], 1 = identical
    """
    cdef Py_ssize_t i, j
    cdef int edit_distance[256][256]
    cdef int cost, deletion, insertion, substitution
    cdef float max_length
    
    # Dynamic programming for edit distance
    for i in range(length1 + 1):
        if i < 256:
            edit_distance[i][0] = i
    for j in range(length2 + 1):
        if j < 256:
            edit_distance[0][j] = j
    
    for i in range(1, length1 + 1):
        if i >= 256:
            break
        for j in range(1, length2 + 1):
            if j >= 256:
                break
            
            if sequence1[i - 1] == sequence2[j - 1]:
                cost = 0
            else:
                cost = 1
            
            deletion = edit_distance[i - 1][j] + 1
            insertion = edit_distance[i][j - 1] + 1
            substitution = edit_distance[i - 1][j - 1] + cost
            
            edit_distance[i][j] = deletion
            if insertion < edit_distance[i][j]:
                edit_distance[i][j] = insertion
            if substitution < edit_distance[i][j]:
                edit_distance[i][j] = substitution
    
    max_length = <float>(length1 if length1 > length2 else length2)
    if max_length > 0.0:
        return 1.0 - (<float>edit_distance[length1][length2] / max_length)
    return 1.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_anomalous_event(
    float[:] event_features,
    float[:] normal_mean,
    float[:] normal_std,
    int num_features,
    float threshold_sigma
) nogil:
    """
    Detect anomalous event (outlier detection).
    
    Args:
        event_features: (D,) feature vector of current event
        normal_mean: (D,) mean of normal events
        normal_std: (D,) standard deviation of normal events
        num_features: feature dimensionality
        threshold_sigma: anomaly threshold in standard deviations
        
    Returns:
        1 if anomalous, 0 if normal
    """
    cdef Py_ssize_t i
    cdef float z_score
    
    for i in range(num_features):
        if normal_std[i] > 1e-6:
            z_score = fabs((event_features[i] - normal_mean[i]) / normal_std[i])
            if z_score > threshold_sigma:
                return 1
    
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void extract_periodic_component(
    float[:] time_series,
    int series_length,
    int period,
    float[:] periodic_component_out
) nogil:
    """
    Extract periodic component from time series.
    
    Args:
        time_series: (T,) input time series
        series_length: length of series
        period: periodicity to extract
        periodic_component_out: (T,) periodic component
    """
    cdef Py_ssize_t i, j
    cdef float sum_val
    cdef int count
    
    for i in range(series_length):
        sum_val = 0.0
        count = 0
        
        # Average over all occurrences of same phase
        j = i % period
        while j < series_length:
            sum_val += time_series[j]
            count += 1
            j += period
        
        if count > 0:
            periodic_component_out[i] = sum_val / <float>count
        else:
            periodic_component_out[i] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_event_rate(
    float[:] event_times,
    int num_events,
    float time_window,
    float[:] rate_out
) nogil:
    """
    Compute event rate (events per time window).
    
    Args:
        event_times: (N,) sorted event timestamps
        num_events: number of events
        time_window: window size
        rate_out: (1,) events per window
    """
    cdef Py_ssize_t i, j
    cdef int max_count = 0
    cdef int count
    
    for i in range(num_events):
        count = 0
        for j in range(i, num_events):
            if event_times[j] - event_times[i] <= time_window:
                count += 1
            else:
                break
        if count > max_count:
            max_count = count
    
    if time_window > 0.0:
        rate_out[0] = <float>max_count / time_window
    else:
        rate_out[0] = 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_inter_event_intervals(
    float[:] event_times,
    int num_events,
    float[:] intervals_out
) nogil:
    """
    Compute intervals between consecutive events.
    
    Args:
        event_times: (N,) event timestamps
        num_events: number of events
        intervals_out: (N-1,) inter-event intervals
    """
    cdef Py_ssize_t i
    
    for i in range(num_events - 1):
        intervals_out[i] = event_times[i + 1] - event_times[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_temporal_drift(
    float[:] time_series,
    int series_length,
    int window_size,
    float drift_threshold
) nogil:
    """
    Detect concept drift in time series (distribution shift).
    
    Args:
        time_series: (T,) time series
        series_length: length of series
        window_size: comparison window
        drift_threshold: threshold for drift detection
        
    Returns:
        1 if drift detected, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef float early_mean = 0.0
    cdef float late_mean = 0.0
    cdef float early_var = 0.0
    cdef float late_var = 0.0
    cdef float delta
    
    if series_length < 2 * window_size:
        return 0
    
    # Early window statistics
    for i in range(window_size):
        early_mean += time_series[i]
    early_mean /= <float>window_size
    
    for i in range(window_size):
        delta = time_series[i] - early_mean
        early_var += delta * delta
    early_var /= <float>window_size
    
    # Late window statistics
    for i in range(series_length - window_size, series_length):
        late_mean += time_series[i]
    late_mean /= <float>window_size
    
    for i in range(series_length - window_size, series_length):
        delta = time_series[i] - late_mean
        late_var += delta * delta
    late_var /= <float>window_size
    
    # Detect significant shift
    if fabs(late_mean - early_mean) > drift_threshold * sqrt(early_var):
        return 1
    
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_granger_causality_score(
    float[:] series1,
    float[:] series2,
    int series_length,
    int max_lag,
    float[:] causality_out
) nogil:
    """
    Simplified Granger causality test (does series1 help predict series2?).
    
    Args:
        series1: (T,) potential cause
        series2: (T,) potential effect
        series_length: length of series
        max_lag: maximum lag to consider
        causality_out: (1,) causality score
    """
    cdef Py_ssize_t i, lag
    cdef float correlation_sum = 0.0
    cdef float mean1 = 0.0
    cdef float mean2 = 0.0
    cdef float std1 = 0.0
    cdef float std2 = 0.0
    cdef float delta1, delta2
    cdef int valid_lags = 0
    
    # Compute means
    for i in range(series_length):
        mean1 += series1[i]
        mean2 += series2[i]
    mean1 /= <float>series_length
    mean2 /= <float>series_length
    
    # Compute standard deviations
    for i in range(series_length):
        delta1 = series1[i] - mean1
        delta2 = series2[i] - mean2
        std1 += delta1 * delta1
        std2 += delta2 * delta2
    std1 = sqrt(std1 / <float>series_length)
    std2 = sqrt(std2 / <float>series_length)
    
    # Compute lagged correlations
    if std1 > 1e-6 and std2 > 1e-6:
        for lag in range(1, max_lag + 1):
            if lag < series_length:
                for i in range(series_length - lag):
                    correlation_sum += ((series1[i] - mean1) / std1) * \
                                       ((series2[i + lag] - mean2) / std2)
                valid_lags += 1
        
        if valid_lags > 0:
            causality_out[0] = fabs(correlation_sum / <float>valid_lags)
        else:
            causality_out[0] = 0.0
    else:
        causality_out[0] = 0.0
