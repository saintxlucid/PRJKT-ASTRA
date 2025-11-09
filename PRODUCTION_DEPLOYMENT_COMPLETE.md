# PROJECT ASTRA 1.0 - PRODUCTION DEPLOYMENT PACKAGE
## Complete System Overview & Deployment Guide

**Version:** 1.0.0  
**Date:** October 16, 2025  
**Status:** Production Ready ✅

---

## 🎯 Executive Overview

We built **ASTRA**: a production-grade, privacy-preserving AI runtime with two core online services, a vector knowledge layer, secure ingress, and an observability envelope that makes it safe to run and easy to operate.

**In plain terms:** You now have a system that calls tools and models on demand (Bridge) and ingests, embeds, and searches documents semantically (Documents)—backed by Qdrant for vectors, llama.cpp for LLM chat/completions, and wrapped in RBAC, quotas, rate limiting, TLS, monitoring, dashboards, alerts, chaos drills, and blue/green deployment. It's all containerized, CI/CD'd, and documented with a cutover runbook, quick reference, and pre-flight/smoke automation.

**What makes it production-ready:** We didn't just stand up a couple of REST endpoints. We engineered a production platform with strong defaults and safe failure modes. It's the difference between "it runs on my laptop" and "it keeps running at 3am on a weekend, and if something goes wrong, on-call knows exactly what to do."

---

## 🏗️ Core Services Architecture

### 1) Bridge Service (Tool Runtime Gateway)

**What it is:** A FastAPI microservice that acts as the control plane for tool execution. The Bridge receives structured tool calls from a planner/agent (or any client), enforces authentication, authorization, and throttling, dispatches to an adapter (e.g., LLM, safe shell, file reader), and records metrics and audit logs.

**Key Capabilities:**

**Adapters & Allowlists:**
- `llama` adapter: Speaks HTTP to a local llama.cpp server for chat/completions
- `file_read` adapter: Reads only within a safe root directory
- Optional `shell` adapter: Whitelist-only commands (discouraged in prod unless tightly controlled)
- Adapters registered in central registry, each with own timeout and per-tool allowlist

**RBAC & Per-Key Scopes:**
- Multiple API keys live in a file (Docker secret) referenced by `BRIDGE_KEYS_FILE`
- Each key declares scopes (e.g., `tool:llama`, `docs:search`, `admin`) and quotas (requests/minute and daily totals)
- Per-tool scope enforcement (`BRIDGE_ENFORCE_PER_TOOL_SCOPE=true`) means a key can only call tools it's allowed to

**Rate Limiting & Quotas:**
- Enforces requests-per-minute (RPM) and daily limits per key
- Prevents abuse, protects the LLM, and keeps capacity predictable

**Audit Logging:**
- Append-only JSON events record every tool call start/end/error
- Request IDs and summaries support security investigations, usage reporting, and compliance

**Prometheus Metrics:**
- Counters for call totals and status
- Histograms for latency
- Health endpoints give SREs visibility into load and performance

**Hardened Defaults:**
- Strong API key required on operational endpoints
- Minimal filesystem exposure (`BRIDGE_SAFE_ROOT`)
- Timeouts per tool to avoid runaway calls
- TLS termination through reverse proxy (NGINX in secure compose; Ingress on Kubernetes)

**Why it matters:** The Bridge is the safety boundary around tool execution. It centralizes auth, quotas, and auditing so you don't have to push security into every tool. It's also your uniform metrics surface for all tool usage, which is crucial for SLOs and cost controls.

---

### 2) Documents Service (Semantic Knowledge Interface)

