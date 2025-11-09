# A→Z Roadmap - PROJECT ASTRA v2.0
**Living Document** | Last Updated: October 9, 2025 | Status: Phase 1 Active

---

## 🎯 North Star Vision

**Local-first, privacy-preserving AI assistant with world-class operations**

- **Reliability:** ≥95% availability, p95 ≤1.2s, MTTR <15min
- **Privacy:** No cloud dependency, local embedding/LLM, encrypted storage
- **Simplicity:** Stateless API, pluggable infra, boring tech choices
- **Operability:** Observability-first, runbooks, graceful degradation

---

## 📋 A→Z Implementation Matrix

### ✅ A — Architecture & Alignment
**Status:** COMPLETE  
**Goal:** Clean layering, pluggable infrastructure, dependency injection

**Implemented:**
- Clean module boundaries: `api/`, `services/`, `infrastructure/`, `models/`, `utils/`
- DI pattern: services injected into routes
- Provider abstractions: `LLMProvider`, `VectorStore` interfaces
- Type hints + Pydantic validation throughout

**Artifacts:**
- `ARCHITECTURE.md` - Layered design documentation
- `IMPLEMENTATION_SUMMARY.md` - Module breakdown
- Dependency graph: API → Services → Infrastructure

**Next:** Write ADRs for key decisions (ADR-001: Why SQLite, ADR-002: Why llama.cpp, etc.)

---

### ✅ B — Backups & Business Continuity
**Status:** COMPLETE (Ops Hardening v1)  
**Goal:** RPO ≤24h, RTO ≤15min

**Implemented:**
- `scripts/backup_production.ps1` - Automated ZIP backups with 7-day retention
- Backs up SQLite DB + ChromaDB vector store
- Success marker file for validation
- Ready for Windows Task Scheduler (daily 03:30)

**Artifacts:**
- Backup script with error handling
- Restore procedure in `docs/RUNBOOK.md`
- `_BACKUP_OK` marker file

**Next:** Schedule Task, run restore drill, document RTO baseline

---

### ✅ C — Caching & Cost Controls
**Status:** PLANNED (Phase 2)  
**Goal:** Reduce LLM load 25–40%, improve p95 latency

**Design:**
- Semantic cache: hash(prompt + context) → cached response
- Idempotency keys for duplicate requests
- Short-lived in-memory cache (5min TTL)
- Cache hit ratio metrics

**Files to Create:**
- `src/astra/infrastructure/cache/semantic_cache.py`
- `src/astra/infrastructure/cache/redis_adapter.py` (optional)
- Metrics: `astra_cache_hits_total`, `astra_cache_misses_total`

**Acceptance:** Cache hit ratio ≥20% on repeated prompts, p95 improvement measurable

---

### ✅ D — Data & Memory Quality
**Status:** PLANNED (Phase 2)  
**Goal:** Relevance > dimensionality, precision@k trending up

**Design:**
- Weekly consolidation job: dedupe, merge similar, temporal decay
- Importance scoring (access frequency, recency, user feedback)
- PII redaction in stored memories
- Memory growth: linear not explosive

**Files to Create:**
- `scripts/consolidate_memories.py` (exists, needs enhancement)
- `src/astra/services/memory_quality.py`
- Metrics: `astra_memory_precision_at_k`, `astra_memories_total`

**Acceptance:** Precision@5 dashboard shows improvement post-consolidation

---

### ⏳ E — Embeddings Strategy
**Status:** CURRENT (MiniLM-384d)  
**Goal:** Migrate to BGE-M3 when scale/GPU warrants

**Current:**
- `all-MiniLM-L6-v2` (384 dimensions)
- CPU-friendly, fast inference
- Good enough for <10k memories

**Migration Path:**
1. Abstract embedding interface (already done in `VectorStore`)
2. Write re-embed playbook with cutover flag
3. Dry-run on copy of vector store
4. Switch with rollback path

**Trigger:** >10k memories, GPU available, or quality ceiling hit

---

### ⏳ F — Fallbacks & Failure Modes
**Status:** PLANNED (Directive 003 - Chaos Drill)  
**Goal:** Graceful degradation, zero crashloops

**Design:**
- Circuit breaker on LLM timeouts (3 failures → open for 30s)
- OpenAI/vLLM fallback behind feature flag
- Canned response for outage: "Assistant temporarily unavailable"
- 503 Service Unavailable (not 5xx crashes)

