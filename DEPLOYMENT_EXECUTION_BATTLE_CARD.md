# 🎯 DEPLOYMENT EXECUTION BATTLE CARD
**ASTRA Production Cutover - Step-by-Step Execution Guide**

**Date:** _____________  
**Operator:** _____________  
**Start Time:** _____________

---

## ⚡ PHASE 1: PRE-FLIGHT VALIDATION (5 Minutes)

### Step 1.1: Run Pre-Flight Validator
```powershell
cd "x:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
.\scripts\validate_preconditions.ps1 -Namespace astra
```

**Expected Output:** `✅ VALIDATION PASSED - Ready for cutover`

**Checks Validated:**
- [ ] Secrets exist (bridge-keys, docs-keys)
- [ ] PVCs bound (qdrant-data, docs-data)
- [ ] TLS configured (Ingress annotations)
- [ ] No `tool:shell` scopes in prod keys
- [ ] HPA configured (2-10 bridge, 2-8 docs)
- [ ] Disk space < 80%
- [ ] Backups recent (< 24h)

**Status:** ⬜ PASS / ⬜ FAIL  
**If FAIL:** STOP. Fix issues. Re-run.

**Completion Time:** _____________

---

### Step 1.2: Run Smoke Tests (ALL PASS Required)
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

**Tests:**
- [ ] Test 1: Bridge health ✅
- [ ] Test 2: Docs health ✅
- [ ] Test 3: Bridge metrics ✅
- [ ] Test 4: Docs metrics ✅
- [ ] Test 5: Tool call (llama) ✅
- [ ] Test 6: Document ingest ✅
- [ ] Test 7: Document search ✅
- [ ] Test 8: RBAC enforcement ✅
- [ ] Test 9: Qdrant collections ✅
- [ ] Test 10: Qdrant health ✅

**Status:** ⬜ 10/10 PASS / ⬜ FAIL  
**If ANY FAIL:** STOP. Investigate. Fix. Re-run.

**Completion Time:** _____________

---

## 🚀 PHASE 2: CANARY CUTOVER (2 Minutes)

### Step 2.1: Open Grafana Dashboard
**Action:** Open in browser (keep visible during cutover)
```
https://grafana.example.com/d/astra-ops
```

**Dashboard Name:** "ASTRA – Ops Overview"

**Key Panels to Watch:**
- Bridge Error Rate (%) - Target: < 1%
- Bridge P95 Latency (s) - Target: < 1s
- Qdrant Status - Target: UP=1
- Pod Restarts - Target: 0

**Status:** ⬜ Dashboard Open and Visible

---

### Step 2.2: Set Environment Variables
```bash
export NS=astra
export DEP_BLUE=bridge
export DEP_GREEN=bridge-green
export SVC=bridge
export PROM_URL="http://prometheus.monitoring:9090"
export ERROR_THRESH="0.01"  # 1% error rate threshold
```

**Status:** ⬜ Variables Set

---

### Step 2.3: Execute Automated Canary Cutover
```bash
./scripts/cutover_canary.sh
```

**What Happens:**
1. ✅ Verifies green deployment ready
2. ✅ Health checks green pods (port-forward)
3. ✅ Checks blue error rate & latency (Prometheus)
4. ✅ Switches Service selector: blue → green
5. ✅ Post-switch health check
6. ✅ 60-second canary monitoring (every 5s)
7. ✅ **Auto-rollback** if error rate >1% (3 consecutive checks)

**Expected Output:**
```
╔═══════════════════════════════════════════════════════╗
║   ✅ CUTOVER COMPLETE                                  ║
╚═══════════════════════════════════════════════════════╝

Traffic switched from bridge to bridge-green
```

**Actual Output:** _____________________________________________

**Status:** ⬜ SUCCESS / ⬜ ROLLED BACK (if rolled back, investigate)

**Cutover Time:** _____________

---

## 📊 PHASE 3: POST-CUTOVER MONITORING (60 Minutes)

### Step 3.1: Start Continuous Monitoring
```bash
# Watch metrics every 5 seconds
watch -n 5 ./scripts/cutover_status.sh
```

**Keep this running for 60 minutes. Watch for:**
- Error rate < 1% (ideally < 0.5%)
- P95 latency < 1s (ideally < 500ms)
- Qdrant Status: UP
- No pod restarts
- No active alerts

**Status:** ⬜ Monitoring Active

**Monitor Start Time:** _____________

---

### Step 3.2: T+10 Minutes - Re-Run Smoke Tests
```powershell
.\scripts\smoke_tests_production.ps1
```

**Expected:** 10/10 PASS

