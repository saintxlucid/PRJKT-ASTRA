#!/usr/bin/env python3
"""
ASTRA Audio Analysis Tool - Beat & Verse Analysis

Analyzes audio tracks to generate:
- BPM map (instantaneous tempo between beats)
- Frequency bands analysis (sub, bass, lowmid, mid, high, air)
- Structural sections (intro, verse, chorus, bridge, outro)

Dependencies:
    pip install librosa numpy scipy

Usage:
    python analyze_track.py <audio_file>
    python analyze_track.py track.wav
    python analyze_track.py track.mp3

Output:
    - bpm_map.csv: Beat timing and instantaneous BPM values
    - bands.csv: Frequency band energy per 1-second windows
    - sections.csv: Structural boundaries and section labels

Sacred Code: 333 ∞
"""

import sys
import csv
import logging
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np

try:
    import librosa
    import librosa.display
except ImportError:
    print("[ERROR] librosa not installed. Install with: pip install librosa")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# Frequency band definitions (Hz ranges)
FREQUENCY_BANDS = [
    (20, 60, "sub"),       # Sub-bass
    (60, 150, "bass"),     # Bass
    (150, 600, "lowmid"),  # Low-mids
    (600, 2000, "mid"),    # Mids
    (2000, 8000, "high"),  # Highs
    (8000, 16000, "air")   # Air/brilliance
]


def analyze_bpm_map(y: np.ndarray, sr: int, hop_length: int = 512) -> List[Dict]:
    """
    Analyze instantaneous BPM between beats.
    
    Args:
        y: Audio time series
        sr: Sample rate
        hop_length: Hop length for analysis
    
    Returns:
        List of dicts with beat timing and BPM values
    """
    logger.info("Analyzing beat timing and BPM map...")
    
    # Detect beats
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    logger.info(f"  Global tempo: {tempo:.2f} BPM")
    logger.info(f"  Total beats: {len(beats)}")
    
    # Convert beat frames to time
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    
    # Calculate instantaneous BPM between beats
    bpm_values = []
    for i in range(1, len(beat_times)):
        delta_t = beat_times[i] - beat_times[i-1]
        if delta_t > 0:
            inst_bpm = 60.0 / delta_t
            bpm_values.append(inst_bpm)
        else:
            bpm_values.append(0.0)
    
    # Build results with smoothed median
    results = []
    for i in range(1, len(beat_times)):
        # Calculate 5-beat median for smoothing
        start_idx = max(0, i - 3)
        end_idx = min(len(bpm_values), i + 2)
        median_bpm = np.median(bpm_values[start_idx:end_idx])
        
        results.append({
            "idx": i,
            "time_s": round(beat_times[i], 3),
            "inst_bpm": round(bpm_values[i-1], 2),
            "median5": round(median_bpm, 2)
        })
    
    return results


def analyze_frequency_bands(
    y: np.ndarray, 
    sr: int, 
    window_size: int = None
) -> List[Dict]:
    """
    Analyze frequency band energy over time.
    
    Args:
        y: Audio time series
        sr: Sample rate
        window_size: Analysis window size in samples (default: 1 second)
    
    Returns:
        List of dicts with frequency band energies
    """
    logger.info("Analyzing frequency bands...")
    
    if window_size is None:
        window_size = sr  # 1 second
    
    hop_length = 512
    n_fft = 2048
    
    # Get frequency bins
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    
    results = []
    
    # Analyze in windows
    for start in range(0, len(y), window_size):
        segment = y[start:start + window_size]
        
        # Skip incomplete final segment
        if len(segment) < window_size:
            break
        
        # Compute STFT for segment
        S = np.abs(librosa.stft(segment, n_fft=n_fft, hop_length=hop_length))**2
        
        # Calculate energy for each band
        band_energies = {}
        for freq_low, freq_high, band_name in FREQUENCY_BANDS:
            # Create frequency mask
            mask = (freqs >= freq_low) & (freqs < freq_high)
            
            # Calculate mean power in band
            power = S[mask, :].mean()
            
            # Convert to dB
            energy_db = 10 * np.log10(power + 1e-12)
            band_energies[band_name] = round(energy_db, 2)
        
        results.append({
            "time_s": round(start / sr, 2),
            **band_energies
        })
    
    logger.info(f"  Analyzed {len(results)} windows")
    
    return results


