# ASTRA Cutover - Final Pre-Flight Checklist
# Run this checklist before executing cutover

**Date:** October 16, 2025  
**Engineer:** _______________  
**Cutover Target:** _______________

---

## ✅ Infrastructure Readiness

### Kubernetes Cluster
- [ ] Namespace `astra` exists and accessible
- [ ] Namespace `monitoring` exists
- [ ] `kubectl` access verified
- [ ] Cluster CPU/Memory capacity checked (>30% free)
- [ ] Cluster node health verified (all nodes Ready)

### Secrets & Configuration
- [ ] `bridge-keys` secret exists in `astra` namespace
- [ ] Admin key configured in secret
- [ ] Agent key configured in secret
- [ ] No `tool:shell` scopes in production keys
- [ ] TLS certificates valid (check expiry date)
- [ ] Ingress TLS secret present

### Persistent Storage
- [ ] PVC `qdrant-data` exists and bound
- [ ] Disk usage < 70% (check with `df -h`)
- [ ] Backup of Qdrant data taken within last 24h
- [ ] Backup verified and restorable

---

## ✅ Monitoring & Observability

### Prometheus Setup
- [ ] Prometheus Operator installed
- [ ] ServiceMonitors applied: `kubectl apply -f k8s/servicemonitor-bridge-docs.yaml`
- [ ] All targets UP in Prometheus UI
  ```bash
  # Check: http://prometheus.monitoring:9090/targets
  # Expected: bridge, docs, qdrant all "UP"
  ```
- [ ] PrometheusRules loaded: `kubectl -n monitoring get prometheusrule`
- [ ] Recording rules functional: `kubectl -n monitoring get prometheusrule astra-recording-rules`
- [ ] Alert rules functional: `kubectl -n monitoring get prometheusrule astra-critical-rules`

### Grafana Dashboard
- [ ] Grafana accessible: https://grafana.example.com
- [ ] ASTRA Ops dashboard imported (UID: astra-ops)
- [ ] All panels showing data (not "No Data")
- [ ] Dashboard refresh set to 10s
- [ ] Dashboard shared with team

### Blackbox Exporter (Synthetic Checks)
- [ ] Blackbox Exporter deployed: `kubectl -n monitoring get deploy blackbox-exporter`
- [ ] Probes configured: `kubectl -n monitoring get probe`
- [ ] Probe targets returning success: `probe_success{job="probe/astra-https-probe"} == 1`

### Alerting
- [ ] Alertmanager configured and accessible
- [ ] Slack/PagerDuty integration tested
- [ ] Test alert fired and received successfully
- [ ] All 21 alert rules loaded (18 critical + 3 synthetic)
- [ ] Runbook URLs in alerts point to correct files

---

## ✅ Application Deployments

### Blue Deployment (Current Production)
- [ ] Bridge deployment running: `kubectl -n astra get deploy bridge`
- [ ] Replicas: _____ (min 2)
- [ ] All pods Ready: `kubectl -n astra get pods -l app=bridge`
- [ ] Health check passing: `curl https://bridge.example.com/health`
- [ ] Metrics exposed: `curl https://bridge.example.com/metrics | grep bridge_calls_total`

### Green Deployment (New Version)
- [ ] Bridge-green deployment created: `kubectl -n astra get deploy bridge-green`
- [ ] Image tag correct: _______________
- [ ] Replicas: _____ (match blue)
- [ ] All pods Ready
- [ ] Health check passing via port-forward
- [ ] No errors in logs: `kubectl -n astra logs -l app=bridge-green --tail=50`

### Docs Service
- [ ] Docs deployment running
- [ ] All pods Ready
- [ ] Health check passing
- [ ] Qdrant connection verified in logs

### Qdrant
- [ ] Qdrant pod running and Ready
- [ ] Health endpoint accessible: `curl http://qdrant.astra:6333/health`
- [ ] Collections present: `astra_docs`
- [ ] Metrics endpoint working

---

## ✅ Network & Security

### Services
- [ ] Bridge service exists: `kubectl -n astra get svc bridge`
- [ ] Service type: ClusterIP
- [ ] Named port `http` exposed (maps to 8888)
- [ ] Endpoints populated: `kubectl -n astra get endpoints bridge`

### Ingress
- [ ] Ingress configured for bridge: `kubectl -n astra get ingress bridge-ingress`
- [ ] TLS enabled
- [ ] Domain correct: bridge.example.com
- [ ] cert-manager issuer configured

### NetworkPolicy
- [ ] Default deny-all egress applied: `kubectl -n astra get netpol default-deny-all-egress`
- [ ] Bridge egress policy applied: `kubectl -n astra get netpol bridge-egress-policy`
- [ ] Docs egress policy applied: `kubectl -n astra get netpol docs-egress-policy`
- [ ] DNS allowed for all pods

---

## ✅ Scripts & Automation

### Validation Scripts
- [ ] `scripts/validate_preconditions.ps1` exists and runs successfully
- [ ] All checks PASS
- [ ] Output saved: `.\scripts\validate_preconditions.ps1 > validation.log`

### Smoke Tests
- [ ] `scripts/smoke_tests_production.ps1` exists
- [ ] Credentials configured: `$env:ADMIN_KEY` and `$env:AGENT_KEY`
- [ ] Test run against current production passes (10/10 tests)
- [ ] Test output saved

### Cutover Scripts
- [ ] `scripts/cutover_canary.sh` exists and is executable
  ```bash
  chmod +x scripts/cutover_canary.sh
  ```
- [ ] Script tested in staging environment
- [ ] Prometheus URL configured in script
- [ ] Script runs without errors in dry-run mode

