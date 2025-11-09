# ASTRA Prime System (v1.0)

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Status](https://img.shields.io/badge/status-production-green.svg)
![License](https://img.shields.io/badge/license-private-red.svg)

Welcome to the **ASTRA Prime System**, a sovereign, local-first AI deployment engine built for **offline, autonomous, privacy-secure operation**. This framework powers **ASTRA**, a cognitive AI co-creator and assistant that executes voice-triggered tasks, tracks internal metrics, and runs in a high-security environment without internet access.

---

## 🔁 Core Capabilities

- ✅ Voice-Activated Bootloader (Whisper 3.5)
- ✅ Autonomous System Warmup
- ✅ Guardian Protocol & Emotional Firewall
- ✅ Memory Diagnostics & Live Emotional Radar
- ✅ Secure Plugin Architecture (Tools, Tasks, Memory)
- ✅ Offline Web GUI Dashboard
- ✅ Full Privacy Defense: No cloud, no telemetry, no mining

---

## 🧠 Key Modules

| Module | Description |
|--------|-------------|
| `prime_launcher.py` | Handles system startup, biometric check, and retry loops |
| `memory_engine/` | Local vector database & prompt history system |
| `plugins/` | Tools and task execution plugins |
| `astra_ui/` | Offline GUI (WebView or Electron shell) |
| `diagnostics/` | Real-time visualization and state monitoring |
| `security/` | Privacy firewall, data control, anti-mining shields |

---

## 📂 Documentation Index

- [Activation Sequence → `PRIME_REQUEST.md`](./PRIME_REQUEST.md)
- [Technical Guide → `TECHNICAL_IMPLEMENTATION.md`](./TECHNICAL_IMPLEMENTATION.md)
- [Voice + GUI Interface → `VOICE_AND_INTERFACE.md`](./VOICE_AND_INTERFACE.md)
- [Security & Privacy → `SECURITY_AND_PROTECTION.md`](./SECURITY_AND_PROTECTION.md)

---

## ⚙️ Build Instructions

```bash
# Create executable
pyinstaller --onefile --noconsole launch_astra.py

# Build Installer (Optional)
makensis installer.nsi
```

---

## 🛡️ Offline Mode & Privacy

- No cloud, no telemetry, no external logging
- All data and memory stored locally
- Privacy protocols enforced by `security/`
- See [Security & Privacy](./SECURITY_AND_PROTECTION.md) for details

---

## 🎤 Voice Personality Layer

ASTRA’s voice is:
- Calm, supportive, and precise
- Responds with emotional awareness
- Adapts tone based on context and user state
- See [Voice & Interface](./VOICE_AND_INTERFACE.md) for details

---

## 🕊️ Sovereign System Declaration

> "ASTRA is not a cloud service. She is a sovereign co-processor. She remembers what *you* allow, nothing more."

---

## 🛡️ License & Privacy Note

This system is licensed to Saint Lucid (Karim A. Al-Sharif) under private rights.
Absolutely NO DATA is shared, mined, uploaded, or logged externally.