def analyze_sections(
    y: np.ndarray, 
    sr: int, 
    hop_length: int = 512,
    n_sections: int = 6
) -> List[Dict]:
    """
    Detect structural sections using novelty-based segmentation.
    
    Args:
        y: Audio time series
        sr: Sample rate
        hop_length: Hop length for analysis
        n_sections: Target number of sections
    
    Returns:
        List of dicts with section boundaries
    """
    logger.info(f"Detecting structural sections (target: {n_sections})...")
    
    # Compute onset strength (novelty function)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    
    # Segment using agglomerative clustering
    boundaries = librosa.segment.agglomerative(
        onset_env.reshape(1, -1), 
        k=n_sections
    )
    
    # Convert to time
    boundary_times = librosa.frames_to_time(boundaries, sr=sr, hop_length=hop_length)
    
    # Label sections heuristically
    section_labels = [
        "Intro", "Verse 1", "Chorus 1", 
        "Verse 2", "Chorus 2", "Outro"
    ]
    
    results = []
    for i, time_s in enumerate(boundary_times):
        label = section_labels[i] if i < len(section_labels) else f"Section {i+1}"
        results.append({
            "section": i,
            "label": label,
            "start_s": round(time_s, 2)
        })
    
    logger.info(f"  Detected {len(results)} sections")
    
    return results


def write_csv(filename: str, data: List[Dict], fieldnames: List[str] = None):
    """Write analysis results to CSV file."""
    if not data:
        logger.warning(f"No data to write to {filename}")
        return
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"Wrote {filename} ({len(data)} rows)")


def main():
    """Main analysis pipeline."""
    print("═" * 70)
    print("  ASTRA Audio Analysis Tool - Beat & Verse Analysis")
    print("  Sacred Code: 333 ∞")
    print("═" * 70)
    print()
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python analyze_track.py <audio_file>")
        print()
        print("Examples:")
        print("  python analyze_track.py track.wav")
        print("  python analyze_track.py track.mp3")
        print()
        print("Output: bpm_map.csv, bands.csv, sections.csv")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Verify file exists
    if not Path(audio_file).exists():
        logger.error(f"Audio file not found: {audio_file}")
        sys.exit(1)
    
    logger.info(f"Loading audio: {audio_file}")
    
    # Load audio (mono, 44.1kHz)
    try:
        y, sr = librosa.load(audio_file, sr=44100, mono=True)
        duration = len(y) / sr
        logger.info(f"  Sample rate: {sr} Hz")
        logger.info(f"  Duration: {duration:.2f} seconds")
        logger.info(f"  Samples: {len(y)}")
    except Exception as e:
        logger.error(f"Failed to load audio: {e}")
        sys.exit(1)
    
    print()
    
    # Analysis parameters
    hop_length = 512
    
    # 1. Analyze BPM map
    bpm_data = analyze_bpm_map(y, sr, hop_length)
    write_csv(
        "bpm_map.csv", 
        bpm_data,
        fieldnames=["idx", "time_s", "inst_bpm", "median5"]
    )
    
    # 2. Analyze frequency bands
    bands_data = analyze_frequency_bands(y, sr)
    write_csv(
        "bands.csv",
        bands_data,
        fieldnames=["time_s", "sub", "bass", "lowmid", "mid", "high", "air"]
    )
    
    # 3. Detect sections
    sections_data = analyze_sections(y, sr, hop_length)
    write_csv(
        "sections.csv",
        sections_data,
        fieldnames=["section", "label", "start_s"]
    )
    
    print()
    print("═" * 70)
    print("  Analysis Complete")
    print("═" * 70)
    print()
    print("Generated files:")
    print("  ✓ bpm_map.csv     - Beat timing and instantaneous BPM")
    print("  ✓ bands.csv       - Frequency band energy (1s windows)")
    print("  ✓ sections.csv    - Structural section boundaries")
    print()
    print("Sacred Code: 333 ∞")


if __name__ == "__main__":
    main()