**What it is:** A FastAPI microservice that ingests PDFs (easily extensible to DOC/HTML), chunks and embeds them using a real embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`), and upserts vectors into Qdrant.

**HTTP Endpoints:**
- `POST /v1/documents/ingest` — Multipart upload; performs text extraction (PyMuPDF), chunking with overlap, embedding, and Qdrant upsert
- `GET /v1/documents/search?q=...` — Semantic search via Qdrant; falls back to keyword search over JSONL index if Qdrant or embeddings unavailable

**Key Capabilities:**

**Production Embeddings:**
- Real sentence-transformers model
- Cacheable model (mount model cache volume to avoid repeated downloads)

**Vector Store:**
- Qdrant with COSINE distance
- Auto-created collection
- Robust upserts

**Fallback Path:**
- If `USE_QDRANT=false` or vector DB is down, operates with keyword search
- Preserves functionality (degraded but not dead)

**RBAC Alignment:**
- Reuses same keyfile scheme as Bridge
- Clients need `docs:ingest` or `docs:search` scopes

**Prometheus Metrics:**
- Ingest counts, ingest/search latency histograms
- First-class SLO inputs

**Security:**
- Non-root user in Docker
- Safe temp handling
- Production-grade settings via environment

**Why it matters:** This service turns your unstructured knowledge into retrievable memory for agents, assistants, or downstream apps. The semantic path (vectors) delivers relevance, while the keyword fallback ensures resilience.

---

### 3) Model and Vector Backends

**llama.cpp server:**
- Local LLM serving endpoint for fast, offline completions
- Configured behind the Bridge for the llama tool adapter
- Swappable with other providers later with no interface change to clients

**Qdrant:**
- Vector database storing embeddings and metadata
- Fast similarity search, collections, snapshots, and persistence via PVCs
- Dashboard exposed (in Docker stack)
- Health endpoints for synthetic probes and smoke tests

**Integration:** These backends are first-class services in both Docker Compose (dev/staging/single host) and Kubernetes (prod). They're monitored, alerted on, and have backup/restore steps in the runbooks.

---

## 🔒 Security Model

Security is not an afterthought—it's baked in:

### Authentication
- All privileged endpoints require an API key
- Keyfile (`BRIDGE_KEYS_FILE`) stores multiple keys with scopes and quotas
- Admin endpoints require admin scope: `/tools`, `/admin/usage`, `/admin/reload-keys`, `/audit/recent`

### Authorization
- Per-key scope enforcement means a key is only good for what you explicitly allow
- With `BRIDGE_ENFORCE_PER_TOOL_SCOPE`, even if a key is leaked, it cannot call unapproved tools

### Rate Limiting & Quotas
- Per-key RPM and daily caps
- In production this is often the difference between a blip and an outage

### Least-Privilege Adapters
- Shell adapter discouraged in prod; if used, whitelist-only
- File_read adapter confined to safe root
- Paths, timeouts, and allowlists enforced in code

### Transport Security
- TLS termination via NGINX (secure compose) or Kubernetes Ingress with cert-manager
- Instructions for issuing and rotating certificates

### Network Policies
- Kubernetes deny-all by default
- Allow policies permit only necessary egress (Bridge → LLM, Bridge/Docs → Qdrant, metrics → monitoring)
- Ingress from Ingress controller only
- Shrinks blast radius of any exploit

### Secrets Management
- Keyfiles mounted as Docker secrets or Kubernetes secrets
- Key rotation scripts (bash + PowerShell)
- Admin endpoint to hot-reload keys without redeploying

### Audit Trail
- Append-only JSON audit of calls (start/end/error)
- Critical for forensics and compliance (who called what, when, with which key, and what happened)

---

## 📊 Observability & SLOs

### Metrics
Both services expose `/metrics` with:
- Call counters by status
- Latency histograms
- Ingest/search counters
- Health endpoints for K8s probes and synthetic monitors

### Dashboards
**Grafana dashboard: "ASTRA - Ops Overview"**

**13 panels:**
1. Bridge Error Rate (%) gauge
2. Bridge P95 Latency (s) gauge
3. Qdrant Status (UP=1)
4. Bridge Calls/sec timeseries
5. Docs Search/min timeseries
6. Docs Ingest/sec timeseries
7. Bridge Error Rate timeseries with threshold
8. Bridge Latency Percentiles (P50/P90/P95/P99)
9. Bridge Calls by Status (success/error stacked)
10. PV /data Usage % gauge
11. Active Pods stat
12. Pod Restarts (1h) stat
13. Bridge Rate Limit Hits/sec

### Alerts
**PrometheusRule set (21 alerts):**

**Page-Level (Immediate):**
- `BridgeHighErrorRate` - >1% errors for 5m
- `BridgeHighLatencyP95` - >1s latency for 5m
- `BridgeCriticalLatencyP95` - >3s latency for 2m (CRITICAL)
- `BridgeDown` - Service unreachable
- `QdrantDown` - Vector DB unreachable
- `PVUsageHigh` - Disk >85%
- `PVUsageCritical` - Disk >95% (EMERGENCY)
- `BridgeUnexpectedRestart` - Pod restart detected
- `BridgeEndpointDown` - Synthetic probe failure
- `DocsEndpointDown` - Docs probe failure

**Warning-Level:**
- `DocsIngestDrop` - Low ingest rate
- `DocsIngestFailureRate` - >5% ingest failures
- `DocsSearchLatencyHigh` - Search P95 >2s
- `BridgeRateLimitHitFrequent` - Quota hits
- `BridgePodCPUThrottling` - CPU throttled
- `DocsPodMemoryHigh` - Memory >90%
- `HPAMaxedOut` - At max replicas
- `BridgeErrorBudgetBurnHigh` - SLO burn rate alert

**Enhanced with:**
- De-flapping (clamp_min for zero traffic, correct histogram aggregation)
- Runbook URLs in annotations
- Blackbox exporter probes for external endpoints

### Recording Rules
Pre-computed metrics for efficient dashboards:
- `bridge:error_rate:5m`
- `bridge:latency:p50:5m` through `p99:5m`
- `bridge:availability:1h`, `24h`, `30d`
- `bridge:error_budget_remaining:30d`
- Resource utilization (CPU, memory) per service
- Docs ingest/search rates

### SLOs & Error Budgets
**Documented in `SLO_REFERENCE.md`:**
- Availability target: 99.5% (216 min/month downtime budget)
- Monthly error budget
- Burn-rate alerts
- Operational guidelines (freeze deploys if burn rate spikes)
- Post-incident review requirements

---

## 🚀 Deployment & Release Engineering

### Docker
**Separate Dockerfiles:**
- Bridge and Docs with non-root users
- Minimal base images
- Healthchecks
- Environment-driven configuration

**Compose Variants:**
- **Secure compose:** NGINX TLS
- **Full stack compose:** Qdrant, llama, Prometheus, Grafana
- **Prod compose:** Single-host deployments

### Kubernetes
**Complete manifest set:**
- Namespace, secrets, PVCs
- Deployments with probes and resource limits
- Services (ClusterIP)
- Ingress with TLS annotations
- HPA (2-10 replicas bridge, 2-8 docs)
- ServiceMonitors for Prometheus Operator
- NetworkPolicies (deny-all + allowlists)
- Blue/Green deployment manifests

**Canary Cutover Script:**
- Health-checks green deployment
- Queries Prometheus for error-rate safety
- Switches Service selector
- Verifies post-switch health
- Auto-rollback if needed

### CI/CD
**GitHub Actions pipeline:**
- Builds both images
- Runs tests
- Pushes to registry (GHCR)
- Applies K8s manifests
- Secrets handled via GitHub + K8s
- Repeatable and auditable deploys

---

## 📚 Documentation & Runbooks

### Pre-Cutover
- **PRE_CUTOVER_CHECKLIST.md** - 10 categories (security, RBAC, metrics, backups, disk/HPA, etc.)
- **CUTOVER_FINAL_CHECKLIST.md** - 100-item comprehensive checklist with GO/NO-GO decision

### Cutover Execution
- **CUTOVER_RUNBOOK.md** - Rolling vs Blue/Green, rollback, monitoring windows, troubleshooting
- **CUTOVER_EXECUTION_GUIDE.md** - Printable, step-by-step with sign-offs and timeline
- **CUTOVER_QUICKSTART.md** - 10-minute execution guide
- **CUTOVER_QUICK_REF.md** - One-page "when things go wrong" commands

### Monitoring & Operations
- **MONITORING_SETUP_GUIDE.md** - 5-minute deployment for rules + dashboards + Alertmanager
- **CUTOVER_SILENCE_GUIDE.md** - Alertmanager silence patterns during deploy windows
- **SLO_REFERENCE.md** - SLO math, burn rates, monthly review checklist

---

## 🤖 Automation Scripts

### Validation & Testing
**`scripts/validate_preconditions.ps1`**
- Ensures secrets, PVCs, TLS, dangerous scopes, HPA, disk, and backups are correct
- 10 categories of checks
- Must pass before cutover

**`scripts/smoke_tests_production.ps1`**
- 10 automated tests: health, tool calls, ingest/search, metrics, Qdrant collections
- Validates end-to-end functionality
- Safe to run repeatedly

**`scripts/chaos_drills.ps1`**
- 4 automated failure drills:
  1. Qdrant down → docs fallback
  2. Bridge restart → alert fired, HPA maintains traffic
  3. Docs restart → service recovered
  4. Network partition → blocked then restored
- Validates alerts and fallbacks behave as designed

### Cutover Automation
**`scripts/cutover_canary.sh`** (Bash)
- Automated Blue/Green cutover with safety checks
- Pre-flight validation
- Health checks via port-forward
- Prometheus error rate and latency checks
- Service selector switch
- Post-switch health verification
- 60-second canary monitoring
- Auto-rollback on error spikes

**`scripts/cutover_status.sh`** (Bash)
- Live metrics dashboard in terminal
- Queries Prometheus for:
  - Bridge error rate, P95 latency, calls/sec
  - Docs ingest/search rates
  - Qdrant status
  - Pod health and restarts
  - PV usage
  - SLO tracking
  - Active alerts
- Colored output for instant visibility

### Security Operations
**`scripts/rotate_bridge_key.sh`** (Bash)  
**`scripts/rotate_bridge_key.ps1`** (PowerShell)
- Generate new admin+agent keys
- Backup old keys
- Update Kubernetes secret
- Trigger `/admin/reload-keys` endpoint
- Output new credentials

---

## 🔄 Data Flow (How a Request Moves Through the System)

### 1) Tool Call via Bridge

```
Client → POST /call {tool_name, args} + x-api-key
    ↓
