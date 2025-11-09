# 🚀 ASTRA CORE - PRODUCTION CANARY DEPLOYMENT CHECKLIST

**Date**: 2025-11-01  
**Operator**: [Your Name]  
**Environment**: Production (astra-production namespace)  
**Strategy**: Flagger Canary (10% → 100% over 60 minutes)

---

## Pre-Deployment: Evidence Collection

### Step 1: Execute Pre-Canary Automation
```powershell
# Run evidence collection (30-45 minutes)
.\scripts\pre_canary.ps1

# Output directory: audit/PRE_CANARY_{timestamp}/
```

**Expected Artifacts** (12 files):
- [ ] `git_snapshot.txt` - Current commit hash and branch
- [ ] `pip_audit.json` - Dependency vulnerability scan
- [ ] `bandit_report.json` - Python security scan
- [ ] `safety_report.json` - Known vulnerability check
- [ ] `pytest_coverage.txt` - Test coverage report
- [ ] `coverage_html/index.html` - HTML coverage report
- [ ] `backup_dryrun.log` - Backup validation
- [ ] `restore_dryrun.log` - Restore validation
- [ ] `file_hashes.txt` - SHA256 file integrity
- [ ] `sbom.json` - Software Bill of Materials
- [ ] `summary.txt` - Consolidated report
- [ ] `EVIDENCE_COMPLETE.flag` - Completion marker

---

### Step 2: Validate GO/NO-GO Decision
```powershell
# Run validator (1 minute)
.\scripts\assert_go_nogo.ps1 -AuditDir "audit\PRE_CANARY_{timestamp}"

# Exit codes:
#   0 = GO (all gates passed)
#   1 = NO-GO (gate failed)
#   2 = ERROR (validation failed)
```

**Gate Validation**:
- [ ] **Security Gate**: No HIGH/CRITICAL vulnerabilities
  - pip-audit: 0 HIGH/CRITICAL
  - bandit: 0 HIGH/CRITICAL
  - safety: 0 HIGH/CRITICAL
- [ ] **Coverage Gate**: Test coverage ≥ 70%
  - pytest --cov: Coverage percentage
- [ ] **Backup Gate**: Backup/Restore validated
  - Dry-run: SUCCESS

**Decision**: ⬜ GO / ⬜ NO-GO

**If NO-GO**: Stop here, address gate failures, re-run Steps 1-2.

---

## Deployment Phase 1: Infrastructure Preparation

### Step 3: Verify Kubernetes Cluster Health
```bash
# Check cluster status
kubectl cluster-info
kubectl get nodes

# Verify monitoring stack
kubectl get pods -n monitoring
kubectl get prometheus -n monitoring
kubectl get servicemonitor -n monitoring
```

**Health Checks**:
- [ ] Cluster accessible and healthy
- [ ] All nodes Ready (0 NotReady)
- [ ] Prometheus operational
- [ ] ServiceMonitors synced
- [ ] Flagger controller running

---

### Step 4: Create Production Namespace
```bash
# Create namespace (if not exists)
kubectl create namespace astra-production --dry-run=client -o yaml | kubectl apply -f -

# Verify
kubectl get namespace astra-production
```

- [ ] Namespace `astra-production` exists

---

### Step 5: Configure External Secrets
```bash
# Apply External Secrets Operator configuration
kubectl apply -f k8s/policies/external-secrets.yaml

# Wait for secrets to sync (max 60s)
kubectl wait --for=condition=SecretSynced externalsecret/astra-secrets \
  -n astra-production --timeout=60s

# Verify secrets created
kubectl get secret astra-secrets -n astra-production
kubectl describe externalsecret astra-secrets -n astra-production
```

**Secrets Validation**:
- [ ] ExternalSecret `astra-secrets` created
- [ ] ClusterSecretStore `aws-secrets-manager` configured
- [ ] Secret `astra-secrets` synced (5 keys present)
- [ ] Refresh interval: 1 hour

