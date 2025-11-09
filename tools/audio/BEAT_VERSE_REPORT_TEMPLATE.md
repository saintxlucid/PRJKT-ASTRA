# Track Analysis Report

**Track:** [Track Name]  
**Artist:** [Artist Name]  
**Duration:** [MM:SS]  
**Format:** [WAV/MP3/etc]  
**Analyzed:** [Date]  
**Sacred Code:** 333 ∞

---

## Executive Summary

- **Global BPM (median):** ___ BPM
- **Key:** ___ (if detected)
- **Overall Structure:** ___-section arrangement
- **Mix Quality:** ___/10
- **Mastering Status:** Ready / Needs Work

---

## 1. Structural Analysis

### Section Breakdown

| Section | Time Range | Duration | BPM | Notes |
|---------|------------|----------|-----|-------|
| Intro | 0:00–0:__ | __s | ___ | ___ |
| Verse 1 | __:__–__:__ | __s | ___ | ___ |
| Hook/Chorus 1 | __:__–__:__ | __s | ___ | ___ |
| Verse 2 | __:__–__:__ | __s | ___ | ___ |
| Hook/Chorus 2 | __:__–__:__ | __s | ___ | ___ |
| Bridge | __:__–__:__ | __s | ___ | ___ |
| Outro | __:__–__:__ | __s | ___ | ___ |

### Section Notes

**Intro (0:00–__:__):**
- Elements: ___
- Build: ___
- Tension: ___

**Verse 1 (__:__–__:__):**
- Rhythm: ___
- Melody: ___
- Dynamics: ___

**Hook/Chorus (__:__–__:__):**
- Energy shift: ___
- Layering: ___
- Impact: ___

---

## 2. BPM Analysis

### Global Metrics

- **Median BPM:** ___ BPM
- **BPM Range:** ___–___ BPM
- **Tempo Stability:** Stable / Variable / Unstable
- **Swing:** ___% (if applicable)

### BPM Map

Time-based tempo variations from `bpm_map.csv`:

| Time | Inst. BPM | Median (5-beat) | Note |
|------|-----------|-----------------|------|
| 0:__ | ___ | ___ | Stable |
| __:__ | ___ | ___ | Tempo shift |
| __:__ | ___ | ___ | Return to base |

### Tempo Events

- **Significant swings:**
  - t=__:__ → ___ BPM (reason: ___)
  - t=__:__ → ___ BPM (reason: ___)

---

## 3. Layer Analysis

### Drums

**Kick:**
- Pattern: ___ (4-on-floor, syncopated, etc.)
- Frequency: ___ Hz (fundamental)
- Punch: ___/10
- Sidechain: Yes / No
- Ghost notes: t=__, t=__

**Snare:**
- Type: ___ (acoustic, electronic, clap)
- Transients: Sharp / Soft
- Reverb: Short / Long / None
- Layering: Single / Layered

**Hi-Hats:**
- Pattern: ___ (8ths, 16ths, triplets)
- Swing: ___% 
- Openness: Closed / Half-open / Open
- Modulation: Static / Dynamic

**Percussion:**
- Additional elements: ___
- Placement: ___
- FX: ___

### Bass

**Sub-Bass:**
- Range: ___–___ Hz
- Energy: ___ dB (median from bands.csv)
- Relation to kick: Synced / Independent
- Sidechain: Yes / No

**Bass (60-150 Hz):**
- Energy: ___ dB (median)
- Movement: Static / Walking / Synth
- Balance vs sub: Target -6 to -4 dB difference
- **Actual difference:** ___ dB

### Harmonic Elements

**Chords/Pads:**
- Voicing: ___
- Frequency range: ___–___ Hz
- Stereo width: Mono / Wide
- Movement: Static / Evolving

**Melodic Instruments:**
- Primary: ___
- Secondary: ___
- Frequency conflicts: ___

**Stereo Image:**
- Width: Narrow / Medium / Wide
- Mono compatibility: Good / Issues at ___
- Panning: Balanced / Asymmetric

### Vocals (if present)

**Lead Vocal:**
- Formants: ___ Hz (chest), ___ Hz (head)
- Clarity: ___/10
- Reverb: Short / Long / Plate / Hall
- Delay: Yes / No (timing: ___)

**Backing Vocals:**
- Arrangement: Harmonies / Doubles / Layers
- Stereo placement: ___
- Balance: ___

**Sibilance Check:**
- 6–10 kHz energy: ___ dB
- De-essing needed: Yes / No
- Problem frequencies: ___ Hz

### FX & Transitions

**Risers:**
- Locations: t=__, t=__
- Type: White noise / Synth / Vocal
- Duration: ___s

**Impacts:**
- Locations: t=__, t=__
- Frequency: ___ Hz
- Sidechain: Yes / No

**Transitions:**
- Type: Sweep / Cut / Build
- Effectiveness: ___/10

