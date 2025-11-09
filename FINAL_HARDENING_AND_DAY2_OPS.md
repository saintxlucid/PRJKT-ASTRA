# 🛡️ FINAL HARDENING & DAY-2 OPS GUIDE
**ASTRA Production Platform - Last-Mile Security & Operational Excellence**

**Version:** 1.0.0  
**Date:** October 16, 2025  
**Status:** Production Hardening Checklist ✅

---

## 🎯 GO/NO-GO Snap Verdict

**Verdict: ✅ GO**

Your package covers services, security, CI/CD, blue/green, observability, SLOs, chaos drills, and rollback. It's the complete set.

---

## 🚦 Five Hard Gates (Before You Flip)

These are already in your scripts - this is the distilled checklist:

### 1. Preflight & Smoke Tests
```powershell
.\scripts\validate_preconditions.ps1
.\scripts\smoke_tests_production.ps1
```
**Expected:** ALL PASS

### 2. Error Rate
```bash
sum(rate(bridge_calls_total{status="error"}[5m])) / 
clamp_min(sum(rate(bridge_calls_total[5m])), 1) * 100
```
**Target:** < 1% (5m window)

### 3. P95 Latency
```bash
histogram_quantile(0.95, sum by (le) (rate(bridge_call_duration_seconds_bucket[5m])))
```
**Target:** < 1s (5m window)

### 4. Qdrant + Probes
**Target:** UP=1, blackbox probes green

### 5. PV Headroom
```bash
100 * (1 - (node_filesystem_avail_bytes{mountpoint="/data"} / 
           node_filesystem_size_bytes{mountpoint="/data"}))
```
**Target:** < 80% used

**If all green → flip with canary script**  
**If any red → halt, fix, re-run preflight**

---

## 📊 What to Watch in First 2 Hours (T+0 → T+2h)

Keep **"ASTRA – Ops Overview"** dashboard open and focus on:

| Metric | Target | Alert If |
|--------|--------|----------|
| Bridge Error Rate (%) | < 1% | > 1% sustained |
| Bridge P95 Latency (s) | < 1s | > 1s sustained |
| Qdrant UP | 1 | 0 for > 30s |
| Pod Restarts | 0 | > 0 unexplained |
| PV /data Usage (%) | < 80% | > 85% |

**If `BridgeHighErrorRate` or `BridgeHighLatencyP95` fire:**
- Pause the cutover
- Check recent deploys and adapter changes
- Be ready to toggle back to blue (canary script auto-rolls back on failure)

---

## 🗓️ 7-Day Stabilization Plan

**Goal:** Prove the platform meets its SLOs, the backup/restore path is real, and ops can handle incidents without you.

### Day 0 (T+0 to T+2h)
- [ ] Run `cutover_status.sh` in watch loop (5s interval)
- [ ] Keep Alertmanager silence scoped only to deploy-noise
- [ ] Remove silence as soon as steady
- [ ] Re-run smoke tests at T+10m and T+60m (expect 10/10)

### Day 1: Security & Keys
- [ ] Rotate admin key with script: `./scripts/rotate_bridge_key.sh`
- [ ] Verify `/admin/reload-keys` succeeds
- [ ] Test Qdrant snapshot + restore in scratch namespace
- [ ] Capture restore steps in runbook
- [ ] Validate NetworkPolicies: Bridge can only reach LLM, Qdrant, monitoring

### Day 2: Quotas & Performance
- [ ] Calibrate rate limits/quotas: confirm no legitimate workflows throttled
- [ ] Tighten any overly generous keys
- [ ] Confirm Prometheus recording rules drive dashboards (no heavy PromQLs in panels)
- [ ] Check for any per-key anomalies in `/admin/usage`

### Day 3: Chaos & Audit
- [ ] Run chaos drills during low-traffic window:
  - Qdrant down → docs fallback
  - Bridge restart → alerts fire, HPA maintains traffic
- [ ] Confirm alerts + fallback behave as designed
- [ ] Review audit logs for anomalous keys or unexpected tool mixes

### Day 4: Backup Validation
- [ ] Backup validation: copy latest model & index snapshots off-cluster
- [ ] Restore in staging environment
- [ ] Run semantic search smoke test on restored data
- [ ] Document exact timing (RTO/RPO reality)