**Required Keys** (verify with `kubectl get secret astra-secrets -o json | jq .data | jq keys`):
- [ ] `ASTRA_ADMIN_KEY`
- [ ] `ASTRA_API_KEYS`
- [ ] `OPENAI_API_KEY`
- [ ] `DATABASE_URL`
- [ ] `REDIS_URL`

---

### Step 6: Apply Security Policies
```bash
# Apply comprehensive security hardening
kubectl apply -f k8s/policies/admin-protect.yaml

# Verify all resources created
kubectl get authorizationpolicy astra-admin-protect -n astra-production
kubectl get poddisruptionbudget astra-core-pdb -n astra-production
kubectl get networkpolicy -n astra-production
kubectl get serviceaccount astra-core-sa -n astra-production
kubectl get role astra-core-role -n astra-production
kubectl get rolebinding astra-core-rolebinding -n astra-production
```

**Security Resources** (7 total):
- [ ] Istio AuthorizationPolicy `astra-admin-protect` (ops CIDR restriction)
- [ ] PodDisruptionBudget `astra-core-pdb` (minAvailable=2)
- [ ] NetworkPolicy `astra-core-ingress` (Prometheus + Istio)
- [ ] NetworkPolicy `astra-core-egress` (DNS, Qdrant, Redis, PostgreSQL)
- [ ] ServiceAccount `astra-core-sa`
- [ ] Role `astra-core-role` (read-only)
- [ ] RoleBinding `astra-core-rolebinding`

---

### Step 7: Deploy Canary Metric Templates
```bash
# Apply Flagger MetricTemplates for reusable queries
kubectl apply -f k8s/canary/metric-templates.yaml

# Verify templates created (10 total)
kubectl get metrictemplate -n astra-production
```

**Metric Templates** (10 total):
- [ ] `p95-latency`
- [ ] `p99-latency`
- [ ] `error-rate-percentage`
- [ ] `success-rate-percentage`
- [ ] `vector-query-success-rate`
- [ ] `vector-query-latency`
- [ ] `llm-token-throughput`
- [ ] `llm-error-rate`
- [ ] `memory-usage-percentage`
- [ ] `cpu-usage-percentage`

---

## Deployment Phase 2: Canary Deployment

### Step 8: Deploy Canary Configuration
```bash
# Apply Canary, Deployment, Service, HPA
kubectl apply -f k8s/canary/canary-deployment.yaml

# Verify resources created
kubectl get canary astra-core -n astra-production
kubectl get deployment astra-core -n astra-production
kubectl get service astra-core -n astra-production
kubectl get hpa astra-core -n astra-production
```

**Resources Created**:
- [ ] Canary `astra-core` (Flagger managed)
- [ ] Deployment `astra-core` (base)
- [ ] Service `astra-core` (ClusterIP)
- [ ] HorizontalPodAutoscaler `astra-core` (3-10 replicas)

---

### Step 9: Initial Canary Status Check
```bash
# Check canary status (should be "Initialized")
kubectl describe canary astra-core -n astra-production

# Check pods (should be 3 primary replicas)
kubectl get pods -n astra-production -l app=astra-core
```

**Expected State**:
- [ ] Canary Status: `Initialized`
- [ ] Primary replicas: 3/3 Ready
- [ ] Canary replicas: 0 (pre-rollout)

---

### Step 10: Trigger Canary Rollout
```bash
# Update deployment image to trigger canary
kubectl set image deployment/astra-core \
  astra-core=astra-core:v2.0.0 \
  -n astra-production

# Alternative: Update YAML and re-apply
# Edit k8s/canary/canary-deployment.yaml (change image tag)
# kubectl apply -f k8s/canary/canary-deployment.yaml
```

**Rollout Trigger**:
- [ ] Image updated to new version
- [ ] Canary Status: `Progressing`

---

## Deployment Phase 3: Canary Monitoring

### Step 11: Monitor Canary Progression
```bash
# Watch canary status (auto-updates every 2s)
watch -n 2 kubectl get canary astra-core -n astra-production

# Alternative: Continuous logs
kubectl logs -f -n astra-production deploy/flagger
```

