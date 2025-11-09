# ASTRA Production Cutover - Execution Guide

**Date:** _______________  
**Engineer:** _______________  
**Cutover Window:** _______________

---

## ⏰ Timeline

| Time | Phase | Duration |
|------|-------|----------|
| **T-30 min** | Pre-flight validation | 15 minutes |
| **T-15 min** | Stakeholder approval | 5 minutes |
| **T-10 min** | Final smoke tests | 5 minutes |
| **T-0** | Cutover execution | 10 minutes |
| **T+10 to T+120 min** | Monitoring & validation | 110 minutes |

---

## 📋 Phase 1: Pre-Flight Validation (T-30 min)

### Step 1.1: Run Precondition Validation

```powershell
cd "x:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# Run validation
.\scripts\validate_preconditions.ps1 -Namespace astra
```

**Expected Output:** `✅ VALIDATION PASSED - Ready for cutover`

**If FAILED:**
- Review specific failures
- Fix issues (see PRE_CUTOVER_CHECKLIST.md)
- Re-run validation
- **DO NOT PROCEED** until all checks pass

### Step 1.2: Run Smoke Tests

```powershell
# Set credentials
$env:ADMIN_KEY = "your-admin-key-here"
$env:AGENT_KEY = "your-agent-key-here"

# Run smoke tests against CURRENT production
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com" `
    -QdrantUrl "http://localhost:6333"
```

**Expected Output:** `✅ SMOKE TESTS PASSED - Safe to proceed`  
**All 10 tests must PASS**

**If ANY test fails:**
- Investigate current production issue
- Fix before proceeding
- **DO NOT DEPLOY** broken code over broken system

### Step 1.3: Capture Baseline Metrics

Open Grafana: https://grafana.example.com/d/astra

Record baseline values:

| Metric | Current Value | Threshold |
|--------|--------------|-----------|
| Error Rate | _____ % | < 0.5% |
| P95 Latency | _____ ms | < 500ms |
| Request Rate | _____ RPS | Expected load |
| CPU Usage | _____ % | < 60% |
| Memory Usage | _____ % | < 70% |

---

## 📝 Phase 2: Stakeholder Approval (T-15 min)

### Checklist for Approval

- [ ] All pre-flight checks passed
- [ ] All smoke tests passed
- [ ] Baseline metrics recorded
- [ ] Rollback plan reviewed and understood
- [ ] On-call SRE available
- [ ] Communication channels ready (#sre-incidents)

### Sign-Off

**Platform Lead:** _______________ Date/Time: _______________  
**SRE On-Call:** _______________ Date/Time: _______________  
**Decision:** [ ] GO / [ ] NO-GO

**If NO-GO:** Document reason and reschedule.

---

## 🚀 Phase 3: Cutover Execution (T-0)

### Choose Deployment Strategy

**Option A: Rolling Update** (Faster, for minor changes)  
**Option B: Blue/Green** (Safer, for major changes)

---

### **OPTION A: Rolling Update**

#### Step A.1: Build and Push Images

```bash
# Set version
export VERSION=prod-v1.0.0
export REGISTRY=ghcr.io/your-org

# Build bridge
docker build -t $REGISTRY/astra-bridge:$VERSION -f services/bridge/Dockerfile .
docker push $REGISTRY/astra-bridge:$VERSION

# Build docs
docker build -t $REGISTRY/astra-docs:$VERSION -f services/documents/Dockerfile .
docker push $REGISTRY/astra-docs:$VERSION
```

**Time: ~5 minutes**

#### Step A.2: Update Deployments

```bash
# Update bridge
kubectl -n astra set image deployment/bridge \
  bridge=$REGISTRY/astra-bridge:$VERSION \
  --record

# Update docs
kubectl -n astra set image deployment/docs \
  docs=$REGISTRY/astra-docs:$VERSION \
  --record
```

#### Step A.3: Watch Rollout

```bash
# Monitor rollout status
kubectl -n astra rollout status deployment/bridge
kubectl -n astra rollout status deployment/docs