### Day 5: SLO Burn Review
- [ ] Export 5 days of error rate + P95 metrics
- [ ] Verify both sit within 99.5% target envelope
- [ ] Calculate error budget burn rate
- [ ] Check for any burn-rate spikes

### Day 6: Security Touch-Ups
- [ ] Ensure no key has `tool:shell` in prod
- [ ] Confirm TLS certs expiry > 30 days; note rotation date
- [ ] Verify no plaintext secrets in any repo or CI logs
- [ ] Check ingress for TLS 1.2+ and strong cipher suites

### Day 7: Stabilization Report
- [ ] Write 1-page stabilization report:
  - Uptime achieved
  - Error budget burn
  - Incidents (if any)
  - Concrete follow-ups
- [ ] Tag release: `prod-v1.0.0-stable`
- [ ] Archive stabilization report

---

## 🔒 Final-Mile Hardening (Quick Wins You Can Do Now)

### Security

#### 1. Enforce Per-Tool Scopes
```bash
# In deployment manifest or .env
BRIDGE_ENFORCE_PER_TOOL_SCOPE=true
```
- [ ] Confirm no prod keys include `tool:shell`
- [ ] Remove shell adapter entirely unless documented need

#### 2. Lock Request Size Limits
```nginx
# In Ingress or NGINX config
client_max_body_size 50m;
client_body_timeout 60s;
proxy_read_timeout 120s;
```
- [ ] Set for docs service to avoid surprise giant uploads
- [ ] Add friendly error pages for 413 (Request Too Large)

#### 3. Pin & Sign Images
```dockerfile
# In Dockerfiles - pin base image digests
FROM python:3.11-slim@sha256:abc123...
```
- [ ] Pin base image digests in Dockerfiles
- [ ] Sign releases with cosign
- [ ] Verify via admission policy (reject unsigned images)

#### 4. SBOM + Vuln Scan in CI
```yaml
# Add to .github/workflows/ci-cd.yml
- name: Generate SBOM
  run: syft . -o json > sbom.json
  
- name: Scan for vulnerabilities
  run: grype sbom.json --fail-on high
```
- [ ] Add Syft (SBOM generation)
- [ ] Add Grype or Trivy scanning
- [ ] Store SBOM artifacts
- [ ] Fail builds on high/critical CVEs

#### 5. Secret Hygiene
- [ ] Validate nothing sensitive in container env dumps
- [ ] Set `no_log` / redact patterns for audit entries
- [ ] Check logs don't leak API keys in headers/stacks

#### 6. Non-Root + Read-Only FS
```yaml
# In K8s deployment
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  readOnlyRootFilesystem: true
volumes:
  - name: tmp
    emptyDir: {}
volumeMounts:
  - name: tmp
    mountPath: /tmp
```
- [ ] Already running non-root ✅
- [ ] Add `readOnlyRootFilesystem: true`
- [ ] Add explicit writeable mounts where needed

---

### Resilience

#### 1. Backpressure Safety
- [ ] Verify llama/qdrant client timeouts + retries with jitter
- [ ] Cap Bridge concurrency if upstreams saturate
- [ ] Consider uvicorn workers + queue back-pressure

#### 2. Graceful Shutdown
```yaml
# In K8s deployment
spec:
  terminationGracePeriodSeconds: 60
```
- [ ] Confirm `terminationGracePeriodSeconds` large enough to finish in-flight calls
- [ ] Add SIGTERM hooks if needed for cleanup

#### 3. Docs Fallback Banner
```python
# When fallback (keyword) is active
docs_fallback_active.set(1)  # Prometheus gauge
logger.warning("Vector search unavailable, using keyword fallback")
```
- [ ] Log structured event when fallback active
- [ ] Export gauge `docs_fallback_active=1`
- [ ] Make visible in dashboard

---

### Observability

#### 1. Per-Tool Latency Histograms
```python
# Ensure bridge_call_duration_seconds has tool label
bridge_call_duration_seconds.labels(tool="llama", status="success").observe(duration)
```
- [ ] Export totals with `tool="..."` label
- [ ] Break out P95 by tool in Grafana panels