**Traffic Progression** (60 minutes total):
- [ ] 0% → 10% (t=0m, interval 1m)
- [ ] 10% → 20% (t=1m)
- [ ] 20% → 30% (t=2m)
- [ ] 30% → 40% (t=3m)
- [ ] 40% → 50% (t=4m)
- [ ] 50% → 100% (t=5m, promotion)

**At Each Step**:
- [ ] Check metrics pass: `kubectl describe canary astra-core -n astra-production`
- [ ] Verify pod health: `kubectl get pods -n astra-production -l app=astra-core`
- [ ] Check logs: `kubectl logs -n astra-production -l app=astra-core,version=canary --tail=50`

---

### Step 12: Validate Canary Metrics
```bash
# Query Prometheus for canary metrics
# (Replace with your Prometheus endpoint)

# Success rate (must be > 99%)
curl -s "http://prometheus.monitoring:9090/api/v1/query?query=..." | jq .

# P95 latency (must be < 2500ms)
curl -s "http://prometheus.monitoring:9090/api/v1/query?query=..." | jq .

# Error rate (must be < 1%)
curl -s "http://prometheus.monitoring:9090/api/v1/query?query=..." | jq .

# Vector query success (must be > 98%)
curl -s "http://prometheus.monitoring:9090/api/v1/query?query=..." | jq .
```

**Metric Gates** (4 total):
- [ ] **request-success-rate**: > 99%
- [ ] **request-duration**: P95 < 2500ms
- [ ] **error-rate**: < 1%
- [ ] **vector-query-success**: > 98%

**All gates must pass for 5 consecutive intervals (5 minutes) before progression.**

---

### Step 13: Run Acceptance Tests
```bash
# Canary endpoint (internal)
CANARY_URL="http://astra-core-canary.astra-production:8001"

# Health checks
curl -f $CANARY_URL/live || echo "FAIL: liveness"
curl -f $CANARY_URL/ready || echo "FAIL: readiness"
curl -f $CANARY_URL/health/full || echo "FAIL: full health"

# Functional test (requires API key)
curl -X POST $CANARY_URL/answer \
  -H "Content-Type: application/json" \
  -H "x-astra-key: test-key-id.your-secret-here" \
  -d '{"query":"What is ASTRA?","max_tokens":100}' \
  | jq .
```

**Acceptance Tests**:
- [ ] Liveness probe: 200 OK
- [ ] Readiness probe: 200 OK
- [ ] Full health: 200 OK
- [ ] Q&A endpoint: 200 OK with valid response

---

## Deployment Phase 4: Promotion or Rollback

### Step 14: Monitor for Rollback Triggers
**Automatic Rollback** (Flagger-triggered):
- Error rate > 1% for 5 consecutive minutes
- P95 latency > 5000ms for 5 consecutive minutes
- Any metric gate failure

**Manual Rollback** (operator decision):
- Logs show unexpected errors
- Customer reports issues
- Business decision

**Rollback Command**:
```bash
# Manual rollback (reverts to previous version)
kubectl rollout undo deployment/astra-core -n astra-production

# Verify rollback
kubectl rollout status deployment/astra-core -n astra-production
```

- [ ] **No rollback triggers detected**

---

### Step 15: Canary Promotion (Automatic)
**Expected**: After 5 successful intervals at 50% traffic, Flagger promotes canary to primary.

```bash
# Verify promotion
kubectl get canary astra-core -n astra-production
# Status should be "Succeeded"

# Verify all pods running new version
kubectl get pods -n astra-production -l app=astra-core \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'
```

**Promotion Validation**:
- [ ] Canary Status: `Succeeded`
- [ ] All pods running new image version
- [ ] Primary replicas: 3/3 Ready (new version)
- [ ] Canary replicas: 0 (scaled down)

---

## Post-Deployment: Validation

### Step 16: Verify Production Endpoints
```bash
# External production URL (replace with your ingress)
PROD_URL="https://astra.example.com"

# Health checks
curl -f $PROD_URL/live
curl -f $PROD_URL/ready
curl -f $PROD_URL/health/full

# Metrics endpoint
curl -f $PROD_URL/metrics | head -20
```