### Status Scripts
- [ ] `scripts/cutover_status.sh` exists and is executable
  ```bash
  chmod +x scripts/cutover_status.sh
  ```
- [ ] Script returns sane metrics
- [ ] No "N/A" for critical metrics

### Chaos Drills
- [ ] `scripts/chaos_drills.ps1` executed successfully
- [ ] All 4 drills passed:
  - [ ] Qdrant down → docs fallback worked
  - [ ] Bridge restart → alert fired, HPA maintained traffic
  - [ ] Docs restart → service recovered
  - [ ] Network partition → blocked then restored

---

## ✅ Error Budget & SLO

### Current Status
- [ ] 30-day availability: _____ % (target: ≥99.5%)
- [ ] Error budget remaining: _____ % (should be >20%)
- [ ] No active incidents in last 24h
- [ ] Recent deployment success rate: _____ % (target: >90%)

### Budget Allocation
- [ ] Cutover estimated to consume: _____ minutes of budget
- [ ] Sufficient budget remaining after cutover: [ ] Yes / [ ] No
- [ ] If budget low (<20%), defer non-critical changes: [ ] N/A / [ ] Done

---

## ✅ Communication & Stakeholders

### Notifications
- [ ] Cutover announced in #sre-oncall (30 min advance notice)
- [ ] Cutover announced in #astra-alerts
- [ ] Stakeholders notified: Product, Engineering, Support
- [ ] Cutover window documented in shared calendar

### On-Call
- [ ] SRE on-call identified: _______________
- [ ] SRE acknowledged and available
- [ ] SRE has access to all systems (kubectl, Grafana, Prometheus)
- [ ] Engineering lead on standby: _______________

### Rollback Plan
- [ ] Rollback command documented and tested
  ```bash
  kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'
  ```
- [ ] Blue deployment kept running (not scaled to 0)
- [ ] Rollback tested in staging
- [ ] Rollback decision criteria defined (error rate >2%, latency >3s)

---

## ✅ Alertmanager Silences

### Silence Configuration
- [ ] Silence command prepared:
  ```bash
  amtool silence add \
    alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95|BridgeUnexpectedRestart|HPAMaxedOut" \
    --duration=45m \
    --comment="Cutover to prod-v1.0.0" \
    --author="oncall@example.com"
  ```
- [ ] Silence duration appropriate: 45 minutes
- [ ] Critical alerts NOT silenced (BridgeDown, QdrantDown, PVUsageCritical)
- [ ] Silence expiry plan documented

### Post-Cutover Silence Management
- [ ] Plan to remove silence early if cutover succeeds quickly
- [ ] Silence removal command ready:
  ```bash
  amtool silence expire <SILENCE_ID>
  ```

---

## ✅ Documentation & Runbooks

### Reference Documents
- [ ] `CUTOVER_EXECUTION_GUIDE.md` reviewed
- [ ] `CUTOVER_RUNBOOK.md` accessible
- [ ] `CUTOVER_QUICK_REF.md` printed or open in browser
- [ ] `CUTOVER_SILENCE_GUIDE.md` reviewed
- [ ] `SLO_REFERENCE.md` reviewed

### Runbook Links
- [ ] All runbook URLs in PrometheusRule annotations updated
- [ ] Links point to actual file paths (not example.com)
- [ ] Runbooks tested and accurate

---

## ✅ Final Safety Checks

### Load Testing (Optional but Recommended)
- [ ] Load test run against blue deployment
- [ ] Sustained load: _____ RPS for _____ minutes
- [ ] Error rate during load: _____ % (target: <0.5%)
- [ ] P95 latency during load: _____ s (target: <1s)
- [ ] No OOM kills or CPU throttling

### Smoke Tests (Pre-Cutover)
- [ ] Run smoke tests one final time
  ```powershell
  .\scripts\smoke_tests_production.ps1
  ```
- [ ] All 10 tests PASS
- [ ] Output saved with timestamp

### Team Readiness
- [ ] All team members notified of cutover
- [ ] Zoom/Teams call scheduled for live monitoring
- [ ] Screen sharing setup for Grafana dashboard
- [ ] Communication channel open (#sre-incidents)

---

## 🚦 GO / NO-GO DECISION

**Review Date/Time:** _______________

**Checklist Score:** _____ / 100 items completed

### GO Criteria (ALL must be YES)
- [ ] All infrastructure checks PASS
- [ ] All monitoring checks PASS
- [ ] Green deployment healthy
- [ ] Error budget sufficient (>20%)
- [ ] On-call SRE available
- [ ] Rollback plan tested
- [ ] Smoke tests passing

### Decision
- [ ] **GO** - Proceed with cutover
- [ ] **NO-GO** - Defer cutover (document reason below)

**Reason for NO-GO (if applicable):**

_______________________________________________

_______________________________________________

**Sign-Off:**
- **SRE On-Call:** _______________ Date/Time: _______________
- **Engineering Lead:** _______________ Date/Time: _______________
- **Platform Lead:** _______________ Date/Time: _______________

---

## 📋 Post-Checklist Actions

### If GO
1. Create Alertmanager silence (45 min)
2. Execute `cutover_canary.sh`
3. Monitor Grafana dashboard continuously
4. Run `cutover_status.sh` every 5 minutes
5. Keep this checklist open for reference

### If NO-GO
1. Document blockers in issue tracker
2. Schedule follow-up meeting to address blockers
3. Re-run checklist after fixes
4. Communicate new cutover date to stakeholders

---

**Keep this checklist visible during cutover for quick reference!** ✅