# Watch pods (in separate terminal)
kubectl -n astra get pods -w -l app=bridge
```

**Expected:** `deployment "bridge" successfully rolled out`

#### Step A.4: Check Logs (New Pods)

```bash
# Get latest bridge pod
kubectl -n astra logs -l app=bridge --tail=50 -f

# Look for:
# - "[INFO] Starting ASTRA Bridge..."
# - "[INFO] Loaded X keys"
# - No errors or exceptions
```

**Time: ~10 minutes total**

---

### **OPTION B: Blue/Green Deployment**

#### Step B.1: Deploy Green

```bash
# Deploy green deployment
kubectl -n astra apply -f k8s/bridge-deployment-green.yaml

# Wait for ready
kubectl -n astra rollout status deployment/bridge-green
```

#### Step B.2: Test Green (Port-Forward)

```bash
# Port-forward to green
kubectl -n astra port-forward deployment/bridge-green 8889:8888 &

# Quick test
curl -sS http://127.0.0.1:8889/health | jq .
```

```powershell
# Full smoke test against green
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "http://127.0.0.1:8889" `
    -AgentKey "$env:AGENT_KEY"
```

**Expected:** All tests PASS on green

#### Step B.3: Switch Traffic to Green

```bash
# Update service selector
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge-green"}}}'

# Verify endpoints
kubectl -n astra get endpoints bridge
```

**Traffic now flows to green deployment**

#### Step B.4: Monitor Green

Watch Grafana for 10-15 minutes. If stable, proceed to Step B.5.

**If issues detected:** Rollback (see Phase 5)

#### Step B.5: Decommission Blue (Optional - Wait 1 Hour)

```bash
# Scale down blue (keep for quick rollback)
kubectl -n astra scale deployment bridge --replicas=0

# After 1 hour of stable green, delete blue
kubectl -n astra delete deployment bridge
```

**Time: ~20 minutes total (excluding monitoring)**

---

## 📊 Phase 4: Post-Cutover Monitoring (T+10 to T+120 min)

### Continuous Monitoring Checklist

**Every 10 minutes for first hour:**

- [ ] Check Grafana dashboard
- [ ] Run smoke tests
- [ ] Check error rate < 0.5%
- [ ] Check P95 latency < 500ms
- [ ] No crash loops in pods
- [ ] No critical alerts

### Key Commands

```bash
# Watch pods
kubectl -n astra get pods -w

# Stream logs
kubectl -n astra logs -l app=bridge -f --tail=100

# Check metrics
curl -sS https://bridge.example.com/metrics | grep bridge_errors_total
```

### Grafana Queries (Monitor Continuously)

```promql
# Error rate (must be < 0.5%)
100 * rate(bridge_errors_total[5m]) / rate(bridge_calls_total[5m])

# P95 latency (must be < 500ms)
histogram_quantile(0.95, rate(bridge_call_duration_seconds_bucket[5m]))

# Request rate
rate(bridge_calls_total[1m])
```

### T+30 Min: Run Full Smoke Tests

```powershell
.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com"
```

**Expected:** All 10 tests PASS

### T+60 Min: Check Audit Logs

```bash
# Download audit log
kubectl -n astra exec -it deploy/bridge -- cat /data/bridge_audit.log | tail -n 500 > audit.log

# Check for anomalies (unknown keys, high error rate)
cat audit.log | jq 'select(.level=="ERROR")' | wc -l
```

**Expected:** Error count < 5 in last hour

### T+120 Min: Decision Point

**If all metrics stable for 2 hours:** Declare cutover successful

**Criteria:**
- ✅ Error rate < 0.5%
- ✅ P95 latency < 500ms
- ✅ No crash loops
- ✅ Smoke tests passing
- ✅ No critical alerts

**Action:** Proceed to Phase 6 (Post-Cutover Tasks)

---

## ❌ Phase 5: Rollback Procedure (If Needed)

### When to Rollback