**Files to Create:**
- `src/astra/infrastructure/llm/circuit_breaker.py`
- `src/astra/infrastructure/llm/fallback_provider.py`
- Chaos test: `tests/chaos/test_llm_down.py`

**Acceptance:** LLM down → 503 with retry-after, no crashes, metrics increment

---

### ✅ G — Governance & Guardrails
**Status:** PARTIAL (needs PII redaction)  
**Goal:** Prevent unsafe/PII leakage

**Current:**
- Request validation via Pydantic models
- Structured logging with redaction helpers

**Needs:**
- Regex/NER redaction for SSN, credit cards, emails
- Output content filters
- Audit log for sensitive operations

**Files to Create:**
- `src/astra/utils/redaction.py`
- `src/astra/utils/content_filter.py`

---

### ✅ H — Harmony & Prompt Discipline
**Status:** COMPLETE  
**Goal:** Zero CoT leakage, reproducible formatting

**Implemented:**
- Harmony chat format enforced in `harmony.py`
- `StopTokenManager` prevents CoT leakage
- Sampling preset: `gptoss-strict` (locked temperature/top_p)
- CoT stripped from saved conversation history

**Tests:** 100% passing for Harmony format parsing

**Artifacts:**
- `src/astra/infrastructure/llm/harmony.py`
- `tests/unit/test_harmony_parse.py`

---

### ✅ I — Identity & Auth
**Status:** PHASE 1 COMPLETE (API Key)  
**Goal:** Phase 2 = JWT, Phase 3 = RBAC

**Current (v2.0):**
- API key authentication via `X-API-Key` header
- Constant-time comparison (timing attack protection)
- Per-key rate limiting (120 req/60s default)
- Exempt paths: health, metrics, docs

**Next (Phase 3):**
- JWT with rotating keys
- Scope-based authorization
- Per-user/per-key quotas in DB

**Files for Phase 3:**
- `src/astra/security_jwt.py`
- `src/astra/models/auth.py`

---

### ✅ J — Job Scheduling
**Status:** READY (not scheduled)  
**Goal:** Automation without cron-chaos

**Jobs Defined:**
- **Daily 03:30:** Backup production data
- **Weekly Sunday 03:45:** Memory consolidation
- **Monthly:** Vacuum database, rotate logs

**Next:** Create Windows Task Scheduler entries, document in Ops Calendar

**Artifacts:**
- `scripts/backup_production.ps1` (ready)
- `scripts/consolidate_memories.py` (needs enhancement)
- `docs/OPS_CALENDAR.md` (to create)

---

### ✅ K — KPIs & SLOs
**Status:** DEFINED (monitoring active)  
**Goal:** Track health, enforce gates

**SLOs:**
- Availability ≥95%
- p50 ≤500ms
- p95 ≤1.2s
- p99 ≤2.5s
- Sustained load: 20 rps
- Error rate <1% (excluding client 4xx)

**Metrics Live:**
- `astra_requests_total{status}`
- `astra_request_duration_seconds`
- `astra_queue_depth`, `astra_queue_wait_seconds`
- `astra_limiter_per_key_blocked_total`

**Next:** Error budget tracking, release gates tied to SLO deltas

---

### ✅ L — LLM Runtime Strategy
**Status:** CPU (llama.cpp), GPU path ready  
**Goal:** Optimal flags per machine, provider abstraction

**Current:**
- llama.cpp @ 127.0.0.1:8001
- Model: GPT-OSS-20B (Q4_K_M, 11.27GB)
- Flags: Default (needs tuning)

**Tools:**
- `scripts/benchmark_llama_flags.py` - Test flag combinations
- Provider abstraction ready for vLLM/OpenAI

**Next (Directive 001):** Benchmark 3 flag sets, lock optimal config

---

### ✅ M — Metrics & Monitoring
**Status:** COMPLETE (Prometheus + Grafana staged)  
**Goal:** Visibility into all subsystems

**Metrics Live:**
- HTTP requests, latency (by method/path/status)
- Token usage (prompt/completion)
- Queue depth, wait time
- Per-key allow/block rates
- Memory stats (coming)

**Dashboards:**
- `ops/grafana_astra_dashboard.json` (10 panels)
- Ready to import

**Alerts (to configure):**
- Queue depth >50 for 2min
- Per-key block rate >10/sec for 2min
- Error rate >5% for 5min
- p95 latency >1.5s for 5min

---

