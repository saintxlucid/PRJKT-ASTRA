# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🛡️ ASTRA Zero-Trust Guardian — Security Hardening Layer (Cython Acceleration)

Security validation at C-speed:
- Input sanitization & validation
- Rate limiting enforcement
- Anomaly detection
- Injection pattern detection
- Token budget enforcement
- Request fingerprinting
- Cryptographic verification primitives

Think of this as ASTRA's "immune system" for malicious inputs.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.math cimport exp, log, sqrt, fabs, pow
from libc.string cimport strlen, strcmp, strstr, memset
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int validate_input_length(
    int input_length,
    int min_length,
    int max_length
) nogil:
    """
    Validate input length is within acceptable bounds.
    
    Args:
        input_length: actual input length
        min_length: minimum acceptable length
        max_length: maximum acceptable length
        
    Returns:
        1 if valid, 0 if invalid
    """
    if input_length < min_length or input_length > max_length:
        return 0
    return 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_entropy(
    float[:] token_distribution
) nogil:
    """
    Compute Shannon entropy of token distribution.
    
    High entropy → diverse/normal text
    Low entropy → repetitive/suspicious patterns
    
    Args:
        token_distribution: (vocab_size,) token probability distribution
        
    Returns:
        entropy: Shannon entropy in bits
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t vocab_size = token_distribution.shape[0]
    cdef float entropy = 0.0
    cdef float p
    
    for i in range(vocab_size):
        p = token_distribution[i]
        if p > 1e-10:
            entropy -= p * log(p) / 0.693147180559945  # log(2)
    
    return entropy


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_repetition_attack(
    int[:] token_ids,
    int max_repeat_length,
    float repeat_threshold
) nogil:
    """
    Detect malicious repetition patterns in token sequence.
    
    Args:
        token_ids: (T,) token ID sequence
        max_repeat_length: maximum pattern length to check
        repeat_threshold: fraction of sequence that's repetitive
        
    Returns:
        1 if attack detected, 0 otherwise
    """
    cdef Py_ssize_t i, j, k
    cdef Py_ssize_t T = token_ids.shape[0]
    cdef int pattern_length, match_count, total_matches
    cdef float repeat_fraction
    
    # Check for exact repeating patterns
    for pattern_length in range(1, max_repeat_length + 1):
        total_matches = 0
        
        for i in range(T - pattern_length):
            match_count = 0
            
            # Check if pattern repeats (manual loop instead of range with step)
            j = i + pattern_length
            while j < T:
                if j + pattern_length > T:
                    break
                
                # Check if pattern matches
                for k in range(pattern_length):
                    if token_ids[i + k] != token_ids[j + k]:
                        break
                else:
                    match_count += 1
                
                j += pattern_length
            
            total_matches += match_count
        
        repeat_fraction = <float>total_matches / <float>T
        if repeat_fraction > repeat_threshold:
            return 1  # Attack detected
    
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_anomaly_score(
    float[:] input_features,
    float[:] baseline_mean,
    float[:] baseline_std
) nogil:
    """
    Compute anomaly score using z-score method.
    
    Args:
        input_features: (D,) input feature vector
        baseline_mean: (D,) baseline mean
        baseline_std: (D,) baseline standard deviation
        
    Returns:
        anomaly_score: higher = more anomalous
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = input_features.shape[0]
    cdef float z_score, anomaly = 0.0
    
    for i in range(D):
        if baseline_std[i] > 1e-6:
            z_score = (input_features[i] - baseline_mean[i]) / baseline_std[i]
            anomaly += z_score * z_score
        else:
            anomaly += (input_features[i] - baseline_mean[i]) * (input_features[i] - baseline_mean[i])
    
    return sqrt(anomaly / <float>D)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int check_rate_limit(
    float[:] request_timestamps,
    float current_time,
    int max_requests,
    float time_window
) nogil:
    """
    Check if rate limit is exceeded.
    
    Args:
        request_timestamps: (N,) timestamps of recent requests
        current_time: current timestamp
        max_requests: maximum allowed requests in window
        time_window: time window in seconds
        
    Returns:
        1 if rate limit OK, 0 if exceeded
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = request_timestamps.shape[0]
    cdef int count = 0
    cdef float cutoff_time = current_time - time_window
    
    for i in range(N):
        if request_timestamps[i] > cutoff_time:
            count += 1
    
    if count >= max_requests:
        return 0  # Rate limit exceeded
    return 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int enforce_token_budget(
    int tokens_used,
    int max_tokens,
    float safety_margin
) nogil:
    """
    Enforce token budget with safety margin.
    
    Args:
        tokens_used: tokens consumed so far
        max_tokens: maximum allowed tokens
        safety_margin: fraction to reserve (0.1 = 10% buffer)
        
    Returns:
        remaining_tokens: tokens remaining (or 0 if exceeded)
    """
    cdef int budget = <int>(<float>max_tokens * (1.0 - safety_margin))
    cdef int remaining = budget - tokens_used
    
    if remaining < 0:
        return 0
    return remaining


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_request_fingerprint(
    float[:] feature_vector,
    int[:] hash_indices,
    float[:] fingerprint_out
) nogil:
    """
    Compute LSH-style fingerprint for request deduplication.
    
    Args:
        feature_vector: (D,) request feature vector
        hash_indices: (num_hashes,) random projection indices
        fingerprint_out: (num_hashes,) binary fingerprint
    """
    cdef Py_ssize_t i, idx
    cdef Py_ssize_t num_hashes = hash_indices.shape[0]
    cdef Py_ssize_t D = feature_vector.shape[0]
    cdef float hash_val
    
    for i in range(num_hashes):
        idx = hash_indices[i] % D
        hash_val = feature_vector[idx]
        
        # Sign-based hashing
        fingerprint_out[i] = 1.0 if hash_val > 0.0 else 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_fingerprint_similarity(
    float[:] fingerprint_a,
    float[:] fingerprint_b
) nogil:
    """
    Compute Hamming similarity between fingerprints.
    
    Args:
        fingerprint_a: (num_hashes,) first fingerprint
        fingerprint_b: (num_hashes,) second fingerprint
        
    Returns:
        similarity: 0-1 (1 = identical)
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t num_hashes = fingerprint_a.shape[0]
    cdef int matches = 0
    
    for i in range(num_hashes):
        if fabs(fingerprint_a[i] - fingerprint_b[i]) < 0.5:
            matches += 1
    
    return <float>matches / <float>num_hashes


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_injection_patterns(
    int[:] token_ids,
    int[:] suspicious_token_ids,
    float threshold
) nogil:
    """
    Detect potential injection attacks (SQL, prompt injection, etc.).
    
    Args:
        token_ids: (T,) input token sequence
        suspicious_token_ids: (S,) known suspicious token IDs
        threshold: fraction of suspicious tokens to trigger alert
        
    Returns:
        1 if injection detected, 0 otherwise
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t T = token_ids.shape[0]
    cdef Py_ssize_t S = suspicious_token_ids.shape[0]
    cdef int suspicious_count = 0
    cdef float suspicious_fraction
    
    # Count suspicious tokens
    for i in range(T):
        for j in range(S):
            if token_ids[i] == suspicious_token_ids[j]:
                suspicious_count += 1
                break
    
    suspicious_fraction = <float>suspicious_count / <float>T
    
    if suspicious_fraction > threshold:
        return 1  # Injection detected
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void apply_exponential_backoff(
    int attempt_count,
    float base_delay,
    float max_delay,
    float jitter,
    float[:] delay_out
) nogil:
    """
    Compute exponential backoff delay with jitter.
    
    Args:
        attempt_count: number of failed attempts
        base_delay: base delay in seconds
        max_delay: maximum delay cap
        jitter: random jitter factor (0-1)
        delay_out: (1,) output delay in seconds
    """
    cdef float delay = base_delay * pow(2.0, <float>attempt_count)
    cdef float jitter_val = (<float>rand() / <float>RAND_MAX) * jitter * delay
    
    delay += jitter_val
    
    if delay > max_delay:
        delay = max_delay
    
    delay_out[0] = delay


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int verify_checksum(
    int[:] data,
    int checksum,
    int modulo
) nogil:
    """
    Verify simple checksum for data integrity.
    
    Args:
        data: (N,) data array
        checksum: expected checksum
        modulo: modulo for checksum computation
        
    Returns:
        1 if valid, 0 if invalid
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = data.shape[0]
    cdef int computed_checksum = 0
    
    for i in range(N):
        computed_checksum = (computed_checksum + data[i]) % modulo
    
    if computed_checksum == checksum:
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_trust_score(
    float request_frequency,
    float anomaly_score,
    float reputation_score,
    float[:] trust_out
) nogil:
    """
    Compute overall trust score for request/user.
    
    Args:
        request_frequency: requests per minute (normalized)
        anomaly_score: anomaly score (0-1)
        reputation_score: historical reputation (0-1)
        trust_out: (1,) output trust score (0-1, higher = more trusted)
    """
    cdef float trust = reputation_score
    
    # Penalize high request frequency
    if request_frequency > 10.0:
        trust *= 0.5
    elif request_frequency > 5.0:
        trust *= 0.8
    
    # Penalize anomalies
    trust *= (1.0 - anomaly_score)
    
    # Clamp to [0, 1]
    if trust < 0.0:
        trust = 0.0
    elif trust > 1.0:
        trust = 1.0
    
    trust_out[0] = trust


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int validate_utf8_sequence(
    unsigned char[:] byte_sequence
) nogil:
    """
    Validate UTF-8 encoding (detect malformed sequences).
    
    Args:
        byte_sequence: (N,) byte array
        
    Returns:
        1 if valid UTF-8, 0 otherwise
    """
    cdef Py_ssize_t i = 0
    cdef Py_ssize_t N = byte_sequence.shape[0]
    cdef unsigned char byte
    cdef int num_continuation
    
    while i < N:
        byte = byte_sequence[i]
        
        # ASCII (0xxxxxxx)
        if (byte & 0x80) == 0:
            i += 1
            continue
        
        # 2-byte sequence (110xxxxx)
        if (byte & 0xE0) == 0xC0:
            num_continuation = 1
        # 3-byte sequence (1110xxxx)
        elif (byte & 0xF0) == 0xE0:
            num_continuation = 2
        # 4-byte sequence (11110xxx)
        elif (byte & 0xF8) == 0xF0:
            num_continuation = 3
        else:
            return 0  # Invalid start byte
        
        # Check continuation bytes
        i += 1
        while num_continuation > 0:
            if i >= N:
                return 0  # Truncated
            
            byte = byte_sequence[i]
            if (byte & 0xC0) != 0x80:
                return 0  # Invalid continuation
            
            i += 1
            num_continuation -= 1
    
    return 1  # Valid UTF-8


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void sanitize_numeric_range(
    float[:] values,
    float min_val,
    float max_val,
    float[:] values_out
) nogil:
    """
    Sanitize numeric values to valid range.
    
    Args:
        values: (N,) input values
        min_val: minimum allowed value
        max_val: maximum allowed value
        values_out: (N,) clamped values
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = values.shape[0]
    
    for i in range(N):
        if values[i] < min_val:
            values_out[i] = min_val
        elif values[i] > max_val:
            values_out[i] = max_val
        else:
            values_out[i] = values[i]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_time_manipulation(
    float[:] timestamps,
    float current_time,
    float max_future_drift,
    float max_past_drift
) nogil:
    """
    Detect timestamp manipulation attacks.
    
    Args:
        timestamps: (N,) request timestamps
        current_time: current server time
        max_future_drift: max allowed future drift (seconds)
        max_past_drift: max allowed past drift (seconds)
        
    Returns:
        1 if manipulation detected, 0 otherwise
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = timestamps.shape[0]
    cdef float drift
    
    for i in range(N):
        drift = timestamps[i] - current_time
        
        if drift > max_future_drift or drift < -max_past_drift:
            return 1  # Manipulation detected
    
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_sliding_window_stats(
    float[:] values,
    int window_size,
    float[:] mean_out,
    float[:] std_out
) nogil:
    """
    Compute sliding window statistics for anomaly detection.
    
    Args:
        values: (T,) time series values
        window_size: window size for statistics
        mean_out: (T,) sliding mean
        std_out: (T,) sliding standard deviation
    """
    cdef Py_ssize_t t, i
    cdef Py_ssize_t T = values.shape[0]
    cdef float sum_val, sum_sq, mean, variance
    cdef int start, end, count
    
    for t in range(T):
        start = max(0, t - window_size + 1)
        end = t + 1
        count = end - start
        
        sum_val = 0.0
        sum_sq = 0.0
        
        for i in range(start, end):
            sum_val += values[i]
            sum_sq += values[i] * values[i]
        
        mean = sum_val / <float>count
        variance = (sum_sq / <float>count) - (mean * mean)
        
        if variance < 0.0:
            variance = 0.0
        
        mean_out[t] = mean
        std_out[t] = sqrt(variance)