#### 2. Per-Key Usage Top-N
- [ ] Add `/admin/top-keys` view (top keys by RPM/error)
- [ ] Expand `/admin/usage` to surface noisy tenants
- [ ] Great for noisy-tenant detection

#### 3. Runbook URLs in Alerts
- [ ] Spot check alert annotations match exact sections in `CUTOVER_QUICK_REF.md`
- [ ] Verify links are reachable (not dead)

---

### Compliance & Privacy (Lightweight but Useful)

#### 1. Data Retention
- [ ] Set log/audit retention policy in writing (e.g., 30/90 days)
- [ ] Confirm log shipper enforces rotation
- [ ] Document in `OPERATIONS.md`

#### 2. PII Sanitization
- [ ] Add one-liner redactor hook for common identifiers
- [ ] Sanitize before persisting audit entries
- [ ] If user content might leak into tool args

---

## 🛠️ Day-2 Guardrails (What Keeps SRE Sane)

### SLOs & Burn

**Lock the SLO target:**
- Availability: 99.5% (216 min/month downtime budget)
- P95 latency: < 500ms for Bridge
- Keep burn-rate alerts active

**Deploy freeze rule:**
- If 2h burn rate > threshold → freeze non-critical deploys
- Document in runbook

---

### Capacity & Scaling

**HPA Settings:**
```yaml
# Set min/max to leave headroom for deploy waves
minReplicas: 2
maxReplicas: 10
```

**Weekly capacity snapshot:**
- [ ] Save as Grafana report: calls/sec, CPU/mem, HPA position
- [ ] Track week-over-week growth

**Qdrant baselines:**
- [ ] Record QPS + latency baselines after cutover
- [ ] Use as regression line for future embed model swaps

---

### Backups & Restore

**Monthly restore dry-run:**
- [ ] Restore to throwaway namespace
- [ ] Write down exact steps + timings
- [ ] Document RTO/RPO reality (not theory)
- [ ] Update runbook with actual restore times

---

### Change Management

**Two-lane deploy policy:**
- **Low-risk changes:** Any time (config tweaks, non-breaking API changes)
- **Risky changes:** Only within staffed window (major version bumps, schema changes)
- Tie to Alertmanager silence templates

---

## 🎪 Chaos & Readiness Mini-Drills (Fast, Safe)

### Existing Drills (From `chaos_drills.ps1`)
1. ✅ Qdrant down → docs fallback
2. ✅ Bridge restart → alert fired, HPA maintains traffic
3. ✅ Docs restart → service recovered
4. ✅ Network partition → blocked then restored

### New Micro-Drills (<5 Minutes Each)

#### Drill 5: Slow Vector Store
```bash
# Limit Qdrant CPU to throttle
kubectl -n astra set resources deploy/qdrant --limits=cpu=100m

# Verify DocsSearchLatencyHigh fires
# Confirm dashboards show fallback OFF (semantic still working but slower)

# Restore
kubectl -n astra set resources deploy/qdrant --limits=cpu=1000m
```

#### Drill 6: Quota Spike
```bash
# Hammer Bridge with single key until RateLimitHit fires
for i in {1..1000}; do
  curl -H "x-api-key: test-key" https://bridge.example.com/call &
done

# Verify:
# - RateLimitHit alert fires
# - Error rate stays low
# - Other keys unaffected (per-key isolation)
```

---

## ⚡ Performance & Cost Sanity

### Embedding Cache Volume
```yaml
# Mount cache volume for sentence-transformers
volumes:
  - name: model-cache
    persistentVolumeClaim:
      claimName: model-cache-pvc
volumeMounts:
  - name: model-cache
    mountPath: /root/.cache/torch
```
- [ ] Avoid cold-start downloads
- [ ] Save bandwidth/time on rolling deploys

### Model Sizing Plan
**Document in `DEPLOYMENT_SUMMARY.md`:**

| Model | Dimensions | Qdrant Vectors Size | QPS Impact | Storage Impact |
|-------|------------|---------------------|------------|----------------|
| all-MiniLM-L6-v2 | 384 | ~1.5 KB/vector | Baseline | Baseline |
| all-mpnet-base-v2 | 768 | ~3 KB/vector | -10% QPS | 2x storage |

