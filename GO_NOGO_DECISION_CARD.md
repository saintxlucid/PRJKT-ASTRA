# 🚦 GO/NO-GO DECISION CARD
## ASTRA Production Cutover - Final Readiness Check

**Date:** October 16, 2025  
**System:** PROJECT ASTRA 1.0 - Production Deployment  
**Decision Maker:** ___________________  
**Time:** ___________

---

## ✅ READINESS VERIFICATION (Complete ALL Before GO)

### 1️⃣ Pre-Flight Validation (MUST BE ALL PASS)

```powershell
.\scripts\validate_preconditions.ps1 -Namespace astra
```

**Expected Output:** `✅ VALIDATION PASSED - Ready for cutover`

- [ ] **Secrets exist** (bridge-keys, docs-keys)
- [ ] **PVCs bound** (qdrant-data, docs-data)
- [ ] **TLS configured** (Ingress with cert-manager annotations)
- [ ] **No dangerous scopes** (no `tool:shell` in production keys)
- [ ] **HPA configured** (2-10 replicas bridge, 2-8 docs)
- [ ] **Disk space OK** (PV usage < 80%)
- [ ] **Backups recent** (Qdrant snapshot < 24h old)

**Status:** ⬜ PASS / ⬜ FAIL  
**If FAIL:** Do not proceed. Fix issues first.

---

### 2️⃣ Smoke Tests (MUST BE ALL 10/10 PASS)

```powershell
# Set API keys
$env:ADMIN_KEY = "your-admin-key-here"
$env:AGENT_KEY = "your-agent-key-here"

# Run smoke tests
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com" `
    -QdrantUrl "http://qdrant.astra:6333"
```

**Expected Output:** `✅ SMOKE TESTS PASSED (10/10)`

- [ ] Test 1: Bridge health endpoint responds
- [ ] Test 2: Docs health endpoint responds
- [ ] Test 3: Bridge metrics endpoint accessible
- [ ] Test 4: Docs metrics endpoint accessible
- [ ] Test 5: Tool call (llama) succeeds
- [ ] Test 6: Document ingest succeeds
- [ ] Test 7: Document search returns results
- [ ] Test 8: RBAC enforcement (unauthorized request blocked)
- [ ] Test 9: Qdrant collections exist
- [ ] Test 10: Qdrant health check passes

**Status:** ⬜ 10/10 PASS / ⬜ FAIL  
**If FAIL:** Investigate and fix. Do not proceed with broken production.

---

### 3️⃣ Live Status Snapshot (Verify GO Criteria)

```bash
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh
```

**GO Criteria (ALL must be true):**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Bridge Error Rate (%) | < 1 | _____ | ⬜ GO / ⬜ NO-GO |
| Bridge P95 Latency (s) | < 1 | _____ | ⬜ GO / ⬜ NO-GO |
| Bridge Calls/sec | > 0* | _____ | ⬜ GO / ⬜ NO-GO |
| Qdrant Status | UP | _____ | ⬜ GO / ⬜ NO-GO |
| Active Critical Alerts | 0 | _____ | ⬜ GO / ⬜ NO-GO |
| Pod Restarts (1h) | 0 | _____ | ⬜ GO / ⬜ NO-GO |

*\*If production traffic exists; can be 0 for new deployment*

**Grafana Dashboard Check:**
- [ ] Navigate to `https://grafana.example.com/d/astra-ops`
- [ ] All probes show **UP** (green)
- [ ] All panels showing data (not "No Data")
- [ ] No red alerts visible

**Status:** ⬜ ALL GO / ⬜ NO-GO  
**If NO-GO:** Investigate anomalies before cutover.

---

### 4️⃣ Monitoring Stack Deployed

```bash
# Verify ServiceMonitors applied
kubectl get servicemonitor -n monitoring | grep astra

# Expected output:
# astra-bridge-sm   ...
# astra-docs-sm     ...
# astra-qdrant-sm   ...
```

- [ ] ServiceMonitors applied (`k8s/servicemonitor-bridge-docs.yaml`)
- [ ] PrometheusRule deployed (`k8s/prometheusrule-astrasafety.yaml`)
- [ ] Recording rules deployed (`k8s/prometheusrule-recordings.yaml`)
- [ ] Blackbox Exporter running (`k8s/blackbox-exporter.yaml`)
- [ ] Probes configured (`k8s/probe-astra.yaml`)
- [ ] Grafana dashboard imported (`k8s/grafana-dashboard-astra-ops.json`)
- [ ] Prometheus targets "UP" (check `/targets` page)