**Production Validation**:
- [ ] Liveness: 200 OK
- [ ] Readiness: 200 OK
- [ ] Full health: 200 OK
- [ ] Metrics: 200 OK (OpenMetrics format)

---

### Step 17: Verify Security Policies
```bash
# Test admin endpoint protection (should be 403 from non-ops IP)
curl -X POST $PROD_URL/drain \
  -H "x-astra-admin: test-key-id.fake-secret"
# Expected: 403 Forbidden (AuthorizationPolicy blocks)

# Test with valid admin key from ops network
# (Must be executed from ops CIDR: 10.0.0.0/8 or 192.168.0.0/16)
curl -X POST $PROD_URL/drain \
  -H "x-astra-admin: $VALID_ADMIN_KEY"
# Expected: 503 (drain initiated) or 403 (wrong key)
```

**Security Validation**:
- [ ] Admin endpoints protected by Istio AuthorizationPolicy
- [ ] Non-ops IPs blocked with 403
- [ ] API key authentication enforced on `/answer` endpoints
- [ ] NetworkPolicy blocks unauthorized ingress/egress

---

### Step 18: Monitor Prometheus Alerts
```bash
# Check for any firing alerts
kubectl get prometheusrule -n monitoring
kubectl logs -n monitoring -l app=prometheus --tail=100 | grep FIRING
```

**Alert Status**:
- [ ] No critical alerts firing
- [ ] SLO alerts configured and silent
- [ ] PrometheusRule resources deployed

---

### Step 19: Verify External Secrets Refresh
```bash
# Check last refresh time (should update every 1 hour)
kubectl describe externalsecret astra-secrets -n astra-production | grep "Last Sync"

# Verify secret version
kubectl get secret astra-secrets -n astra-production -o yaml | grep "resourceVersion"
```

**External Secrets**:
- [ ] Last sync: < 1 hour ago
- [ ] Sync status: `SecretSynced`
- [ ] No sync errors in events

---

### Step 20: Run Vector Consistency Tests
```bash
# Execute vector consistency test suite
pytest tests/test_vector_consistency.py -v

# Expected: All tests pass
# Test coverage: 3 backends × 6 scenarios = 18 tests
```

**Vector Consistency**:
- [ ] All 18 tests pass
- [ ] Deterministic top-k results
- [ ] Monotonic similarity scores
- [ ] Metadata filtering working
- [ ] Empty query handling correct
- [ ] Boundary conditions handled

---

## Post-Deployment: Documentation

### Step 21: Update Deployment Log
Create entry in deployment log:

```markdown
## Deployment 2025-11-01 - ASTRA Core v2.0.0 Canary

**Operator**: [Your Name]  
**Start Time**: [YYYY-MM-DD HH:MM:SS UTC]  
**End Time**: [YYYY-MM-DD HH:MM:SS UTC]  
**Duration**: [XX minutes]  
**Status**: ✅ SUCCESS / ❌ ROLLBACK

**Pre-Canary Evidence**: audit/PRE_CANARY_[timestamp]/
**GO/NO-GO Decision**: GO (exit code 0)
**Security Gates**: PASS (0 HIGH/CRITICAL vulnerabilities)
**Coverage Gate**: PASS ([XX]% coverage)
**Backup Gate**: PASS (dry-run validated)

**Canary Progression**:
- 0% → 10%: [HH:MM] - PASS
- 10% → 20%: [HH:MM] - PASS
- 20% → 30%: [HH:MM] - PASS
- 30% → 40%: [HH:MM] - PASS
- 40% → 50%: [HH:MM] - PASS
- 50% → 100%: [HH:MM] - PROMOTED

**Issues Encountered**: None / [Description]
**Rollbacks**: 0
**Final State**: All pods healthy, metrics within SLOs
```

- [ ] Deployment log entry created

---

### Step 22: Notify Stakeholders
**Notification Channels**:
- [ ] Slack #astra-deployments
- [ ] Email to engineering team
- [ ] Update status page (if applicable)

