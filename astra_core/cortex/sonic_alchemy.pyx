# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: embedsignature=True

"""
ASTRA Sonic Alchemy Kernel - Real-Time Audio Intuition
=======================================================

Producer-level audio instincts at C-speed:
- Onset detection (transient events)
- Transient shaping (punch control)
- Spectral fingerprints (audio DNA)
- Zero-latency feature extraction
- Micro-beat alignment
- Energy pattern detection

All those things a producer senses with the body — ASTRA can sense numerically.

Creates a "Lucid DSP Core" that turns raw sound into:
- Emotion tags
- Energy states
- Tension curves
- Mood signatures
"""

import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport sqrt, exp, sin, cos, atan2, fabs, tanh, log, pow
from cython.parallel import prange


# ============================================================================
# ONSET DETECTION (Transient Events)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_onsets(
    float[:] audio,
    float[:] onset_strength,
    Py_ssize_t hop_size=512,
    float threshold=0.3
) nogil:
    """
    Detect onsets (transient events like drums, attacks).
    
    Uses spectral flux method - sudden increases in spectral energy.
    
    Args:
        audio: (N,) audio signal
        onset_strength: (num_frames,) output onset strength
        hop_size: hop between analysis frames
        threshold: detection threshold
    """
    cdef Py_ssize_t i, j, n = audio.shape[0]
    cdef Py_ssize_t num_frames = onset_strength.shape[0]
    cdef float current_energy, prev_energy, flux
    cdef Py_ssize_t frame_idx = 0
    
    prev_energy = 0.0
    i = 0
    while i < n - hop_size and frame_idx < num_frames:
        # Compute energy in current frame
        current_energy = 0.0
        for j in range(hop_size):
            current_energy += audio[i + j] * audio[i + j]
        
        # Spectral flux = positive difference
        flux = current_energy - prev_energy
        if flux < 0.0:
            flux = 0.0
        
        onset_strength[frame_idx] = flux
        prev_energy = current_energy
        frame_idx += 1
        i += hop_size


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void peak_pick_onsets(
    float[:] onset_strength,
    float[:] onset_times,
    Py_ssize_t[:] num_onsets_out,
    float threshold=0.5,
    Py_ssize_t min_distance=10
) nogil:
    """
    Pick onset peaks from onset strength function.
    
    Args:
        onset_strength: (num_frames,) onset strength
        onset_times: (max_onsets,) output onset frame indices
        num_onsets_out: (1,) number of detected onsets
        threshold: minimum peak height
        min_distance: minimum frames between onsets
    """
    cdef Py_ssize_t i, n = onset_strength.shape[0]
    cdef Py_ssize_t max_onsets = onset_times.shape[0]
    cdef Py_ssize_t onset_count = 0
    cdef Py_ssize_t last_onset = -min_distance
    cdef float strength
    
    for i in range(1, n - 1):
        strength = onset_strength[i]
        
        # Check if it's a local maximum above threshold
        if strength > threshold and \
           strength > onset_strength[i-1] and \
           strength > onset_strength[i+1] and \
           i - last_onset >= min_distance:
            
            if onset_count < max_onsets:
                onset_times[onset_count] = <float>i
                onset_count += 1
                last_onset = i
    
    num_onsets_out[0] = onset_count


# ============================================================================
# TRANSIENT SHAPING (Punch Control)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void shape_transients(
    float[:] audio,
    float[:] onset_times,
    Py_ssize_t num_onsets,
    float[:] audio_out,
    float attack_gain=1.5,
    float sustain_gain=0.8,
    Py_ssize_t attack_samples=100
) nogil:
    """
    Shape transients for more punch or smoothness.
    
    Amplifies attack portion, reduces sustain.
    
    Args:
        audio: (N,) input audio
        onset_times: (num_onsets,) onset frame indices
        num_onsets: number of valid onsets
        audio_out: (N,) shaped audio
        attack_gain: gain for attack portion
        sustain_gain: gain for sustain portion
        attack_samples: attack window size
    """
    cdef Py_ssize_t i, j, n = audio.shape[0]
    cdef Py_ssize_t onset_idx
    cdef Py_ssize_t onset_frame
    cdef float gain
    cdef bint in_attack
    
    # Copy input to output
    for i in range(n):
        audio_out[i] = audio[i]
    
    # Apply gain envelopes around onsets
    for j in range(num_onsets):
        onset_frame = <Py_ssize_t>onset_times[j]
        
        # Attack phase
        for i in range(attack_samples):
            onset_idx = onset_frame + i
            if onset_idx < n:
                # Exponential attack envelope
                gain = attack_gain * (1.0 - <float>i / <float>attack_samples)
                audio_out[onset_idx] *= (1.0 + gain)
        
        # Sustain phase
        for i in range(attack_samples, attack_samples * 3):
            onset_idx = onset_frame + i
            if onset_idx < n:
                audio_out[onset_idx] *= sustain_gain