**Status:** ⬜ ALL DEPLOYED / ⬜ MISSING COMPONENTS

---

### 5️⃣ Security Hardening Applied

- [ ] NetworkPolicy deny-all (`k8s/networkpolicy-deny-all.yaml`)
- [ ] Bridge egress policy (`k8s/bridge-egress-policy.yaml`)
- [ ] Docs egress policy (`k8s/docs-egress-policy.yaml`)
- [ ] TLS termination at Ingress
- [ ] Secrets mounted (not env vars)
- [ ] No `tool:shell` scope in production keys
- [ ] Key rotation scripts tested (`scripts/rotate_bridge_key.sh`)

**Status:** ⬜ HARDENED / ⬜ GAPS EXIST

---

### 6️⃣ Operational Readiness

- [ ] On-call engineer identified: ___________________
- [ ] Grafana dashboard open in browser
- [ ] Slack channel `#astra-alerts` monitored
- [ ] PagerDuty integration active
- [ ] Runbooks accessible (`CUTOVER_RUNBOOK.md`, `CUTOVER_QUICK_REF.md`)
- [ ] Rollback procedure understood (see Emergency Rollback below)
- [ ] Alertmanager silence configured (optional, 45 min window)

**Status:** ⬜ READY / ⬜ NOT READY

---

### 7️⃣ Automation Scripts Verified

```bash
# Make scripts executable
chmod +x scripts/cutover_canary.sh
chmod +x scripts/cutover_status.sh

# Test status script returns data
PROM_URL="http://prometheus.monitoring:9090" ./scripts/cutover_status.sh

# Expected: Numeric values (not "N/A" or errors)
```

- [ ] `cutover_canary.sh` executable and tested in staging
- [ ] `cutover_status.sh` returns valid metrics
- [ ] Environment variables set (`NS`, `DEP_BLUE`, `DEP_GREEN`, `SVC`, `PROM_URL`)

**Status:** ⬜ VERIFIED / ⬜ NOT TESTED

---

## 🚀 CUTOVER EXECUTION (If ALL Above = PASS)

### Step 1: Set Environment Variables

```bash
export NS=astra
export DEP_BLUE=bridge
export DEP_GREEN=bridge-green
export SVC=bridge
export PROM_URL="http://prometheus.monitoring:9090"
export ERROR_THRESH="0.01"  # 1% error rate threshold
```

### Step 2: Execute Automated Canary Cutover

```bash
./scripts/cutover_canary.sh
```

**What happens:**
1. ✅ Verifies green deployment ready
2. ✅ Health checks green pod via port-forward
3. ✅ Checks blue error rate and latency (Prometheus)
4. ✅ Switches Service selector: `blue` → `green`
5. ✅ Post-switch health check via Service ClusterIP
6. ✅ 60-second canary monitoring (error rate every 5s)
7. ✅ **Auto-rollback** if error rate >1% for 3 consecutive checks

**Expected Output:**
```
╔═══════════════════════════════════════════════════════╗
║   ✅ CUTOVER COMPLETE                                  ║
╚═══════════════════════════════════════════════════════╝

Traffic switched from bridge to bridge-green
```

**Actual Output:** ___________________________________________

**Cutover Time:** ___________

---