Bridge authenticates key, checks scopes (tool:llama), checks quotas (RPM, daily)
    ↓
Request audited and timed (Prometheus histogram)
    ↓
llama adapter calls llama.cpp endpoint (local network)
    ↓
Result returned as JSON
    ↓
Counters and latency recorded; audit end event written
```

**Result:** A controlled, observable, permissioned tool call with uniform logging and metrics.

### 2) Document Ingestion & Search

```
User → POST /v1/documents/ingest (PDF) + docs:ingest key
    ↓
Extract text via PyMuPDF
    ↓
Chunk with overlap
    ↓
Embed each chunk (sentence-transformers)
    ↓
Upsert into Qdrant
```

```
User → GET /v1/documents/search?q=... + docs:search key
    ↓
Create query vector
    ↓
Vector similarity search against Qdrant
    ↓
If Qdrant/embeddings unavailable → fallback to JSONL keyword search
    ↓
Return results
```

**Metrics:** Ingest count/latency, search count/latency feed dashboards and alerts.

**Result:** External knowledge becomes first-class memory that remains usable even when vector path is degraded.

---

## 🛡️ Operations & Reliability Posture

### Availability
- ✅ Readiness and liveness probes prevent bad pods from serving traffic
- ✅ HPA maintains capacity; alert warns when maxed
- ✅ Blue/Green eliminates in-place risk and lets you test green before flipping

### Resilience
- ✅ Docs has keyword fallback when vectors are down
- ✅ Bridge rate limits prevent single-key overloads
- ✅ NetworkPolicies limit blast radius
- ✅ Chaos drills validate that alarms fire and fallbacks actually work

### Recoverability
- ✅ Qdrant snapshots and backing up indexes/models to object storage (documented)
- ✅ Runbooks for rollbacks, restores, and emergency downgrades

### Security
- ✅ Keys stored as secrets; rotation scripted and hot-reload supported
- ✅ No plaintext secrets in repos; TLS termination; admin endpoints restricted
- ✅ Shell adapter not enabled by default; if enabled, commands allowlisted only

### Observability
- ✅ Alerts cover error rate, latency, service down, PV usage, restarts, throttling, memory pressure, ingest failure rate
- ✅ Blackbox probes catch TLS/routing issues that internal metrics might miss
- ✅ Recording rules ensure dashboards stay fast under load

---

## 🔮 Extensibility & Future Evolution

We purposely separated orchestration (Bridge) and knowledge (Docs) so you can evolve each independently:

### More Adapters
Add `http`, `browser`, `db_query`, `retrieval`, or `task_runner` adapters under the same RBAC/metrics/audit umbrella.

### RAG Pipeline
You already have embeddings and search; add a retrieval middleware that feeds Bridge's llama calls with retrieved context (plus a reranker if needed).

### Web UI
The platform is API-first; a React/Tailwind UI can sit on top with login tied to API keys or OAuth—your monitoring and security already support it.

### Multi-Tenant
Scopes and quotas per key map naturally to per-tenant isolation. Namespacing in Qdrant is straightforward (collections per tenant or per domain).

### Model Diversity
Swap in different local models or hosted providers behind the same adapter interface without touching clients.

---

## ✅ What "Production-Ready" Actually Means Here

We answered the hard questions before they became incidents:

| Question | Answer |
|----------|--------|
| Who can call which tools, and how fast? | RBAC scopes + RPM/daily quotas |
| What happens if vectors go down? | Docs fallback to keyword search |
| How do we know it's healthy? | Metrics, probes, dashboards, blackbox checks |
| What if it breaks during deploy? | Blue/Green manifests + canary script + automatic rollback |
| How do we roll secrets? | Key rotation scripts + admin reload endpoint |
| How do we prevent security surprises? | NetworkPolicy deny-all + minimal allow rules, safe roots, allowlists |
| How do we keep costs/latency under control? | Rate limiting, recording rules, targeted alerts, clear SLO with burn-rate alarms |
| How do we teach ops to run it at 2am? | Pre-flight validator, smoke tests, quick reference, runbook, execution guide, chaos drills |

**That is the difference between "we have an app" and "we have an operational service."**

---

## 👨‍💻 Developer Experience

For developers, the system is intentionally boring in the best way:

### Local Dev
- `docker-compose.full.yml` spins up llama, Qdrant, Bridge, Docs, Prometheus, Grafana
- Sample scripts (`start_full_stack.ps1`, smoke tests) make it turnkey

### CI/CD
- One push builds, tests, and deploys

### APIs
- Minimal, well-named endpoints
- Tool calls consistent: `/call` with `{tool_name, args}`
- Docs are RESTful: `/ingest`, `/search`

### Testing
- Unit tests and integration patterns included
- Chaos drills simulate failure paths

### Documentation
- Everything is written down—the how and the why

---

## 📅 A Day in the Life (How You'll Actually Use It)

### Before Release
1. Run `validate_preconditions.ps1` and `smoke_tests_production.ps1`
2. Import the Grafana dashboard
3. Apply Prometheus rules

### Cutover
1. Use the canary script to switch Service to green deployment if health checks pass
2. Keep Grafana open at "Ops Overview" screen

### Operate
1. Let HPA scale with load
2. If an alert fires, click the runbook URL from the alert
3. Follow the steps (most have a 1–2 command fix or rollback)

### Maintain
1. Rotate admin key monthly
2. Check audit logs weekly
3. Review SLO burn monthly
4. Run chaos drills quarterly

### Improve
- Add adapters
- Wire RAG
- Land the web UI
- The platform is ready

---

## 🚀 FINAL DEPLOYMENT STEPS

### Prerequisites (Must Complete First)

1. **Deploy ServiceMonitors** (Prometheus scraping)
   ```bash
   kubectl apply -f k8s/servicemonitor-bridge-docs.yaml
   
   # Verify targets appear (wait 30 seconds)
   # Navigate to: http://prometheus.monitoring:9090/targets
   # Expected: astra-bridge-sm, astra-docs-sm, astra-qdrant-sm all "UP"
   ```

2. **Deploy Monitoring Stack**
   ```bash
   # PrometheusRule with de-flapped formulas
   kubectl apply -f k8s/prometheusrule-astrasafety.yaml
   
   # Recording rules for efficient dashboards
   kubectl apply -f k8s/prometheusrule-recordings.yaml
   
   # Blackbox Exporter for synthetic checks
   kubectl apply -f k8s/blackbox-exporter.yaml
   kubectl apply -f k8s/probe-astra.yaml
   
   # NetworkPolicy for security hardening
   kubectl apply -f k8s/networkpolicy-deny-all.yaml
   ```

3. **Import Grafana Dashboard**
   - Open Grafana: `https://grafana.example.com`
   - Click "+" → "Import"
   - Paste contents of `k8s/grafana-dashboard-astra-ops.json`
   - Select datasource: Prometheus
   - Click "Import"