# ============================================================================
# SPECTRAL FINGERPRINT (Audio DNA)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_spectral_fingerprint(
    float[:, :] spectrogram,
    float[:] fingerprint_out
) nogil:
    """
    Compute compact spectral fingerprint.
    
    Fingerprint = [spectral_centroid, spectral_spread, 
                   spectral_skew, spectral_rolloff,
                   spectral_flux, harmonic_ratio]
    
    Args:
        spectrogram: (num_frames, num_bins) magnitude spectrogram
        fingerprint_out: (6,) compact fingerprint
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t num_frames = spectrogram.shape[0]
    cdef Py_ssize_t num_bins = spectrogram.shape[1]
    cdef double centroid = 0.0
    cdef double spread = 0.0
    cdef double total_energy = 0.0
    cdef double rolloff_threshold, cumulative_energy
    cdef Py_ssize_t rolloff_bin = 0
    cdef float magnitude
    
    # Compute spectral centroid (center of mass)
    for j in range(num_bins):
        magnitude = 0.0
        for i in range(num_frames):
            magnitude += spectrogram[i, j]
        magnitude /= <float>num_frames
        
        centroid += magnitude * <double>j
        total_energy += magnitude
    
    if total_energy > 1e-6:
        centroid /= total_energy
    
    # Compute spectral spread (variance)
    for j in range(num_bins):
        magnitude = 0.0
        for i in range(num_frames):
            magnitude += spectrogram[i, j]
        magnitude /= <float>num_frames
        
        spread += magnitude * (j - centroid) * (j - centroid)
    
    if total_energy > 1e-6:
        spread = sqrt(spread / total_energy)
    
    # Compute spectral rolloff (85% energy point)
    rolloff_threshold = 0.85 * total_energy
    cumulative_energy = 0.0
    for j in range(num_bins):
        magnitude = 0.0
        for i in range(num_frames):
            magnitude += spectrogram[i, j]
        magnitude /= <float>num_frames
        
        cumulative_energy += magnitude
        if cumulative_energy >= rolloff_threshold:
            rolloff_bin = j
            break
    
    # Store fingerprint
    fingerprint_out[0] = <float>centroid / <float>num_bins  # Normalized centroid
    fingerprint_out[1] = <float>spread / <float>num_bins    # Normalized spread
    fingerprint_out[2] = 0.0  # Placeholder for skew
    fingerprint_out[3] = <float>rolloff_bin / <float>num_bins
    fingerprint_out[4] = 0.0  # Placeholder for flux
    fingerprint_out[5] = 0.0  # Placeholder for harmonic ratio


# ============================================================================
# ENERGY PATTERN DETECTION
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_energy_patterns(
    float[:] audio,
    float[:] energy_curve,
    Py_ssize_t window_size=2048
) nogil:
    """
    Extract energy curve for pattern detection.
    
    Args:
        audio: (N,) audio signal
        energy_curve: (num_frames,) output energy over time
        window_size: analysis window
    """
    cdef Py_ssize_t i, j, n = audio.shape[0]
    cdef Py_ssize_t num_frames = energy_curve.shape[0]
    cdef float energy
    cdef Py_ssize_t frame_idx = 0
    
    i = 0
    while i < n - window_size and frame_idx < num_frames:
        energy = 0.0
        for j in range(window_size):
            energy += audio[i + j] * audio[i + j]
        
        energy_curve[frame_idx] = sqrt(energy / <float>window_size)
        frame_idx += 1
        i += window_size // 2  # 50% overlap


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void classify_energy_state(
    float[:] energy_curve,
    float[:] state_out
) nogil:
    """
    Classify energy state: calm, building, peak, release.
    
    state = [0=calm, 1=building, 2=peak, 3=release]
    
    Args:
        energy_curve: (T,) energy over time
        state_out: (T,) energy state classification
    """
    cdef Py_ssize_t t, T = energy_curve.shape[0]
    cdef float energy, prev_energy, next_energy
    cdef float slope_before, slope_after
    cdef float mean_energy = 0.0
    
    # Compute mean energy
    for t in range(T):
        mean_energy += energy_curve[t]
    mean_energy /= <float>T
    
    for t in range(1, T - 1):
        energy = energy_curve[t]
        prev_energy = energy_curve[t-1]
        next_energy = energy_curve[t+1]
        
        slope_before = energy - prev_energy
        slope_after = next_energy - energy
        
        # Classify state
        if energy < mean_energy * 0.5:
            state_out[t] = 0.0  # Calm
        elif slope_before > 0.0 and slope_after > 0.0:
            state_out[t] = 1.0  # Building
        elif energy > mean_energy * 1.5:
            state_out[t] = 2.0  # Peak
        elif slope_before < 0.0 and slope_after < 0.0:
            state_out[t] = 3.0  # Release
        else:
            state_out[t] = 0.0  # Calm (default)
    
    # Boundary conditions
    state_out[0] = 0.0
    state_out[T-1] = 0.0


# ============================================================================
# MICRO-BEAT ALIGNMENT
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_micro_beats(
    float[:] onset_strength,
    float[:] beat_times,
    Py_ssize_t[:] num_beats_out,
    float tempo_bpm=120.0,
    Py_ssize_t sr=44100
) nogil:
    """
    Detect micro-beats from onset strength.
    
    Uses tempo to guide beat tracking.
    
    Args:
        onset_strength: (num_frames,) onset strength
        beat_times: (max_beats,) output beat times
        num_beats_out: (1,) number of detected beats
        tempo_bpm: estimated tempo in BPM
        sr: sample rate
    """
    cdef Py_ssize_t i, n = onset_strength.shape[0]
    cdef Py_ssize_t max_beats = beat_times.shape[0]
    cdef float beat_period = 60.0 / tempo_bpm * <float>sr  # Samples per beat
    cdef Py_ssize_t expected_beat_frame
    cdef Py_ssize_t search_window = <Py_ssize_t>(beat_period * 0.1)  # ±10%
    cdef Py_ssize_t beat_count = 0
    cdef float max_strength
    cdef Py_ssize_t max_idx
    cdef Py_ssize_t start, end
    
    expected_beat_frame = 0
    while expected_beat_frame < n and beat_count < max_beats:
        # Search for max onset in window around expected beat
        start = expected_beat_frame - search_window
        if start < 0:
            start = 0
        end = expected_beat_frame + search_window
        if end >= n:
            end = n - 1
        
        max_strength = onset_strength[start]
        max_idx = start
        for i in range(start + 1, end + 1):
            if onset_strength[i] > max_strength:
                max_strength = onset_strength[i]
                max_idx = i
        
        beat_times[beat_count] = <float>max_idx
        beat_count += 1
        expected_beat_frame = max_idx + <Py_ssize_t>beat_period
    
    num_beats_out[0] = beat_count


# ============================================================================
# TENSION CURVE EXTRACTION (Producer Instinct)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void extract_tension_curve(
    float[:] audio,
    float[:] tension_out,
    Py_ssize_t window_size=4096
) nogil:
    """
    Extract tension curve from audio.
    
    Tension = spectral brightness + energy variance
    
    Args:
        audio: (N,) audio signal
        tension_out: (num_frames,) tension curve
        window_size: analysis window
    """
    cdef Py_ssize_t i, j, n = audio.shape[0]
    cdef Py_ssize_t num_frames = tension_out.shape[0]
    cdef float brightness, variance, mean
    cdef Py_ssize_t frame_idx = 0
    
    i = 0
    while i < n - window_size and frame_idx < num_frames:
        # Compute mean
        mean = 0.0
        for j in range(window_size):
            mean += fabs(audio[i + j])
        mean /= <float>window_size
        
        # Compute variance (instability measure)
        variance = 0.0
        for j in range(window_size):
            variance += (fabs(audio[i + j]) - mean) * (fabs(audio[i + j]) - mean)
        variance /= <float>window_size
        
        # Brightness approximation (high-frequency content)
        brightness = 0.0
        for j in range(window_size - 1):
            brightness += fabs(audio[i + j + 1] - audio[i + j])
        brightness /= <float>window_size
        
        # Combine for tension metric
        tension_out[frame_idx] = sqrt(variance) + brightness * 0.5
        frame_idx += 1
        i += window_size // 2


# ============================================================================
# MOOD TAG EXTRACTION (Emotion → Tags)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void extract_mood_tags(
    float[:] energy_curve,
    float[:] tension_curve,
    float[:] spectral_fingerprint,
    float[:] mood_vector_out
) nogil:
    """
    Extract mood tags from audio features.
    
    mood_vector = [energy_level, tension_level, brightness, 
                   darkness, aggression, calmness, joy, sadness]
    
    Args:
        energy_curve: (T,) energy over time
        tension_curve: (T,) tension over time
        spectral_fingerprint: (6,) spectral features
        mood_vector_out: (8,) mood tag scores
    """
    cdef Py_ssize_t t, T = energy_curve.shape[0]
    cdef float mean_energy = 0.0
    cdef float mean_tension = 0.0
    cdef float energy_variance = 0.0
    cdef float centroid, spread
    
    # Compute statistics
    for t in range(T):
        mean_energy += energy_curve[t]
        mean_tension += tension_curve[t]
    mean_energy /= <float>T
    mean_tension /= <float>T
    
    for t in range(T):
        energy_variance += (energy_curve[t] - mean_energy) * (energy_curve[t] - mean_energy)
    energy_variance /= <float>T
    
    centroid = spectral_fingerprint[0]
    spread = spectral_fingerprint[1]
    
    # Map to mood tags
    mood_vector_out[0] = mean_energy  # Energy level
    mood_vector_out[1] = mean_tension  # Tension level
    mood_vector_out[2] = centroid  # Brightness (high centroid = bright)
    mood_vector_out[3] = 1.0 - centroid  # Darkness (inverse)
    mood_vector_out[4] = mean_tension * mean_energy  # Aggression
    mood_vector_out[5] = (1.0 - mean_tension) * (1.0 - mean_energy)  # Calmness
    mood_vector_out[6] = centroid * mean_energy  # Joy (bright + energetic)
    mood_vector_out[7] = (1.0 - centroid) * mean_tension  # Sadness (dark + tense)


# ============================================================================
# HARMONIC CONTENT ANALYSIS
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_harmonic_ratio(
    float[:] audio,
    Py_ssize_t window_size=2048
) nogil:
    """
    Compute harmonic-to-noise ratio.
    
    Higher ratio = more tonal/musical content
    Lower ratio = more percussive/noise content
    
    Args:
        audio: (N,) audio signal
        window_size: analysis window
    
    Returns:
        Harmonic ratio [0, 1]
    """
    cdef Py_ssize_t i, n = audio.shape[0]
    cdef float autocorr_zero = 0.0
    cdef float autocorr_peak = 0.0
    cdef Py_ssize_t lag
    cdef float corr
    
    # Autocorrelation at zero lag (total energy)
    for i in range(window_size):
        if i < n:
            autocorr_zero += audio[i] * audio[i]
    
    # Find peak autocorrelation (harmonic content)
    for lag in range(20, min(window_size, 400)):  # Pitch range ~100Hz - 2kHz
        corr = 0.0
        for i in range(window_size - lag):
            if i + lag < n:
                corr += audio[i] * audio[i + lag]
        
        if corr > autocorr_peak:
            autocorr_peak = corr
    
    if autocorr_zero > 1e-6:
        return autocorr_peak / autocorr_zero
    return 0.0