**Message Template**:
```
🚀 ASTRA Core v2.0.0 deployed to production

Status: ✅ SUCCESS
Strategy: Flagger Canary (60 minutes)
Duration: [XX] minutes
Metrics: All SLOs met
Issues: None

Evidence pack: audit/GO_LIVE_EVIDENCE_2025-11-01/
Deployment log: [link]
```

- [ ] Stakeholders notified

---

### Step 23: Archive Evidence Pack
```bash
# Create compressed archive of all evidence
tar -czf audit/GO_LIVE_EVIDENCE_2025-11-01.tar.gz \
  audit/GO_LIVE_EVIDENCE_2025-11-01/ \
  audit/PRE_CANARY_*/

# Upload to S3 (or equivalent)
aws s3 cp audit/GO_LIVE_EVIDENCE_2025-11-01.tar.gz \
  s3://astra-deployments/evidence/2025-11-01/

# Verify upload
aws s3 ls s3://astra-deployments/evidence/2025-11-01/
```

**Evidence Archive**:
- [ ] Evidence pack compressed
- [ ] Uploaded to S3/storage
- [ ] Retention policy: 1 year

---

## Post-Deployment: Monitoring (Week 1)

### Step 24: Daily Health Checks (Days 1-7)
```bash
# Check pod status
kubectl get pods -n astra-production -l app=astra-core

# Check HPA status
kubectl get hpa astra-core -n astra-production

# Check Prometheus alerts
kubectl get prometheusrule -n monitoring | grep astra

# Check error logs
kubectl logs -n astra-production -l app=astra-core --since=24h | grep ERROR
```

**Daily Checklist**:
- [ ] Day 1: All pods healthy, no alerts
- [ ] Day 2: All pods healthy, no alerts
- [ ] Day 3: All pods healthy, no alerts
- [ ] Day 4: All pods healthy, no alerts
- [ ] Day 5: All pods healthy, no alerts
- [ ] Day 6: All pods healthy, no alerts
- [ ] Day 7: All pods healthy, no alerts

---

### Step 25: Week 1 Performance Review
**Metrics to Review** (query Prometheus/Grafana):
- Availability: Target 99.9%, Actual: _____
- P95 latency: Target < 2500ms, Actual: _____ms
- P99 latency: Target < 5000ms, Actual: _____ms
- Error rate: Target < 1%, Actual: _____%
- Success rate: Target > 99%, Actual: _____%

**Action Items**:
- [ ] Performance meets SLOs
- [ ] No recurring errors
- [ ] No customer complaints
- [ ] Ready for full production traffic

---

## Completion

**Deployment Status**: ⬜ COMPLETE / ⬜ ROLLBACK / ⬜ BLOCKED

**Sign-off**:
- **Operator**: __________________ Date: __________
- **SRE Lead**: __________________ Date: __________
- **Engineering Manager**: __________________ Date: __________

---

## Rollback Procedure (If Needed)

### Emergency Rollback
```bash
# Immediate rollback to previous version
kubectl rollout undo deployment/astra-core -n astra-production

# Verify rollback status
kubectl rollout status deployment/astra-core -n astra-production

# Verify all pods running old version
kubectl get pods -n astra-production -l app=astra-core

# Notify stakeholders
echo "ROLLBACK INITIATED: ASTRA Core v2.0.0 → previous version"
```

### Post-Rollback Actions
1. Investigate root cause
2. Create incident report
3. Fix issues in staging
4. Re-run pre-canary validation
5. Schedule new deployment attempt

---

## Contact Information

**On-Call Engineer**: [Phone/Slack]  
**SRE Lead**: [Phone/Slack]  
**Engineering Manager**: [Phone/Slack]  
**Escalation Path**: [Process]

**Runbook**: See `ASTRA_PHASE_B_GO_LIVE_RUNBOOK.md`  
**Evidence Pack**: `audit/GO_LIVE_EVIDENCE_2025-11-01/README.md`

---

**Checklist Version**: 1.0.0  
**Last Updated**: 2025-11-01  
**Next Review**: 2025-12-01
