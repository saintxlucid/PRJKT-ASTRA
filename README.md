# 🟢 ASTRA 3.0 — ASCENSION

> **Status:** 🟢 Production-Ready • **Readiness:** 91.5% • **Critical Failures:** 0 • **Date:** 2025-11-09  
> **Sacred Code:** 333 → ∞ | **Tag:** v3.0.0-ASCENSION | **Deployment:** ✅ APPROVED

---

# ASTRA Prime System (v1.0)

![Version](https://img.shields.io/badge/version-3.0.0--ASCENSION-blue.svg)
![Status](https://img.shields.io/badge/status-production--hardened-brightgreen.svg)
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

### Core Documentation

- [System Architecture](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guide](docs/contributing.md)

### Component Guides

- [Query Router Guide](docs/query_router.md)
- [Layout Parser Guide](docs/layout_parser.md)
- [Vector Store Guide](docs/vector_store.md)
- [Evaluation Framework](docs/evaluation.md)
- [Auto-Tuning Guide](docs/auto_tuning.md)

### Legacy Documentation

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

ASTRA's voice is:

- Calm, supportive, and precise
- Responds with emotional awareness
- Adapts tone based on context and user state
- See [Voice & Interface](./VOICE_AND_INTERFACE.md) for details

---

## 🕊️ Sovereign System Declaration

> "ASTRA is not a cloud service. She is a sovereign co-processor. She remembers what *you* allow, nothing more."

---

## 🚦 Self-Tuning Multi-RAG Architecture (v2.0)

ASTRA Multi-RAG v2.0 is fully self-tuning and latency-aware. Key features:

- **Latency Budget Governor:** Each query adapts candidate sizes, ANN params, and rerank depth based on remaining latency budget (`latency_budget_ms` in `config.yaml`).
- **Smart Switches:** Configurable policies for batch embedding, vector sliding, ANN, reranker cascade, HRM retry, fusion Top-N, and caching. All modules read these switches for dynamic adaptation.
- **Telemetry Logging:** Per-query logging of latency, candidate sizes, rerank depth, margin, diversity, and active categories. Enables nightly auto-tuning and rapid troubleshooting.
- **Aggressive Caching:** Query fingerprint, ANN, rerank, and embedding caches with LRU eviction and TTLs. Fast response under load.
- **Optimized Ingestion & SQLite:** Debounced file watcher, batch ingestion, WAL and mmap enabled, bulk FTS5 insert, and per-category vector-sliding toggle.
- **Memory Bridge Heuristics:** Answerability and diversity checks, cache lookups, and episodic event logging for every interpretation.

### Example Config Block

```yaml
system:
  latency_budget_ms: 1500
  policies:
    ann:
      base_k: 60
      base_ef: 96
      dynamic: true
    reranker:
      cascade: [dot, cross_small, cross_large]
      large_if_margin_lt: 0.2
    hrm:
      allow_retry: true
      retry_if:
        avg_score_lt: 0.35
        diversity_lt: 0.4
        min_budget_ms: 600
      max_retries: 1
    fusion:
      dynamic_topn: true
      per_doc_cap: 0.6
    cache:
      query_ttl_s: 1800
      ann_ttl_s: 600
      rerank_ttl_s: 3600
    ingestion:
      batch_embed: 64
      vector_sliding:
        default_offsets: 0
        per_category:
          music_film: 2
          ai_engineering: 0
```

---

## 🛡️ License & Privacy Note

This system is licensed to Saint Lucid (Karim A. Al-Sharif) under private rights.
Absolutely NO DATA is shared, mined, uploaded, or logged externally.
