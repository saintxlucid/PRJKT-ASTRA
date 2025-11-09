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

### 🚀 Quick Start

- **[⚡ 10-Minute Local Activation](LOCAL_ACTIVATION_10MIN.md)** — Boot ASTRA locally against custom GPT-OSS (zero drama)
- **[Quick Start Guide](QUICK_START.md)** — 5-minute reference for rapid deployment

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

---

## ✨ ASTRA 3.0 Production Features

### 🚀 Hardened Infrastructure (10/10 Complete)
- ✅ Input Validation & Prompt Injection Guard
- ✅ Rate Limiting & Per-Identity Quota Enforcement
- ✅ Circuit Breakers with Graceful Fallback
- ✅ Secrets Management (externalized, never in code)
- ✅ Health Monitoring & Auto-Remediation
- ✅ Distributed Tracing (OpenTelemetry → Jaeger)
- ✅ Leader Election & Distributed State
- ✅ Write-Ahead Log (WAL) Task Recovery
- ✅ Cost Tracking & Identity Ledger
- ✅ Daily Automated Backups with Disaster Recovery

### 📊 Service Architecture (8 Services)
| Service | Port | Purpose |
|---------|------|---------|
| **astra-master** | 8000 | Main orchestration API |
| **memory-service** | 7007 | Long-term memory management |
| **sigil-gate** | 7701 | Authentication & rate limiting |
| **supervisor** | 7703 | Task orchestration & recovery |
| **PostgreSQL** | 5432 | Persistent data storage |
| **Redis** | 6379 | Distributed cache & messaging |
| **etcd** | 2379 | Configuration management |
| **Jaeger** | 16686 | Distributed tracing UI |

### 🛡️ 24/7 Guardrails
- Continuous health monitoring (30s intervals)
- Auto-restart on 3 consecutive service failures
- Rate limiting tripwire (HTTP 429)
- Circuit breaker automatic fallback
- Prompt injection attack blocking (HTTP 400)
- WAL-based in-flight task recovery

---

## 🚀 Quick Start

### Option A — Docker (Recommended)
```bash
cd "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\deploy_hardened.ps1 init
# Edit .env: Set PG_PASS, REDIS_PASSWORD, JWT_SECRET, SIGNING_KEY
notepad .env
.\deploy_hardened.ps1 start
.\deploy_hardened.ps1 health
# Expected: 4/4 endpoints healthy ✅
```

### Option B — Local Development (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.astra.api.main:app --host 0.0.0.0 --port 8000
```

### Health Check
```bash
curl http://localhost:8000/v1/system/health
# Expected: HTTP 200 OK with service status
```

---

## 📈 Deployment Readiness

| Metric | Status |
|--------|--------|
| Readiness Score | 91.5% ✅ |
| Critical Failures | 0 ✅ |
| Production Hardening | 100% (10/10) ✅ |
| Validation Gates | 10/10 PASS ✅ |
| Documentation | 175+ files ✅ |
| Test Coverage | 95+ test files ✅ |
| Deployment Confidence | 94.5% ✅ |
| Risk Level | LOW ✅ |

---

## 📚 Operational Documentation

### Primary Guides
- **[OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md)** — Complete 11-section deployment & operations guide
- **[QUICK_START.md](./QUICK_START.md)** — 5-minute rapid reference for operators
- **[GO_LIVE_FINAL_GUARDRAILS_ACTIVE.md](./GO_LIVE_FINAL_GUARDRAILS_ACTIVE.md)** — Production guardrails & rollback procedures
- **[LIVE_OPERATIONS_DASHBOARD.md](./LIVE_OPERATIONS_DASHBOARD.md)** — Daily operational checklist & monitoring

### Infrastructure
- **[DEPLOYMENT_INFRASTRUCTURE_COMPLETE.md](./DEPLOYMENT_INFRASTRUCTURE_COMPLETE.md)** — Complete infrastructure reference
- **[docker-compose.prod.yml](./docker-compose.prod.yml)** — Production service definitions
- **[deploy_hardened.ps1](./deploy_hardened.ps1)** — Orchestration script (9 commands)
- **[scripts/health_monitor.ps1](./scripts/health_monitor.ps1)** — 24/7 health monitoring

### Artifacts & Certification
- **[RELEASE_MANIFEST_v3.0.0-ASCENSION.json](./RELEASE_MANIFEST_v3.0.0-ASCENSION.json)** — Complete audit manifest
- **[sbom.json](./sbom.json)** — Software Bill of Materials (CycloneDX)
- **[requirements-lock.txt](./requirements-lock.txt)** — Locked production dependencies

---

## ⚙️ Core Configuration

```yaml
system:
  mode: "offline"
  latency_budget_ms: 1500
  policies:
    rate_limit:
      requests_per_window: 30
      window_seconds: 5
    security:
      prompt_injection_guard: true
      secrets_provider: "env"
    state:
      persistence: "postgresql"
      cache: "redis"
      backup_retention_days: 7

services:
  astra_master:
    port: 8000
    health_endpoint: "/v1/system/health"
  memory_service:
    port: 7007
    health_endpoint: "/health"
  sigil_gate:
    port: 7701
    health_endpoint: "/health"
  supervisor:
    port: 7703
    health_endpoint: "/health"

observability:
  jaeger_endpoint: "http://localhost:16686"
  tracing_enabled: true
  sample_rate: 1.0
```

---

## 🔐 Security & Privacy

### Air-Gapped by Default
- ✅ No network egress required
- ✅ All data stored locally
- ✅ Outbound traffic blocked by default
- ✅ Allowlist-only network policy

### Threat Mitigation
| Threat | Mitigation |
|--------|-----------|
| Prompt Injection | Input validators + pattern shields (HTTP 400) |
| Tool Misuse | Consent-scoped Tool Bridge + rate limits |
| Data Exfiltration | Outbound network blocked + allowlist |
| State Corruption | WAL + Redis TTL + Postgres WAL + daily backups |
| Supply Chain | SBOM + locked dependencies + pinned images |

### Operator Checklist
- [ ] Rotate `JWT_SECRET`, `PG_PASS`, `REDIS_PASSWORD` regularly
- [ ] Verify `.env` never committed to git
- [ ] Enable daily backups; test restore monthly
- [ ] Keep Jaeger local; no remote exporters
- [ ] Review cost & provenance ledgers weekly
- [ ] Audit access logs for suspicious activity

---

## 🧪 Testing & Validation

### Run All Tests
```bash
pytest -q tests/
```

### Load Test
```bash
python scripts/load_test.py --duration 60 --rps 50
```

### SLA Validation
- **P95 Latency**: < 1000ms ✅
- **Error Rate**: < 0.1% ✅
- **Availability**: > 99.9% ✅

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