**Status:** ⬜ PASS / ⬜ FAIL

**If FAIL:** Investigate immediately. Consider rollback if critical.

**T+10 Time:** _____________

---

### Step 3.3: T+30 Minutes - Grafana Validation
**Check Grafana "ASTRA – Ops Overview" Dashboard:**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Bridge Error Rate (%) | < 1% | _____ | ⬜ OK / ⬜ WARN |
| Bridge P95 Latency (s) | < 1s | _____ | ⬜ OK / ⬜ WARN |
| Qdrant Status | UP=1 | _____ | ⬜ OK / ⬜ DOWN |
| Pod Restarts (1h) | 0 | _____ | ⬜ OK / ⬜ WARN |
| Active Alerts | 0 | _____ | ⬜ OK / ⬜ ALERTS |

**Overall Status:** ⬜ ALL GREEN / ⬜ ISSUES DETECTED

**T+30 Time:** _____________

---

### Step 3.4: T+60 Minutes - Final Validation (SUCCESS CRITERIA)

**All of these MUST be true for 60 continuous minutes:**

- [ ] Error rate < 0.5% sustained
- [ ] P95 latency < 500ms sustained
- [ ] Zero pod restarts
- [ ] Zero critical alerts firing
- [ ] Smoke tests passing (10/10)
- [ ] No errors in logs
- [ ] Grafana all green
- [ ] Qdrant UP

**Final Metrics at T+60:**

| Metric | Value | Status |
|--------|-------|--------|
| Bridge Error Rate (%) | _____ | ⬜ OK / ⬜ FAIL |
| Bridge P95 Latency (s) | _____ | ⬜ OK / ⬜ FAIL |
| Bridge Calls/sec | _____ | ⬜ OK |
| Docs Search/min | _____ | ⬜ OK |
| Qdrant Status | _____ | ⬜ UP / ⬜ DOWN |
| Pod Restarts | _____ | ⬜ 0 / ⬜ >0 |
| Active Alerts | _____ | ⬜ 0 / ⬜ >0 |

**Overall Status:** ⬜ SUCCESS ✅ / ⬜ ROLLBACK NEEDED ❌

**T+60 Time:** _____________

---

## 🧹 PHASE 4: POST-CUTOVER CLEANUP (10 Minutes)

**ONLY PROCEED IF PHASE 3 SUCCESS CRITERIA MET**

### Step 4.1: Keep Blue Warm for 60 Minutes (Already Done)
**Blue deployment is still running at replicas=2 (no action needed)**

**Status:** ⬜ Blue Still Running (for quick rollback if needed)

---

### Step 4.2: Scale Down Blue (After 60 Min Stability)
```bash
# Scale blue to 0 (keep deployment for emergency)
kubectl -n astra scale deploy/bridge --replicas=0

# Verify blue scaled down
kubectl -n astra get deploy bridge
```

**Expected Output:**
```
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
bridge   0/0     0            0           Xh
```

**Status:** ⬜ Blue Scaled to 0

**Scale Down Time:** _____________

---

### Step 4.3: Rotate Admin Key (Security Best Practice)
```bash
# Run key rotation script
./scripts/rotate_bridge_key.sh -Namespace astra

# Script will:
# 1. Generate new admin + agent keys
# 2. Backup old keys
# 3. Update Kubernetes secret
# 4. Trigger /admin/reload-keys endpoint
# 5. Output new credentials
```

**Expected Output:**
```
✅ Keys rotated successfully
New admin key: <redacted>
New agent key: <redacted>
Old keys backed up to: /backups/bridge-keys-<timestamp>.json
```

**New Keys (SAVE SECURELY):**
```
Admin Key: _____________________________________________
Agent Key: _____________________________________________
```

**Status:** ⬜ Keys Rotated Successfully

**Rotation Time:** _____________

---

### Step 4.4: Verify NetworkPolicies Enforced
```bash
# Verify NetworkPolicies are active
kubectl -n astra get networkpolicy

# Expected policies:
# - deny-all-egress (default deny)
# - bridge-egress-allow (Bridge → LLM, Qdrant, monitoring)
# - docs-egress-allow (Docs → Qdrant, monitoring)
```

**Expected Output:**
```
NAME                  POD-SELECTOR    AGE
deny-all-egress      <none>          Xd
bridge-egress-allow  app=bridge      Xd
docs-egress-allow    app=docs        Xd
```

**Status:** ⬜ NetworkPolicies Active and Enforced

**Verification Time:** _____________

---