- [ ] Keep table for finance/SRE to grasp storage/QPS tradeoffs
- [ ] Document quick toggle process

### Profiling Switch
```python
# Add runtime flag for debugging
if os.getenv("ENABLE_PROFILING") == "true":
    uvicorn.run(app, access_log=True)
```
- [ ] Enable uvicorn access logs only during investigations
- [ ] Off by default to keep noise low

---

## 📋 Governance & Lifecycle

### API Versioning
- [ ] Tag current Bridge/Docs APIs as `v1`
- [ ] Define deprecation policy (e.g., 90 days)
- [ ] Add header `Astra-Deprecated: <date>` for breaking changes

### Config Registry
- [ ] Store prod config snapshots (envs, limits, quota defaults) next to releases
- [ ] Gold during incidents

### Incident Templates
**Create two doc templates:**

**1. SEV-Page Template:**
- Timeline
- Impact (users affected, duration)
- Root cause
- Action items
- Owner assignments

**2. Retro Template:**
- What happened
- What worked well
- What to automate next time
- Follow-up items with dates

- [ ] Link templates from alert annotations
- [ ] Store in `docs/incident-templates/`

---

## ✅ Definition of Done (Ultra-Concrete)

Before declaring **"PRODUCTION LIVE"**, verify ALL:

- [ ] `validate_preconditions.ps1` PASS
- [ ] `smoke_tests_production.ps1` 10/10 PASS (pre & T+10)
- [ ] `cutover_status.sh` shows error <1%, P95 <1s, probes UP
- [ ] ServiceMonitors showing targets UP in Prometheus
- [ ] Alertmanager silence applied for deploy window
- [ ] Canary script flipped to green and auto-checks happy
- [ ] No critical alerts for 60 minutes post-flip
- [ ] One admin + one agent key rotated post-flip
- [ ] Blue scaled down to 0 (kept for 1h), then deleted

**If every box above is green: You're live and it's boring—which is exactly what you want.**

---

## 📊 PromQL Cheats (Drop-In for Quick Checks)

### Error Rate (%)
```promql
sum(rate(bridge_calls_total{status="error"}[5m])) /
clamp_min(sum(rate(bridge_calls_total[5m])), 1) * 100
```

### P95 Latency (s)
```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(bridge_call_duration_seconds_bucket[5m]))
)
```

### Docs Search/min
```promql
sum(rate(docs_search_total[1m])) * 60
```

### PV Usage (%)
```promql
100 * (1 - (node_filesystem_avail_bytes{mountpoint="/data"} /
           node_filesystem_size_bytes{mountpoint="/data"}))
```

---

## 🎯 Acceptance Criteria: "Production Stable"

**Meet ALL for any continuous 24-hour period within first week:**

- [ ] Error rate ≤ 0.5% (5m windows) for 24h
- [ ] P95 latency ≤ 0.5s (5m windows) for 24h
- [ ] No critical alerts sustained > 5 minutes
- [ ] No pod crashloops; restarts ≤ 1 and explained
- [ ] Backups & restore validated once in staging
- [ ] Audit logs show only expected scopes; no key misuse

**When done:**
- Tag release: `prod-v1.0.0-stable`
- Archive stabilization report
- Celebrate 🎉

---

## 🚀 Short, High-Impact Backlog (2-3 Week v1.1 Hardening)

Prioritized by risk reduction and product value:

### 1. Inbound Request Size Limits
- [ ] Add 25-50 MB limits on Docs + Ingress
- [ ] Friendly error pages for 413 responses
- **Impact:** Prevents abuse, protects disk

### 2. Per-Token RBAC for Docs
- [ ] Separate `docs:ingest` vs `docs:search` scopes
- [ ] Add per-token rate limits on ingest
- **Impact:** Finer-grained access control

### 3. Model Caches as Named Volumes
- [ ] Mount embeddings + llama caches
- [ ] Warmup at pod start
- **Impact:** Faster cold starts, no re-downloads

