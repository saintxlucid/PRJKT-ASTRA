# cython: boundscheck=False, wraparound=False, cdivision=True, language_level=3
"""
ASTRA Cortex: DSP & Audio Kernels
==================================

Real-time audio processing for:
- Voice activity detection (VAD)
- Spectral analysis
- Onset detection
- Energy-based gating
"""

from cython.parallel import prange
cimport cython
from libc.math cimport sqrt, log10, fabs
import numpy as np


# ============================================================================
# RMS ENVELOPE (Frame-wise)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void rms_framewise(
    float[:] x,
    Py_ssize_t frame_size,
    Py_ssize_t hop_size,
    float[:] out
) nogil:
    """
    Compute RMS (root-mean-square) envelope of audio signal.
    
    Args:
        x: (N,) input audio signal
        frame_size: size of analysis frame (e.g., 2048 samples)
        hop_size: hop between frames (e.g., 512 samples)
        out: (num_frames,) output RMS values
    
    Used for:
    - Voice activity detection
    - Energy-based gating
    - Dynamic range analysis
    """
    cdef Py_ssize_t i, j, n = x.shape[0], idx = 0
    cdef float s, v
    
    i = 0
    while i <= n - frame_size:
        s = 0.0
        for j in range(frame_size):
            v = x[i + j]
            s += v * v
        out[idx] = sqrt(s / frame_size)
        idx += 1
        i += hop_size


# ============================================================================
# SPECTRAL ENERGY BANDS
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void spectral_energy_bands(
    float[:] magnitude_spectrum,
    Py_ssize_t[:] band_edges,
    float[:] band_energies
) nogil:
    """
    Compute energy in frequency bands.
    
    Args:
        magnitude_spectrum: (fft_size // 2 + 1,) magnitude spectrum
        band_edges: (num_bands + 1,) bin indices for band boundaries
        band_energies: (num_bands,) output energy per band
    
    Example bands:
        - Low: 0-200 Hz (bass, kick drum)
        - Mid: 200-2000 Hz (voice, melody)
        - High: 2000-8000 Hz (sibilance, cymbals)
    """
    cdef Py_ssize_t i, j, num_bands = band_energies.shape[0]
    cdef Py_ssize_t start, end
    cdef float energy
    
    for i in range(num_bands):
        start = band_edges[i]
        end = band_edges[i + 1]
        energy = 0.0
        
        for j in range(start, end):
            energy += magnitude_spectrum[j] * magnitude_spectrum[j]
        
        band_energies[i] = energy


# ============================================================================
# ENVELOPE FOLLOWER (Attack/Release)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void envelope_follower(
    float[:] x,
    float[:] out,
    float attack_coeff=0.99,
    float release_coeff=0.999
) nogil:
    """
    Smooth envelope follower with asymmetric attack/release.
    
    Follows signal peaks with fast attack, slow release.
    
    Args:
        x: (N,) input signal (e.g., RMS values)
        out: (N,) output envelope
        attack_coeff: smoothing for rising edges (higher = slower)
        release_coeff: smoothing for falling edges (higher = slower)
    
    Used for:
    - VAD with hysteresis
    - Adaptive gating
    - Dynamic compression
    """
    cdef Py_ssize_t i, n = x.shape[0]
    cdef float envelope = 0.0
    cdef float coeff
    
    for i in range(n):
        if fabs(x[i]) > envelope:
            coeff = attack_coeff
        else:
            coeff = release_coeff
        
        envelope = coeff * envelope + (1.0 - coeff) * fabs(x[i])
        out[i] = envelope


# ============================================================================
# ONSET DETECTION (Spectral Flux)
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void spectral_flux(
    float[:, :] magnitude_spectrogram,
    float[:] onset_strength
) nogil:
    """
    Compute onset detection function via spectral flux.
    
    Measures increase in spectral energy between consecutive frames.
    
    Args:
        magnitude_spectrogram: (num_frames, num_bins) magnitude spectrogram
        onset_strength: (num_frames,) output onset strength
    
    Used for:
    - Beat tracking
    - Transient detection
    - Audio segmentation
    """
    cdef Py_ssize_t i, j, num_frames = magnitude_spectrogram.shape[0]
    cdef Py_ssize_t num_bins = magnitude_spectrogram.shape[1]
    cdef float diff, flux
    
    onset_strength[0] = 0.0
    
    for i in range(1, num_frames):
        flux = 0.0
        for j in range(num_bins):
            diff = magnitude_spectrogram[i, j] - magnitude_spectrogram[i - 1, j]
            if diff > 0:
                flux += diff
        onset_strength[i] = flux


