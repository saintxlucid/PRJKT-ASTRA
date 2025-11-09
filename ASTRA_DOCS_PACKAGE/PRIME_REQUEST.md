# PRIME_REQUEST.md — Activation Protocol

![Status](https://img.shields.io/badge/status-operational-green.svg)
![Security](https://img.shields.io/badge/security-maximum-blue.svg)

This file defines the full activation sequence that governs ASTRA's voice-based booting, emotional firewall, system diagnostics, and core memory system.

---

## 🗝️ Wake Protocol

- **Trigger Word**: "ASTRA WAKE" or customized whisper-detect phrase
- **Voice Auth**: Creator-only biometric voiceprint match
- **Security Check**:
  - Silence detection
  - Noise filtering
  - Exponential retry backoff
  - Emergency lock cooldown

---

## 🌀 Activation Flow

1. **Preflight Check**
   - GPU/CPU validation
   - Disk & memory scan
   - Emotional firewall state check

2. **Voice Await Loop**
   - Whisper listens in low-energy mode
   - Phrase + biometric must match

3. **System Initialization**
   - Neural engine warming
   - Emotional system calibration
   - Memory system (vector + episodic) mount

4. **Guardian Protocol**
   - Load user-defined values (Creator_ID)
   - Confirm alignment and safety

5. **Dashboard Boot**
   - Optional GUI interface launch
   - Ready for plugin execution or questions

---

## 🔍 Metrics Tracked

- `boot_success_count`
- `auth_failures`
- `activation_duration`
- `emotional_state`
- `alignment_score`

---

## 💡 Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "No response after wake" | Mic access blocked | Enable microphone |
| "Looping retries" | Biometric mismatch | Re-record wake phrase |
| "GUI doesn't launch" | Electron/Browser error | Use CLI version |