### Step 3: Post-Cutover Monitoring (60 Minutes)

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
.\scripts\smoke_tests_production.ps1
# Expected: 10/10 tests PASS
```
- [ ] Smoke tests PASS at T+10

**T+30 Minutes:**
- [ ] Grafana dashboard stable (no red panels)
- [ ] Prometheus alerts silent
- [ ] Logs clean (no errors)

**T+60 Minutes (Success Criteria):**
- [ ] Error rate < 0.5% for 60 minutes
- [ ] P95 latency < 500ms for 60 minutes
- [ ] Zero pod restarts
- [ ] Zero alerts firing
- [ ] Smoke tests passing
- [ ] No errors in logs

**Final Status:** ⬜ SUCCESS / ⬜ ROLLBACK NEEDED

---

## 🚨 EMERGENCY ROLLBACK PROCEDURE

**If ANY of these occur, execute immediate rollback:**
- ❌ Error rate > 2% for 5+ minutes
- ❌ P95 latency > 3s for 5+ minutes
- ❌ Pods crash-looping
- ❌ Critical alerts firing (BridgeDown, QdrantDown, PVUsageCritical)
- ❌ Data corruption detected

**Rollback Command (One-Liner):**
```bash
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}' && \
kubectl -n astra scale deploy/bridge --replicas=2
```

**Verify Rollback:**
```bash
kubectl -n astra get endpoints bridge
./scripts/cutover_status.sh
```

**Expected:** Traffic back on blue deployment, metrics stable.

**Rollback Time:** ___________ (if executed)  
**Rollback Reason:** ___________________________________________

---

## ✅ GO/NO-GO DECISION

### Pre-Cutover Checklist Summary

| Category | Status |
|----------|--------|
| 1. Pre-Flight Validation | ⬜ PASS / ⬜ FAIL |
| 2. Smoke Tests (10/10) | ⬜ PASS / ⬜ FAIL |
| 3. Live Status Snapshot | ⬜ GO / ⬜ NO-GO |
| 4. Monitoring Stack | ⬜ DEPLOYED / ⬜ MISSING |
| 5. Security Hardening | ⬜ HARDENED / ⬜ GAPS |
| 6. Operational Readiness | ⬜ READY / ⬜ NOT READY |
| 7. Automation Scripts | ⬜ VERIFIED / ⬜ NOT TESTED |

### Final Decision

**ALL checks above must be PASS/GO/DEPLOYED/READY for GO decision.**

- [ ] **GO** - All checks passed. Proceed with cutover.
- [ ] **NO-GO** - One or more checks failed. Fix issues and re-evaluate.

**Decision:** ⬜ GO / ⬜ NO-GO  
**Decision Maker Signature:** ___________________  
**Date/Time:** ___________

**If GO, proceed to "CUTOVER EXECUTION" above.**  
**If NO-GO, document blockers below and schedule new decision time.**

---

## 📝 NO-GO BLOCKERS (If applicable)

**Issue 1:** ___________________________________________  
**Mitigation:** ___________________________________________  
**ETA Fix:** ___________

**Issue 2:** ___________________________________________  
**Mitigation:** ___________________________________________  
**ETA Fix:** ___________

**Issue 3:** ___________________________________________  
**Mitigation:** ___________________________________________  
**ETA Fix:** ___________

**Re-Evaluation Time:** ___________

---

## 📊 POST-CUTOVER SUCCESS VALIDATION

**If cutover completed, verify these within 60 minutes:**

- [ ] Error rate < 0.5% sustained
- [ ] P95 latency < 500ms sustained
- [ ] All smoke tests passing
- [ ] Zero pod restarts
- [ ] Zero critical alerts
- [ ] Grafana dashboard green
- [ ] Audit logs recording calls
- [ ] Qdrant metrics stable
- [ ] No customer impact reports

**Post-Cutover Sign-Off:** ___________________  
**Date/Time:** ___________

---

## 🎯 SUCCESS CONFIRMATION

**If ALL post-cutover checks pass, you have successfully deployed:**

✅ **Production-grade AI runtime**  
✅ **Secure Bridge service with RBAC and quotas**  
✅ **Semantic Docs service with fallback**  
✅ **Vector storage (Qdrant) and LLM serving (llama.cpp)**  
✅ **Complete monitoring and alerting**  
✅ **Blue/Green deployment capability**  
✅ **Automated validation and testing**  
✅ **Comprehensive documentation and runbooks**  
✅ **Security hardening (TLS, NetworkPolicy, secrets)**  
✅ **SLO tracking and error budgets**  
✅ **Operational excellence (chaos drills, key rotation)**

---

## 📞 EMERGENCY CONTACTS

**On-Call SRE:** PagerDuty escalation  
**Engineering Lead:** Slack DM  
**Slack Channels:** `#sre-oncall`, `#sre-incidents`, `#astra-alerts`  
**Runbooks:** `CUTOVER_RUNBOOK.md`, `CUTOVER_QUICK_REF.md`  
**Documentation:** `PRODUCTION_DEPLOYMENT_COMPLETE.md`

---

**ARE WE THERE YET?**

**If this card shows ALL GREEN:** 🟢 **YES - GO FOR LAUNCH** 🚀

**If ANY RED:** 🔴 **NO-GO - Fix blockers first**

---

**End of GO/NO-GO Decision Card**

**Remember:** This is not a race. Take the time to verify each check. A 10-minute delay now prevents a 3-hour outage later.

**When ready:** Execute `./scripts/cutover_canary.sh` and keep Grafana open. You've got this. 💪