---

### Step 1: Pre-Flight Validation (MUST BE ALL PASS)

```powershell
# Validate all preconditions
.\scripts\validate_preconditions.ps1 -Namespace astra

# Expected: ✅ VALIDATION PASSED - Ready for cutover
```

**If ANY check fails:** Fix the issue before proceeding. Do not skip this step.

---

### Step 2: Smoke Tests (MUST BE ALL PASS)

```powershell
# Set API keys
$env:ADMIN_KEY = "your-admin-key-here"
$env:AGENT_KEY = "your-agent-key-here"

# Run smoke tests
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com" `
    -QdrantUrl "http://qdrant.astra:6333"

# Expected: ✅ SMOKE TESTS PASSED - Safe to proceed
# ALL 10 TESTS MUST PASS
```

**If ANY test fails:** Investigate and fix. Do not proceed with broken production.

---

### Step 3: Live Status Snapshot (Verify GO Criteria)

```bash
# Check current production health
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```

**GO Criteria (ALL must be true):**
- ✅ Bridge Error Rate (%) < 1
- ✅ Bridge P95 Latency (s) < 1
- ✅ Qdrant Status: UP
- ✅ Bridge Calls/sec > 0 (if production traffic exists)
- ✅ No active critical alerts
- ✅ Zero pod restarts in last hour

**Also check Grafana:**
- Navigate to: `https://grafana.example.com/d/astra-ops`
- Confirm probes show UP (green)
- All panels showing data (not "No Data")