### Step 4.5: Final Smoke Test (Post-Cleanup)
```powershell
# Re-run smoke tests with NEW keys
$env:ADMIN_KEY = "<new-admin-key>"
$env:AGENT_KEY = "<new-agent-key>"

.\scripts\smoke_tests_production.ps1
```

**Expected:** 10/10 PASS

**Status:** ⬜ PASS / ⬜ FAIL

**If FAIL:** Keys may not have reloaded. Check logs.

**Completion Time:** _____________

---

## 🚨 EMERGENCY ROLLBACK PROCEDURE

**USE ONLY IF:**
- Error rate > 2% for 5+ minutes
- P95 latency > 3s for 5+ minutes
- Pods crash-looping
- Critical alerts firing
- Data corruption detected

### Immediate Rollback (One Command)
```bash
# Switch service back to blue
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'

# Scale up blue if scaled down
kubectl -n astra scale deploy/bridge --replicas=2
```

### Verify Rollback
```bash
# Check endpoints
kubectl -n astra get endpoints bridge

# Verify metrics recovering
./scripts/cutover_status.sh
```

**Expected:** Traffic back on blue, metrics stabilizing

**Rollback Executed:** ⬜ YES / ⬜ NO  
**Rollback Time:** _____________  
**Rollback Reason:** _____________________________________________

---

## ✅ DEPLOYMENT COMPLETION CHECKLIST

### Final Sign-Off

**All phases completed successfully:**
- [ ] Phase 1: Pre-flight + smoke tests (ALL PASS)
- [ ] Phase 2: Canary cutover (SUCCESS)
- [ ] Phase 3: 60-minute monitoring (SUCCESS)
- [ ] Phase 4: Cleanup (Blue scaled down, keys rotated, NetworkPolicies enforced)

**Production is now LIVE on GREEN deployment:**
- [ ] Error rate < 0.5% sustained
- [ ] P95 latency < 500ms sustained
- [ ] Zero critical alerts
- [ ] Zero pod restarts
- [ ] Smoke tests passing with new keys
- [ ] NetworkPolicies enforced
- [ ] Admin key rotated

**Status:** ⬜ PRODUCTION LIVE ✅ / ⬜ ROLLBACK EXECUTED ❌

---

## 📝 POST-DEPLOYMENT NOTES

**Deployment Duration:** _____________ (from start to completion)

**Issues Encountered:**
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

**Resolutions:**
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

**Follow-Up Actions:**
1. _____________________________________________
2. _____________________________________________
3. _____________________________________________

---

## 📊 PRODUCTION METRICS SNAPSHOT (For Records)

**At T+60 (Final):**
- Bridge Error Rate: _______%
- Bridge P95 Latency: _______s
- Bridge Calls/sec: _______
- Docs Search/min: _______
- Qdrant Status: _______
- Pod Restarts: _______
- Active Alerts: _______

---

## 🎯 NEXT STEPS (Week 1 Stabilization)

**Follow `FINAL_HARDENING_AND_DAY2_OPS.md` for 7-day plan:**

- [ ] **Day 1:** Test Qdrant snapshot + restore in staging
- [ ] **Day 2:** Calibrate rate limits/quotas
- [ ] **Day 3:** Run chaos drills (low-traffic window)
- [ ] **Day 4:** Backup validation (off-cluster)
- [ ] **Day 5:** SLO burn review (5-day metrics)
- [ ] **Day 6:** Security touch-ups (TLS expiry, no tool:shell)
- [ ] **Day 7:** Write stabilization report, tag release `prod-v1.0.0-stable`

---

## 📞 EMERGENCY CONTACTS

**On-Call SRE:** PagerDuty escalation  
**Engineering Lead:** Slack DM  
**Slack Channels:** `#sre-oncall`, `#sre-incidents`, `#astra-alerts`

**Runbooks:**
- **Quick Ref:** `CUTOVER_QUICK_REF.md`
- **Detailed:** `CUTOVER_RUNBOOK.md`
- **Day-2 Ops:** `FINAL_HARDENING_AND_DAY2_OPS.md`

---

## 🎤 DEPLOYMENT SIGN-OFF

**Deployment Lead:** _______________________ Date: _______  
**On-Call SRE:** _______________________ Date: _______  
**Engineering Lead:** _______________________ Date: _______

**Status:** ⬜ PRODUCTION LIVE ✅ / ⬜ ROLLBACK EXECUTED ❌

---

**End of Deployment Execution Battle Card**

**You've got this. Press the button. Watch the graphs. Scale down blue. Rotate keys. Done.** 🚀

**Version:** 1.0.0  
**Date:** October 16, 2025  
**Status:** Ready for Execution ✅
