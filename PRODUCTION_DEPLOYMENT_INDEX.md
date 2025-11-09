# 📚 PRODUCTION DEPLOYMENT INDEX
**Complete Guide to ASTRA Production Deployment**

**Version:** 1.0.0  
**Date:** October 16, 2025  
**Status:** Production Ready ✅

---

## 🎯 START HERE

**New to this deployment?** Read these **3 documents** in order:

1. **`ARE_WE_THERE_YET.md`** ✅ YES - You're ready. 3-command launch.
2. **`60_SECOND_LAUNCH_CHECKLIST.md`** 📋 One-pager to tape to monitor.
3. **`GO_NOGO_DECISION_CARD.md`** 🚦 Comprehensive checklist with sign-offs.

**Ready to deploy RIGHT NOW?** Jump to [Quick Launch](#-quick-launch-3-commands) below.

---

## 🚀 Quick Launch (3 Commands)

### 1. Pre-Flight + Smoke Tests
```powershell
.\scripts\validate_preconditions.ps1
.\scripts\smoke_tests_production.ps1 -BridgeUrl "https://bridge.example.com" -DocsUrl "https://docs.example.com"
```
**Expected:** ✅ ALL PASS

### 2. Status Snapshot
```bash
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```
**Expected:** Error <1%, P95 <1s, No alerts

### 3. Canary Cutover
```bash
NS=astra DEP_BLUE=bridge DEP_GREEN=bridge-green SVC=bridge \
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_canary.sh
```
**Expected:** ✅ CUTOVER COMPLETE

**Monitor for 60 minutes:**
```bash
watch -n 5 ./scripts/cutover_status.sh
```

---

## 📖 Complete Documentation Map

### 🚀 Launch & Cutover Documents

| Document | Lines | Purpose | When to Use |
|----------|-------|---------|-------------|
| **ARE_WE_THERE_YET.md** | ~250 | Direct answer + 3-command launch | Before pressing button |
| **60_SECOND_LAUNCH_CHECKLIST.md** | ~120 | Ultra-compact one-pager | Tape to monitor |
| **GO_NOGO_DECISION_CARD.md** | ~400 | Comprehensive checklist + sign-offs | Final decision meeting |
| **PRODUCTION_DEPLOYMENT_COMPLETE.md** | 797 | Full deployment package | Complete reference |
| **CUTOVER_QUICKSTART.md** | ~200 | 10-minute execution workflow | Day of cutover |
| **CUTOVER_RUNBOOK.md** | ~500 | Detailed cutover procedures | Planning + execution |
| **CUTOVER_EXECUTION_GUIDE.md** | ~400 | Printable step-by-step | On-call guide |
| **CUTOVER_QUICK_REF.md** | ~150 | "When things go wrong" | Emergency reference |

### 🛡️ Hardening & Day-2 Ops

| Document | Lines | Purpose | When to Use |
|----------|-------|---------|-------------|
| **FINAL_HARDENING_AND_DAY2_OPS.md** | ~800 | Last-mile security + 7-day plan | Before & after cutover |
| **PRE_CUTOVER_CHECKLIST.md** | ~300 | 10 categories pre-flight | Days before cutover |
| **CUTOVER_FINAL_CHECKLIST.md** | ~500 | 100-item comprehensive | Final validation |

### 📊 Monitoring & SLOs

| Document | Lines | Purpose | When to Use |
|----------|-------|---------|-------------|
| **MONITORING_SETUP_GUIDE.md** | ~400 | 5-minute observability deploy | Before cutover |
| **SLO_REFERENCE.md** | ~300 | SLO math, burn rates, reviews | Ongoing operations |
| **CUTOVER_SILENCE_GUIDE.md** | ~200 | Alertmanager silence patterns | During deploys |

---

## 🛠️ Scripts Reference

### Validation & Testing

```powershell
# Pre-flight checks (10 categories)
.\scripts\validate_preconditions.ps1 -Namespace astra

# 10 automated end-to-end tests
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com"

# 4 automated failure scenarios
.\scripts\chaos_drills.ps1 -Namespace astra
```

### Deployment & Cutover

```bash
# Automated Blue/Green cutover with auto-rollback
NS=astra DEP_BLUE=bridge DEP_GREEN=bridge-green SVC=bridge \
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_canary.sh

# Live colored metrics dashboard
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```

### Security Operations

```bash
# Rotate keys (Bash)
./scripts/rotate_bridge_key.sh -Namespace astra

# Rotate keys (PowerShell)
.\scripts\rotate_bridge_key.ps1 -Namespace astra
```

---

## 🗂️ Kubernetes Manifests

### Monitoring Stack
```bash
kubectl apply -f k8s/servicemonitor-bridge-docs.yaml      # Prometheus scraping
kubectl apply -f k8s/prometheusrule-astrasafety.yaml      # 21 alerts
kubectl apply -f k8s/prometheusrule-recordings.yaml       # 37 recording rules
kubectl apply -f k8s/blackbox-exporter.yaml               # Synthetic checks
kubectl apply -f k8s/probe-astra.yaml                     # External probes
```

### Security Hardening
```bash
kubectl apply -f k8s/networkpolicy-deny-all.yaml          # Default deny
kubectl apply -f k8s/bridge-egress-policy.yaml            # Bridge allowlist
kubectl apply -f k8s/docs-egress-policy.yaml              # Docs allowlist
```

### Grafana Dashboard
- File: `k8s/grafana-dashboard-astra-ops.json`
- Import in Grafana UI: "+" → "Import" → Paste JSON

---

## ✅ Success Criteria

### Immediate (T+60 min)
- ✅ Error rate < 0.5% sustained
- ✅ P95 latency < 500ms sustained
- ✅ All smoke tests passing (10/10)
- ✅ Zero pod restarts
- ✅ Zero critical alerts
- ✅ Grafana dashboard all green

### Week 1 (Stabilization)
- ✅ Admin key rotated
- ✅ Qdrant snapshot + restore validated
- ✅ NetworkPolicies enforced
- ✅ Chaos drills pass (4 scenarios)
- ✅ Audit logs clean
- ✅ SLO burn rate within targets

### Production Stable (24h continuous)
- ✅ Error rate ≤ 0.5% for 24h
- ✅ P95 latency ≤ 0.5s for 24h
- ✅ No critical alerts >5 min
- ✅ No pod crashloops
- ✅ Backups validated
- ✅ No key misuse

---

## 🚨 Emergency Rollback

**One command:**
```bash
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}' && \
kubectl -n astra scale deploy/bridge --replicas=2
```

**Verify:**
```bash
kubectl -n astra get endpoints bridge
./scripts/cutover_status.sh
```

---

## 📊 What You're Deploying

### Core Services
- **Bridge Service** - Tool execution gateway (RBAC, quotas, audit)
- **Documents Service** - Semantic search (Qdrant + fallback)
- **Qdrant** - Vector database (COSINE, dim 384)
- **llama.cpp** - Local LLM serving

### Observability
- **21 Alerts** - De-flapped, with runbook URLs
- **13-Panel Dashboard** - "ASTRA - Ops Overview"
- **37 Recording Rules** - Efficient pre-aggregated metrics
- **Blackbox Probes** - External/internal synthetic checks

### Security
- **RBAC** - Per-key scopes (tool:\*, docs:\*, admin)
- **Rate Limiting** - RPM + daily quotas per key
- **NetworkPolicy** - Deny-all + minimal allow rules
- **TLS** - Termination at Ingress (cert-manager)
- **Audit Trail** - Append-only JSON logs

### Deployment
- **Blue/Green** - Zero-downtime with auto-rollback
- **HPA** - 2-10 replicas bridge, 2-8 docs
- **PVCs** - Persistent storage for Qdrant + Docs
- **ServiceMonitors** - Auto-discovery for Prometheus

---

## 🎯 SLO Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Availability | 99.5% | <99% for 5m |
| Error Rate | <0.5% | >1% for 5m |
| P95 Latency | <500ms | >1s for 5m |
| P99 Latency | <1s | >3s for 2m |

**Error Budget:** 216 minutes/month downtime

---

## 📞 Support

### Emergency
- **On-Call SRE:** PagerDuty
- **Slack:** `#sre-incidents`, `#astra-alerts`
- **Quick Ref:** `CUTOVER_QUICK_REF.md`

### Documentation
- **This Index:** `PRODUCTION_DEPLOYMENT_INDEX.md`
- **Quick Start:** `ARE_WE_THERE_YET.md`
- **Full Guide:** `PRODUCTION_DEPLOYMENT_COMPLETE.md`
- **Day-2 Ops:** `FINAL_HARDENING_AND_DAY2_OPS.md`

---

## 🎤 In One Sentence

**We built a secure, observable, resilient AI runtime—Bridge for tool execution, Docs for semantic memory, Qdrant for vectors, llama for inference—backed by RBAC, quotas, TLS, NetworkPolicies, CI/CD, blue/green, dashboards, alerts, fallbacks, chaos drills, and runbooks, so you can ship and sleep.**

---

## ✅ Bottom Line

**Are we there yet?** → **YES. GO.** 🚀

You have:
- ✅ Production-grade AI runtime
- ✅ Complete security hardening
- ✅ Full observability stack
- ✅ Automated deployment + rollback
- ✅ Comprehensive documentation
- ✅ 7-day stabilization plan

**You're not just ready to deploy. You're ready to operate, scale, and sleep.** 🚀💤

---

**End of Production Deployment Index**

**Version:** 1.0.0  
**Date:** October 16, 2025  
**Status:** PRODUCTION READY ✅