---

### Step 4: Canary Cutover (Blue/Green)

```bash
# Set environment variables
export NS=astra
export DEP_BLUE=bridge
export DEP_GREEN=bridge-green
export SVC=bridge
export PROM_URL="http://prometheus.monitoring:9090"

# Execute automated canary cutover
./scripts/cutover_canary.sh
```

**What the script does:**
1. ✅ Verifies green deployment is ready
2. ✅ Health checks green pods via port-forward
3. ✅ Checks current blue error rate and latency via Prometheus
4. ✅ Switches service selector from blue → green
5. ✅ Post-switch health check via service ClusterIP
6. ✅ 60-second canary monitoring (checks error rate every 5s)
7. ✅ **Auto-rollback** if error rate >1% for 3 consecutive checks

**Expected Output:**
```
╔═══════════════════════════════════════════════════════╗
║   ✅ CUTOVER COMPLETE                                  ║
╚═══════════════════════════════════════════════════════╝

Traffic switched from bridge to bridge-green
```

**If post-switch health fails:** The script automatically switches back to blue. Investigate before retrying.

---

### Step 5: Post-Cutover Monitoring (60 Minutes)

```bash
# Continuous monitoring (every 5 seconds)
watch -n 5 ./scripts/cutover_status.sh
```

**Monitor for:**
- ✅ Error rate < 0.5%
- ✅ P95 latency < 500ms
- ✅ No active alerts
- ✅ No pod restarts