# ============================================================================
# ZERO-CROSSING RATE
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void zero_crossing_rate(
    float[:] x,
    Py_ssize_t frame_size,
    Py_ssize_t hop_size,
    float[:] out
) nogil:
    """
    Compute zero-crossing rate (ZCR) per frame.
    
    ZCR measures signal noisiness:
    - High ZCR → noisy/unvoiced (fricatives, sibilants)
    - Low ZCR → tonal/voiced (vowels, harmonics)
    
    Args:
        x: (N,) input signal
        frame_size: analysis frame size
        hop_size: hop between frames
        out: (num_frames,) output ZCR values
    """
    cdef Py_ssize_t i, j, n = x.shape[0], idx = 0
    cdef Py_ssize_t crossings
    
    i = 0
    while i <= n - frame_size:
        crossings = 0
        for j in range(frame_size - 1):
            if (x[i + j] >= 0 and x[i + j + 1] < 0) or \
               (x[i + j] < 0 and x[i + j + 1] >= 0):
                crossings += 1
        out[idx] = <float>crossings / <float>frame_size
        idx += 1
        i += hop_size


# ============================================================================
# VOICE ACTIVITY DETECTION (VAD) - Combined Features
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void vad_detect(
    float[:] rms,
    float[:] zcr,
    float[:] vad_out,
    float rms_threshold=0.02,
    float zcr_threshold=0.3,
    float hangover_frames=5
) nogil:
    """
    Voice activity detection combining RMS energy and zero-crossing rate.
    
    Args:
        rms: (num_frames,) RMS envelope
        zcr: (num_frames,) zero-crossing rate
        vad_out: (num_frames,) output VAD flags (1.0 = voice, 0.0 = silence)
        rms_threshold: energy threshold
        zcr_threshold: max ZCR for voiced (lower = more tonal)
        hangover_frames: extend voice regions by N frames (avoid chopping)
    
    Algorithm:
    - Voice detected when: RMS > threshold AND ZCR < threshold
    - Extends voice regions by hangover_frames to avoid choppiness
    """
    cdef Py_ssize_t i, n = rms.shape[0]
    cdef Py_ssize_t hangover_counter = 0
    cdef bint voice_detected
    
    for i in range(n):
        voice_detected = (rms[i] > rms_threshold and zcr[i] < zcr_threshold)
        
        if voice_detected:
            vad_out[i] = 1.0
            hangover_counter = <Py_ssize_t>hangover_frames
        elif hangover_counter > 0:
            vad_out[i] = 1.0
            hangover_counter -= 1
        else:
            vad_out[i] = 0.0


# ============================================================================
# ADAPTIVE NOISE GATE
# ============================================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void adaptive_noise_gate(
    float[:] x,
    float[:] out,
    float threshold_db=-40.0,
    float attack_ms=5.0,
    float release_ms=50.0,
    float sample_rate=16000.0
) nogil:
    """
    Adaptive noise gate with smooth attack/release.
    
    Args:
        x: (N,) input signal
        out: (N,) gated output
        threshold_db: gate threshold in dB
        attack_ms: attack time in milliseconds
        release_ms: release time in milliseconds
        sample_rate: audio sample rate
    
    When signal drops below threshold, smoothly attenuates to silence.
    """
    cdef Py_ssize_t i, n = x.shape[0]
    cdef float threshold_lin = 10.0 ** (threshold_db / 20.0)
    cdef float attack_coeff = 1.0 - (1000.0 / (attack_ms * sample_rate))
    cdef float release_coeff = 1.0 - (1000.0 / (release_ms * sample_rate))
    cdef float gain = 1.0
    cdef float coeff
    
    for i in range(n):
        if fabs(x[i]) > threshold_lin:
            coeff = attack_coeff
        else:
            coeff = release_coeff
        
        gain = coeff * gain + (1.0 - coeff) * (1.0 if fabs(x[i]) > threshold_lin else 0.0)
        out[i] = x[i] * gain