**Immediate rollback if:**
- Error rate > 2% for 5+ minutes
- P95 latency > 1s for 5+ minutes
- Pods crash-looping after 3 attempts
- Critical alerts firing
- Data corruption detected
- Qdrant unreachable

### Rollback: Rolling Update

```bash
# Announce in Slack #sre-incidents
# "🚨 Rolling back bridge deployment due to [reason]"

# Execute rollback
kubectl -n astra rollout undo deployment/bridge
kubectl -n astra rollout undo deployment/docs

# Verify rollback
kubectl -n astra rollout status deployment/bridge

# Check version
kubectl -n astra get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# Run smoke tests
.\scripts\smoke_tests_production.ps1
```

**Time: ~2 minutes**

### Rollback: Blue/Green

```bash
# Announce rollback

# Switch service back to blue
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'

# Scale up blue if scaled down
kubectl -n astra scale deployment bridge --replicas=2

# Delete green
kubectl -n astra delete deployment bridge-green

# Verify
kubectl -n astra get endpoints bridge
```

**Time: ~1 minute**

### Emergency Stop (Nuclear Option)

```bash
# Scale new deployment to 0
kubectl -n astra scale deployment bridge --replicas=0
kubectl -n astra scale deployment bridge-green --replicas=0

# Scale old deployment to stable count
kubectl -n astra scale deployment bridge --replicas=2
```

---

## ✅ Phase 6: Post-Cutover Tasks (T+2h to T+24h)

### Immediate (T+2h)

- [ ] **Rotate admin key**
  ```powershell
  .\scripts\rotate_bridge_key.ps1 -Namespace astra
  ```

- [ ] **Apply NetworkPolicy**
  ```bash
  kubectl -n astra apply -f k8s/bridge-egress-policy.yaml
  kubectl -n astra apply -f k8s/docs-egress-policy.yaml
  ```

- [ ] **Verify backup ran**
  ```bash
  kubectl -n astra logs -l job-name=backup-qdrant --tail=50
  ```

### T+4h

- [ ] Run smoke tests again
- [ ] Review audit logs for anomalies
- [ ] Check disk usage on PVs

### T+24h

- [ ] **Remove old keys from keys file** (after 24h grace period)
- [ ] **Load test** at expected QPS
  ```bash
  hey -n 1000 -c 50 -m POST \
    -H "x-api-key: $AGENT_KEY" \
    -D payload.json \
    https://bridge.example.com/call
  ```
- [ ] **Update runbook** with lessons learned

---

## 📞 Emergency Contacts

| Role | Contact | Method |
|------|---------|--------|
| **On-Call SRE** | _______________ | PagerDuty |
| **Platform Lead** | _______________ | Slack DM |
| **Engineering VP** | _______________ | Phone |

**Slack Channels:**
- **#sre-oncall** - Operational issues
- **#sre-incidents** - Active incidents
- **#astra-alerts** - Monitoring alerts

---

## 📝 Execution Log

| Time | Action | Result | Notes |
|------|--------|--------|-------|
| _____ | Pre-flight validation | ⬜ PASS / ⬜ FAIL | |
| _____ | Smoke tests (pre) | ⬜ PASS / ⬜ FAIL | |
| _____ | Stakeholder approval | ⬜ GO / ⬜ NO-GO | |
| _____ | Build & push images | ⬜ SUCCESS / ⬜ FAIL | |
| _____ | Deploy to K8s | ⬜ SUCCESS / ⬜ FAIL | |
| _____ | Rollout complete | ⬜ SUCCESS / ⬜ FAIL | |
| _____ | Smoke tests (post) | ⬜ PASS / ⬜ FAIL | |
| _____ | T+30 min check | ⬜ HEALTHY / ⬜ ISSUE | |
| _____ | T+60 min check | ⬜ HEALTHY / ⬜ ISSUE | |
| _____ | T+120 min check | ⬜ HEALTHY / ⬜ ISSUE | |
| _____ | Cutover declared | ⬜ SUCCESS / ⬜ ROLLBACK | |

---

**Print this guide and check off steps as you execute!**