### ⏳ N — Networking & Exposure
**Status:** LOCAL ONLY (safe default)  
**Goal:** Controlled external access when needed

**Current:** 127.0.0.1:8080 (localhost only)

**When Exposing:**
- CORS allowlist (specific origins only)
- IP allow/deny lists
- TLS proxy (nginx/Caddy)
- Rate limiting (already in place)

**Checklist to Create:** `docs/EXTERNAL_EXPOSURE_CHECKLIST.md`

---

### ✅ O — Observability & Tracing
**Status:** COMPLETE (Ops Hardening v1)  
**Goal:** Root cause in <5min

**Implemented:**
- Request ID middleware (UUID per request)
- Structured logging (JSON in production)
- Request ID in all logs + response headers
- Trace request: API → Service → LLM → DB

**Next (Phase 3):** OpenTelemetry exporter for Jaeger/Zipkin

**Artifacts:**
- `src/astra/api/middleware/request_id.py`
- `src/astra/utils/logging.py` (contextvars)

---

### ✅ P — Performance & Capacity
**Status:** PHASE 1 COMPLETE (Directive 001)  
**Goal:** Sustainable 20 rps

**Implemented:**
- Per-key token bucket rate limiting
- Queue guard (max 64 queued, 32 inflight)
- Request shedding (503 when saturated)
- Metrics for queue depth, wait time

**Load Test (to run):**
- 20 rps sustained for 10min
- Measure p50/p95/p99, error rate
- Baseline for future releases

**Next:** CI load test gate, capacity report per release

---

### ⏳ Q — Quality Gates
**Status:** PARTIAL (tests exist, no CI gates)  
**Goal:** Ship only green builds

**Current:**
- 46/49 unit tests passing
- 12 new capacity tests passing
- Integration tests exist

**Needs:**
- GitHub Actions workflow (or equivalent CI)
- Smoke tests + load baseline gate
- Fail-fast on test failures
- Artifact exports (test reports, coverage)

**Files to Create:**
- `.github/workflows/ci.yml`
- `scripts/run_load_baseline.ps1`

---

### ✅ R — Runbooks & Recovery
**Status:** COMPLETE (Ops Hardening v1)  
**Goal:** MTTR <15min

**Implemented:**
- `docs/RUNBOOK.md` - 5 error scenarios with recovery steps
- Error scenarios: DB locked, LLM timeout, OOM, rate limit, unauthorized
- PowerShell recovery commands
- Escalation procedures (skeleton)

**Next:** Tabletop exercise, measure actual TTR

---

### ✅ S — Security
**Status:** STRONG (constant-time, rate limits)  
**Goal:** Least privilege + invariants

**Implemented:**
- API key with constant-time compare (timing attack protection)
- Per-key rate limiting (prevents DoS)
- Log redaction helpers
- Secrets never logged
- Exempt paths for health/metrics

**Next (Phase 3):**
- Dependency vulnerability scanning
- Security checklist per release
- Penetration test (basic)

---

### ✅ T — Tooling & Developer Experience
**Status:** EXCELLENT  
**Goal:** 5-minute onboarding

**Implemented:**
- `QUICKSTART.md` - 5-minute guide
- `scripts/` - PowerShell automation
- Validation scripts
- Comprehensive docs

**Quality:**
- Linting (ruff, black, mypy available)
- Type hints throughout
- Pre-commit hooks (to add)

**Next:** Document pre-commit setup

---

### ⏳ U — UX & Delivery Surfaces
**Status:** PLANNED (Directive 002 - SSE Streaming)  
**Goal:** Real-time streaming, minimal operator console

**Current:**
- OpenAPI docs @ /docs
- Simple test UI (test_ui.html)

**Next (Directive 002):**
- SSE streaming endpoint `/v1/chat/stream`
- Perceived latency improvement
- EventSource demo in browser

**Later (Phase 3):**
- Minimal operator console (HTMX)
- Health dashboard, conversation list, job status

---

### ⏳ V — Versioning & Releases
**Status:** v2.0.0 (semver started)  
**Goal:** Predictable cadence

**Current:** v2.0.0 (production-grade baseline)

**Next:**
- v2.1.0: SSE streaming, chaos tests, JWT auth
- v2.2.0: Semantic cache, memory consolidation
- v2.3.0: Operator console, pgvector adapter

**Artifacts Needed:**
- `CHANGELOG.md` (to create)
- Release bundle script
- Rollback playbook per version

---

### ⏳ W — Workflows & Automation
**Status:** PLANNED (Phase 2)  
**Goal:** Boring operations