**T+10 Minutes:**
```powershell
# Run smoke tests again
.\scripts\smoke_tests_production.ps1
# Expected: 10/10 tests PASS
```

**T+30 Minutes:**
- Check Grafana dashboard
- Verify all metrics stable
- No alerts firing

**T+60 Minutes (Success Criteria):**
- ✅ Error rate < 0.5% for 60 minutes
- ✅ P95 latency < 500ms for 60 minutes
- ✅ Zero pod restarts
- ✅ Zero alerts firing
- ✅ Smoke tests passing
- ✅ No errors in logs

---

### Step 6: Post-Cutover Cleanup

```bash
# Scale down blue deployment (keep for quick rollback)
kubectl -n astra scale deploy/bridge --replicas=0

# After 1 hour of stable green, delete blue
kubectl -n astra delete deploy/bridge

# Rotate admin key (security best practice)
./scripts/rotate_bridge_key.sh -Namespace astra

# Apply NetworkPolicy (if not already applied)
kubectl apply -f k8s/bridge-egress-policy.yaml
kubectl apply -f k8s/docs-egress-policy.yaml
```

---

## 🚨 Emergency Rollback (If Needed)

**Immediate rollback command:**
```bash
# Switch service back to blue
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'

# Scale up blue if scaled down
kubectl -n astra scale deploy/bridge --replicas=2

# Verify rollback
kubectl -n astra get endpoints bridge
./scripts/cutover_status.sh
```