### 4. HTTP RAG Adapter in Bridge
- [ ] Retrieval → rerank → llama pipeline
- [ ] Behind same scopes/quota/audit
- **Impact:** Low code, big value—semantic memory + chat

### 5. Helm Chart
- [ ] Parameterized, repeatable installs
- [ ] Values for models, quotas, collections, ingress, TLS
- **Impact:** Multi-environment consistency

### 6. Workload Identity for Backups
- [ ] Object store access without static creds
- **Impact:** Security best practice

### 7. Feature Flags for Adapters
- [ ] Flip capabilities without redeploys
- **Impact:** Operational flexibility

**Each has clear acceptance tests:**
- Latency impact measured
- Error rate unchanged
- Smoke tests pass
- Runbook updated

---

## 🔐 Two "Oh-By-The-Way" Safety Tips

### 1. Shell Adapter
**Keep it out of prod**, or if absolutely necessary:
- Ensure no key with user-facing access has `tool:shell`
- Audit weekly for violations
- Log all shell calls to dedicated audit file

### 2. Egress NetworkPolicy
- Add "deny by default" egress for namespace
- Explicitly allow 3 destinations: LLM, Qdrant, monitoring
- You already created policies—ensure enforced pre-cutover

---

## ⚡ One-Line GO Path (You Can Literally Run This)

### Step 1: Preflight + Smoke
```powershell
.\scripts\validate_preconditions.ps1
.\scripts\smoke_tests_production.ps1 -BridgeUrl "https://bridge.example.com" -DocsUrl "https://docs.example.com"
```

### Step 2: Status Snapshot
```bash
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```

### Step 3: Canary Switch
```bash
NS=astra DEP_BLUE=bridge DEP_GREEN=bridge-green SVC=bridge \
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_canary.sh
```

### Step 4: Watch for 60 Minutes
```bash
watch -n 5 ./scripts/cutover_status.sh
```

### Step 5: If Thresholds Met
```bash
# Scale down blue and call it
kubectl -n astra scale deploy/bridge --replicas=0

# After 1h stable, delete blue
kubectl -n astra delete deploy/bridge
```

---

## 🔧 Tiny Nits to Double-Check (One Pass, 10 Minutes)

- [ ] Ingress TLS cipher suite and minimum TLS version (1.2+)
- [ ] `client_body_timeout` and `proxy_read_timeout` sensible for ingest
- [ ] `readinessProbe` failure thresholds not too strict during cold starts
- [ ] Log redaction covers API keys in headers and error stacks
- [ ] Prometheus scrape intervals consistent (15s fine)
- [ ] Histogram buckets aligned with SLOs (e.g., 0.05…5s)
- [ ] Timezone handling for daily quotas (UTC cutoff)
  - **Note:** Africa/Cairo is local; quotas reset on UTC to avoid surprises

---

## 🎯 What to Tackle Next (When Dust Settles)

### 1. RAG Middleware in Bridge
- Retrieval → (optional) rerank → llama
- Controlled by same RBAC/quotas
- Fully observable

### 2. Tenant Isolation
- Per-tenant collections/namespaces in Qdrant
- Per-tenant keys/scopes
- Opens door to multi-customer safely

### 3. UI
- React/Tailwind admin panel
- Keys, scopes, quotas, usage graphs
- Audit search (read-only first)

### 4. Admission Policy
- Enforce signed images (cosign)
- Non-root pods at cluster gate

### 5. Disaster Test
- Simulate loss of PV backing Qdrant
- Measure RTO
- Confirm restore steps match runbook

---

## 🎤 Short Version: Yes—You're There

The thing you built is not just deployable; **it's operable**.

**You've done the hard work—the rest is just pressing the big green button and watching the graphs do exactly what you designed them to do.**

---

## 📞 Next Steps

**If you want, we can draft:**
- RAG middleware adapter (retrieval + rerank + llama)
- Wired to RBAC/metrics/audit pattern
- Copy-paste code and tests

**Just say the word and we'll drop it in.**

---

**End of Final Hardening & Day-2 Ops Guide**

**Version:** 1.0.0  
**Status:** Production Hardening Complete ✅  
**Date:** October 16, 2025

**You're not just ready to deploy. You're ready to operate, scale, and sleep.** 🚀💤