**Workflows to Automate:**
- Nightly: Database vacuum
- Daily: Backups
- Weekly: Memory consolidation
- Monthly: Log rotation, key rotation option

**Next:** Create `docs/OPS_CALENDAR.md` with schedule

---

### ⏳ X — eXperiments & A/B
**Status:** PLANNED (Phase 4)  
**Goal:** Improve quality safely

**Experiment Ideas:**
- Sampling preset A/B (strict vs creative)
- Semantic cache on/off
- Retrieval depth: top-5 vs top-10
- Embedding model comparison

**Infrastructure Needed:**
- Feature flags (environment-based for now)
- Experiment toggles in config
- A/B analyzer script

---

### ⏳ Y — Yield & Economics
**Status:** TRACKED (metrics in place)  
**Goal:** Maximize throughput per watt/$

**Current Tracking:**
- Token usage metrics
- Queue efficiency (wait time, depth)
- Request rate vs error rate

**Optimizations:**
- Cache > recompute (Phase 2)
- Compress memories (Phase 2)
- Detect repeated prompts (Phase 2)

**Next:** Monthly "ops economics" report (throughput, cache savings, cost avoidance)

---

### ⏳ Z — Zero-Downtime Standards
**Status:** DESIGNED (not implemented)  
**Goal:** Never break production

**Needed:**
- Blue/green start script
- Config hot-reload (without restart)
- Feature flags (env-based now, DB later)
- Canary test suite

**Files to Create:**
- `scripts/blue_green_deploy.ps1`
- `scripts/canary_test.ps1`
- Deploy checklist with canary criteria

---

## 📅 Phased Timeline

### ✅ Phase 0: V2.0 Hardening (COMPLETE)
**Duration:** October 1-8, 2025

**Delivered:**
- Backups with retention
- API key authentication
- Request ID tracing
- Queue guard + concurrency limiter
- Prometheus metrics
- Comprehensive documentation
- 93.9% test coverage (46/49 passing)

---

### ⏳ Phase 1: Capacity & Safety (ACTIVE — Week 1-2)
**Duration:** October 9-22, 2025  
**Current:** Directive 001 deployment in progress

**Goals:**
- ✅ Per-key rate limiting (code complete, deploying)
- ✅ Queue metrics + Grafana alerts (code complete, importing)
- ⏳ SSE streaming endpoint (Directive 002)
- ⏳ Health drill-down (DB/LLM/ChromaDB status)
- ⏳ CI load baseline (20 rps, 10min, p95 gate)

**Gate to Phase 2:**
- 3 green load baselines in a row
- Alerts tuned (no false positives for 3 days)
- Runbook validated with tabletop exercise

---

### ⏳ Phase 2: Reliability & Memory (Weeks 3-4)
**Goals:**
- Weekly memory consolidation job
- Semantic cache (opt-in, 20% hit rate target)
- Chaos tests: LLM down, DB lock, vector lag
- Fallback provider (OpenAI behind flag)

**Gate to Phase 3:**
- Chaos suite passes (graceful degradation)
- Cache hit ratio ≥20% on repeated prompts
- No 5xx crashes during chaos tests

---

### ⏳ Phase 3: Security & UX (Month 2)
**Goals:**
- JWT authentication + rotating keys
- Minimal operator console (HTMX)
- Export/Import conversations
- PII redaction in memories

**Gate to Phase 4:**
- Operator completes routine tasks without shell
- Auth logs/alerts active
- Security checklist passing

---

### ⏳ Phase 4: Scale-Ready (Month 3)
**Goals:**
- Postgres/pgvector adapter (behind flag)
- Blue/green deployment scripts
- Config hot-reload
- Load @ 40 rps with graceful shedding

**Gate to Phase 5:**
- 40 rps sustained, p95 <1.2s
- Fallback smoke test passes
- Zero-downtime deploy validated

---

### ⏳ Phase 5: Model Upgrade (Quarter)
**Goals:**
- Hardware assessment for GPU
- BGE-M3 or e5-large if warranted
- Re-embed playbook executed
- Model router (preset choice by task)

**Gate:**
- Quality improvement ≥10% on benchmark
- No SLO regression
- Rollback tested

---