**Rollback criteria:**
- Error rate > 2% for 5+ minutes
- P95 latency > 3s for 5+ minutes
- Pods crash-looping
- Critical alerts firing
- Data corruption detected

---

## 📊 Success Validation

**If all checks are green, then YES: We're there. 🚀**

You now have:
- ✅ Production-grade AI runtime
- ✅ Secure Bridge service with RBAC and quotas
- ✅ Semantic Docs service with fallback
- ✅ Vector storage (Qdrant) and LLM serving (llama.cpp)
- ✅ Complete monitoring and alerting
- ✅ Blue/Green deployment capability
- ✅ Automated validation and testing
- ✅ Comprehensive documentation and runbooks
- ✅ Security hardening (TLS, NetworkPolicy, secrets)
- ✅ SLO tracking and error budgets
- ✅ Operational excellence (chaos drills, key rotation)

---

## 📞 Support & Resources

### Documentation
- **Architecture:** `ARCHITECTURE.md`, `ARCHITECTURE_PRODUCTION.md`
- **Deployment:** All `CUTOVER_*.md` files
- **Operations:** `MONITORING_SETUP_GUIDE.md`, `SLO_REFERENCE.md`
- **Development:** `BRIDGE_MODULE_COMPLETE.md`, `DOCS_SYSTEM_COMPLETE.md`

### Scripts
- **Validation:** `scripts/validate_preconditions.ps1`
- **Testing:** `scripts/smoke_tests_production.ps1`, `scripts/chaos_drills.ps1`
- **Deployment:** `scripts/cutover_canary.sh`, `scripts/cutover_status.sh`
- **Security:** `scripts/rotate_bridge_key.sh`, `scripts/rotate_bridge_key.ps1`

### Kubernetes Manifests
- **Core:** `k8s/*-deployment.yaml`, `k8s/*-service.yaml`
- **Monitoring:** `k8s/prometheusrule-*.yaml`, `k8s/servicemonitor-*.yaml`
- **Security:** `k8s/networkpolicy-*.yaml`, `k8s/*-egress-policy.yaml`
- **Blue/Green:** `k8s/bridge-deployment-green.yaml`

### Emergency Contacts
- **On-Call SRE:** PagerDuty
- **Engineering Lead:** Slack DM
- **Slack Channels:** #sre-oncall, #sre-incidents, #astra-alerts

---

## 🎯 In One Sentence

**We built a secure, observable, resilient AI runtime—Bridge for tool execution, Docs for semantic memory, Qdrant for vectors, llama for inference—backed by RBAC, quotas, TLS, NetworkPolicies, CI/CD, blue/green, dashboards, alerts, fallbacks, chaos drills, and runbooks, so you can ship and sleep.**

---

**End of Deployment Package**

**Version:** 1.0.0  
**Status:** PRODUCTION READY ✅  
**Date:** October 16, 2025

