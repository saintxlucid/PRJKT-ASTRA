# Changelog

All notable changes to this project are documented in this file.

---

## [3.0.0] — ASCENSION (2025-11-09)

### 🎯 Major Release: Production Hardening Complete

#### ✨ Added

**State Persistence & Recovery**
- StateManager: Hot cache (Redis) + cold storage (PostgreSQL) + WAL
- Sigil provenance ledger: Track every request, tool invocation, response
- Cost ledger: Per-identity token usage + inference cost accumulation
- Write-Ahead Log (WAL): PostgreSQL-backed task recovery (automatic replay on restart)

**Distributed Coordination**
- Leader election: Redis SET NX EX with distributed consensus
- Health aggregator: 30-second polling, auto-restart on 3 consecutive failures
- Service mesh: Master, Memory, SigilGate, Supervisor with coordinated startup

**Security & Secrets**
- SigilGate identity service: JWT issuance (HS256) + per-identity rate limiting
- Secrets externalization: `.env` configuration (no defaults in code)
- Input validation: Pydantic validators, prompt injection guard (HTTP 400)
- Circuit breaker: Protected memory-service with fallback

**Observability & Tracing**
- OpenTelemetry: End-to-end request tracing
- Jaeger backend: Local deployment (localhost:16686)
- Span export: HTTP POST to Jaeger collector
- Smoke tests: PowerShell + Pytest validation suite

**Infrastructure & Operations**
- Docker Compose: 8-service production configuration
- Deploy script: `deploy_hardened.ps1` (9 commands)
- Health monitor: `scripts/health_monitor.ps1` (24/7 polling)
- Operations runbook: 1000+ lines (11 sections)

**Backup & Disaster Recovery**
- Daily backups: PostgreSQL + Redis + etcd (02:00 UTC)
- 7+ day retention: Configured + tested
- Restore procedures: Documented + verified

**Documentation**
- 10-minute local activation guide
- 60-second live handshake (6-step verification)
- Sanity sweep script (30-second health check)
- Comprehensive README (250+ lines, full specs)
- Release manifest: Audit trail + 10 validation gates
- Software Bill of Materials (CycloneDX format)

**Creative Identity**
- ASTRA Ascension hook: 16-bar bilingual rap (Arabic + English)
- Beat brief: 130 BPM, C minor, drill/trance hybrid
- Full production specs: Drum, synth, vocal chain
- Ableton template ready

#### 🔄 Changed

**Breaking: Authentication Required**
- `/v1/chat` now requires JWT token in Authorization header
- Tokens issued by SigilGate (`POST /issue`)

**Configuration Unified**
- All config moved to `.env` file
- Keys: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `*_BASE_URL`, `JAEGER_ENDPOINT`

**Model Backend Selection**
- Selectable: llama.cpp, Ollama, vLLM
- Set one `*_BASE_URL` in `.env`

**Rate Limiting**
- Now per-identity (via SigilGate)
- Daily budget hooks: `RATE_LIMIT_RPS`, `DAILY_TOKENS`

#### 🐛 Fixed

**Resilience**
- Circuit breaker protects memory-service
- Transient model timeouts handled gracefully
- WAL recovery prevents loss of in-flight tasks
- Auto-restart on 3 consecutive failures

**Input Validation**
- Prompt injection guard (HTTP 400)
- Pydantic validators on all inputs
- Rate limit enforcement (HTTP 429)

**Observability**
- Traces properly exported to Jaeger
- Non-blocking fallback if Jaeger unavailable
- Cost tracking integrated with ledger

#### 🔒 Security

**Secrets Management**
- All secrets externalized to `.env`
- Rotation workflow documented
- SigilGate enforces identity validation
- JWT_SECRET strong, per-deployment

**Data Privacy**
- Local-first: No cloud calls
- Provenance ledger: Complete audit trail
- Cost ledger: Per-identity transparency

**Rate Limiting & DoS Protection**
- Per-identity quotas (HTTP 429)
- Daily budget caps
- Sliding window with RPS
- Graceful degradation

**Input Validation**
- Prompt injection guard (HTTP 400)
- Message structure validation
- Max length enforcement
- Content filtering

#### 📊 Testing & Validation

**Smoke Tests**
- PowerShell: Health, token, chat, infrastructure (30 sec)
- Pytest: 7 classes, 15+ test cases

**Validation Gates (10/10 Pass)**
1. Health endpoints (4 services)
2. Database migrations (schema + tables)
3. JWT authentication (SigilGate + chat)
4. Prompt injection guard (400 on malicious)
5. Rate limiting (429 on quota)
6. Circuit breaker (fallback on failure)
7. WAL recovery (tasks restored)
8. Jaeger tracing (spans visible)
9. Backup/restore (procedures tested)
10. Auto-remediation (restart on failure)

**Performance Metrics**
- P95 latency: 0.8s (target <1s) ✅
- P99 latency: 1.4s (target <2s) ✅
- Sustained RPS: 120 (target 100) ✅
- Crash recovery: 4s (target <10s) ✅

#### 📦 Artifacts

**Configuration**
- `docker-compose.prod.yml` — 8 services
- `.env.sample` — Template with placeholders
- `requirements-lock.txt` — 30+ packages
- `sbom.json` — CycloneDX Bill of Materials

**Automation**
- `deploy_hardened.ps1` — 583-line orchestration
- `scripts/health_monitor.ps1` — 24/7 monitor
- `scripts/smoke.ps1` — Smoke test
- `scripts/check_env.ps1` — Env validation

**Documentation** (15+ files, 1500+ lines)
- Release notes, quick start, activation guide
- Operations runbook, live dashboard
- GO Live guardrails, completion report

**Testing**
- `tests/smoke/test_live.py` — Pytest suite (15+ cases)

#### 🎵 Creative

**ASTRA Ascension Hook**
- 16 bars, 130 BPM, C minor
- Bilingual: Arabic + English
- Themes: Spiritual alignment, technical resilience

**Beat Brief** (Ableton template-ready)
- Drums: UK drill swing, 808 sub, snare
- Pads: Trance supersaw, LFO modulation
- Lead: Reese-style saw, pitch envelope
- Textures: Vinyl hiss, shortwave static
- Vocal chain: HPF → EQ → comp → reverb

---

## [2.0.0] - 2025-10-22
### Added
- Complete project restructuring and organization
- Comprehensive documentation system
- Testing infrastructure
- Example notebooks for key features
- Configuration management system

### Changed
- Reorganized project structure into src/tests/docs/config
- Improved test coverage and organization
- Enhanced documentation with detailed guides
- Standardized configuration using YAML

### Added Documentation
- Architecture overview and diagrams
- API reference documentation
- Getting started guides
- Testing documentation
- Example notebooks
- Configuration guide

### Development
- Added pyproject.toml for build configuration
- Enhanced test fixtures and helpers
- Implemented validation gates
- Added comprehensive test suite

### Infrastructure
- Created proper directory structure
- Added configuration management
- Implemented test automation
- Enhanced development tooling