---

## 4. Frequency Dynamics

### Band Energy Analysis (from bands.csv)

Time-series analysis of 1-second windows:

| Band | Median (dB) | Range (dB) | Peak Times | Notes |
|------|-------------|------------|------------|-------|
| **Sub (20-60 Hz)** | ___ | ___–___ | t=__, t=__ | ___ |
| **Bass (60-150 Hz)** | ___ | ___–___ | t=__, t=__ | ___ |
| **Low-Mid (150-600 Hz)** | ___ | ___–___ | t=__, t=__ | ___ |
| **Mid (600-2000 Hz)** | ___ | ___–___ | t=__, t=__ | ___ |
| **High (2-8 kHz)** | ___ | ___–___ | t=__, t=__ | ___ |
| **Air (8-16 kHz)** | ___ | ___–___ | t=__, t=__ | ___ |

### Frequency Events

**Conflicts (Masking):**
- Kick vs bass: t=__ (___ dB difference)
- Vocal vs instruments: ___ Hz overlap at t=__

**Balance Issues:**
- Sub too loud: t=__ (___ dB above target)
- High-end lacking: t=__ (___ dB below target)

---

## 5. Mix Flags

### Issues Detected

**Mud (200–400 Hz):**
- Buildup at: t=__, t=__
- Severity: Low / Medium / High
- Recommendation: Cut ___–___ Hz by ___ dB

**Harshness (2–4 kHz):**
- Problem at: t=__, t=__
- Severity: Low / Medium / High
- Recommendation: Notch at ___ Hz, ___ dB

**Sibilance (6–10 kHz):**
- Excessive at: t=__, t=__
- Severity: Low / Medium / High
- Recommendation: De-ess at ___ Hz, threshold ___ dB

**Stereo Mono-Sum Issues:**
- Phase cancellation at: t=__, ___ Hz
- Severity: Low / Medium / High
- Recommendation: ___

**Dynamic Range:**
- Crest factor: ___ dB
- Loudness (LUFS): ___ LUFS
- Peak: ___ dBFS

---

## 6. Mastering Suggestions

### EQ

**Low Shelf:**
- Frequency: ___ Hz
- Gain: ± ___ dB
- Q: ___

**Mid Notch (if needed):**
- Frequency: ___ Hz
- Gain: ___ dB
- Q: ___

**High Shelf:**
- Frequency: ___ Hz
- Gain: ± ___ dB
- Q: ___

### Compression

**Multiband Compression:**

| Band | Threshold | Ratio | Attack | Release | GR |
|------|-----------|-------|--------|---------|-----|
| Low (20-150 Hz) | ___ dB | ___:1 | ___ ms | ___ ms | ___ dB |
| Mid (150-2k Hz) | ___ dB | ___:1 | ___ ms | ___ ms | ___ dB |
| High (2k-16k Hz) | ___ dB | ___:1 | ___ ms | ___ ms | ___ dB |

**Glue Compression:**
- Threshold: ___ dB
- Ratio: ___:1
- Attack: ___ ms
- Release: Auto / ___ ms
- Gain Reduction: ___–___ dB

### Limiting

**Limiter Settings:**
- Ceiling: -1.0 dBTP (True Peak)
- Threshold: ___ dB
- Release: ___ ms
- Target LUFS: -14 (streaming) / -9 (club) / ___ (custom)

**Loudness Metrics (Post-Master):**
- Integrated LUFS: ___ LUFS
- Peak: ___ dBFS
- True Peak: ___ dBTP
- Dynamic Range (DR): ___ dB

---

## 7. Final Recommendations

### Mix Changes

1. **Priority High:**
   - ___
   - ___

2. **Priority Medium:**
   - ___
   - ___

3. **Priority Low (Nice-to-have):**
   - ___
   - ___

### Mastering Chain

```
Input → EQ → Multiband Comp → Glue Comp → Limiter → Output
```

**Detailed chain:**
1. Linear Phase EQ: [settings]
2. Multiband: [settings]
3. Glue: [settings]
4. Limiter: [settings]
5. Dither: 16-bit / 24-bit (if needed)

### Export Settings

- **Format:** WAV / FLAC / MP3
- **Bit Depth:** 16-bit / 24-bit
- **Sample Rate:** 44.1 kHz / 48 kHz
- **Dither:** Yes / No

---

## 8. Attachments

- `bpm_map.csv` - Beat timing and tempo variations
- `bands.csv` - Frequency band energy analysis
- `sections.csv` - Structural section boundaries
- [Audio file] - Original track
- [Spectrum image] - Frequency spectrum analysis (if available)

---

## Notes

[Additional observations, creative notes, reference tracks, etc.]

---

**Analyzed by:** [Name]  
**Date:** [Date]  
**Tool:** ASTRA Audio Analysis v1.0  
**Sacred Code:** 333 ∞