## 🎯 Success Metrics (Track Weekly)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **Availability** | ≥95% | TBD | ⏳ Track after Phase 1 |
| **p50 Latency** | ≤500ms | TBD | ⏳ Baseline this week |
| **p95 Latency** | ≤1.2s | TBD | ⏳ Baseline this week |
| **p99 Latency** | ≤2.5s | TBD | ⏳ Baseline this week |
| **MTTR** | <15min | TBD | ⏳ Measure in drill |
| **Backup Success** | 7/7 days | 0/7 | ⏳ Schedule task |
| **Test Coverage** | ≥95% | 93.9% | ✅ Good |
| **5xx Error Rate** | <1% | TBD | ⏳ Track in Grafana |
| **Crashloops (30d)** | 0 | 0 | ✅ Stable |
| **Memory Precision@5** | Trend ↑ | Baseline | ⏳ Implement tracking |

---

## 🚨 Top 5 Risks & Mitigations

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| **Single LLM dependency** | High | Fallback provider (Phase 2) | ⏳ Planned |
| **Queue starvation** | Medium | Per-key budgets (Phase 1) | ✅ Implemented |
| **Vector bloat** | Medium | Consolidation job (Phase 2) | ⏳ Planned |
| **Auth bypass** | High | Constant-time compare, JWT (Phase 3) | ✅ Mitigated |
| **SLO regressions** | Medium | Load test gates (Phase 1) | ⏳ Implementing |

---

## 📚 Living Artifacts (Keep Updated)

| Document | Purpose | Update Frequency |
|----------|---------|------------------|
| `DEPLOYMENT_STATUS.md` | Last 7 days ops truth | Daily |
| `RUNBOOK.md` | Recovery procedures | After incidents |
| `PRODUCTION_ENHANCEMENTS.md` | Backlog + decisions | Weekly |
| `CHANGELOG.md` | User-visible changes | Per release |
| `ADRs/` | Architecture decisions | As needed |
| **This file** | Roadmap progress | Weekly |

---

## 🎬 Next Actions (Monday Start)

### Immediate (Directive 001 — Today)
1. ✅ Deploy per-key rate limiting
2. ✅ Validate queue metrics
3. ⏳ Import Grafana dashboard + alerts
4. ⏳ Benchmark llama.cpp flags
5. ⏳ Git commit capacity controls

### This Week (Directive 002)
1. Implement SSE streaming endpoint
2. Run load baseline (20 rps, 10min)
3. Health drill-down endpoint
4. Schedule backup task
5. Measure SLO baseline

### Next Week (Directive 003)
1. Chaos test: LLM down
2. Implement circuit breaker
3. Fallback provider (OpenAI flag)
4. Tabletop exercise (RUNBOOK validation)
5. Memory consolidation job

---

## 🏆 Phase Gates & Decision Points

**Phase 1 → Phase 2 Gate:**
- [ ] 3 consecutive green load baselines (20 rps, p95 <1.2s)
- [ ] Alerts tuned (no false positives for 3 days)
- [ ] Runbook validated in tabletop exercise
- [ ] SSE streaming production-ready

**Phase 2 → Phase 3 Gate:**
- [ ] Chaos tests passing (LLM down, DB lock, vector lag)
- [ ] Cache hit ratio ≥20%
- [ ] No 5xx crashes during chaos
- [ ] Fallback provider smoke tested

**Phase 3 → Phase 4 Gate:**
- [ ] JWT auth implemented + tested
- [ ] Operator console handles routine tasks
- [ ] Security checklist passing
- [ ] Export/Import working

**Phase 4 → Phase 5 Gate:**
- [ ] 40 rps sustained load (p95 <1.2s)
- [ ] pgvector smoke tested
- [ ] Zero-downtime deploy validated
- [ ] Blue/green scripts working

---

## 🎓 Lessons & Adaptations

**What's Working:**
- Clean architecture → easy to extend
- PowerShell-first ops → Windows-native
- Additive changes → low risk deploys
- Comprehensive docs → faster debugging

**What to Improve:**
- Need CI/CD pipeline (Phase 1)
- Consolidation job needs work (Phase 2)
- ADRs missing (document decisions)
- Load testing not automated yet

**Adaptations Made:**
- Chose per-key limiting over global (better fairness)
- SQLite WAL instead of Postgres (simplicity wins for now)
- llama.cpp over vLLM (CPU-first, less complex)

---

**Last Updated:** October 9, 2025  
**Next Review:** October 16, 2025 (after Phase 1 gate)  
**Maintained By:** Operations Lead

---

**🚀 Current Focus: Directive 001 — Capacity Controls Go-Live**
