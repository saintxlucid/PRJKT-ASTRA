# ASTRA Cutover - Quick Start Guide
# Execute cutover in 10 minutes with automated safety checks

---

## ⚡ Prerequisites (5 minutes)

### 1. Deploy ServiceMonitors (Prometheus Scraping)

```bash
cd "x:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"

# Apply ServiceMonitors
kubectl apply -f k8s/servicemonitor-bridge-docs.yaml

# Verify targets appear in Prometheus (wait 30 seconds)
# Navigate to: http://prometheus.monitoring:9090/targets
# Expected: astra-bridge-sm, astra-docs-sm, astra-qdrant-sm all "UP"
```

### 2. Make Scripts Executable

```bash
# On Windows with Git Bash or WSL
chmod +x scripts/cutover_canary.sh
chmod +x scripts/cutover_status.sh

# Or run via bash explicitly:
# bash scripts/cutover_canary.sh
```

### 3. Set Environment Variables

```bash
# Prometheus URL (update with your domain)
export PROM_URL="http://prometheus.monitoring:9090"

# OR for external access:
export PROM_URL="https://prometheus.example.com"

# Namespace
export NS="astra"
```

### 4. Verify Current Status

```bash
# Check live metrics
bash scripts/cutover_status.sh

# Expected output:
# Bridge Error Rate: < 1%
# Bridge P95 Latency: < 1s
# Qdrant Status: UP
# No active alerts
```

---

## 🚀 Execute Cutover (2 minutes)

### Option 1: Automated Canary (Recommended)

```bash
# Set all configuration
export NS=astra
export DEP_BLUE=bridge
export DEP_GREEN=bridge-green
export SVC=bridge
export PROM_URL="http://prometheus.monitoring:9090"

# Run automated canary cutover
bash scripts/cutover_canary.sh
```

**What it does:**
1. ✅ Verifies green deployment is ready
2. ✅ Health checks green pods via port-forward
3. ✅ Checks current blue error rate and latency
4. ✅ Switches service selector to green
5. ✅ Post-switch health check via service
6. ✅ 60-second canary monitoring
7. ✅ Auto-rollback if error rate spikes

**Expected output:**
```
✅ CUTOVER COMPLETE
Traffic switched from bridge to bridge-green
```

### Option 2: Manual Blue/Green (If Script Fails)

```bash
# 1. Verify green is ready
kubectl -n astra rollout status deploy/bridge-green

# 2. Switch service
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge-green"}}}'

# 3. Test health
kubectl -n astra run health-check --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -fsS http://bridge.astra:80/health

# 4. Monitor
bash scripts/cutover_status.sh
```

---

## 📊 Monitor (60 minutes)

### Every 5 Minutes (Automated)

```bash
# Run status check on loop
watch -n 5 bash scripts/cutover_status.sh
```

**Watch for:**
- ✅ Error rate < 0.5%
- ✅ P95 latency < 500ms
- ✅ No active alerts
- ✅ No pod restarts

### T+10 Minutes: Run Smoke Tests

```powershell
# In PowerShell terminal
$env:ADMIN_KEY = "your-admin-key"
$env:AGENT_KEY = "your-agent-key"

.\scripts\smoke_tests_production.ps1 `
    -BridgeUrl "https://bridge.example.com" `
    -DocsUrl "https://docs.example.com"

# Expected: 10/10 tests PASS
```

### T+30 Minutes: Check Grafana

Open: https://grafana.example.com/d/astra-ops

**Verify:**
- Bridge error rate gauge: < 1%
- Bridge P95 latency gauge: < 1s
- Qdrant status: 1 (UP)
- No pod restarts in last hour

---

## 🎯 Success Criteria (T+60)

### All Must Be True

- ✅ Error rate < 0.5% for 60 minutes
- ✅ P95 latency < 500ms for 60 minutes
- ✅ Zero pod restarts
- ✅ Zero alerts firing
- ✅ Smoke tests passing
- ✅ No errors in logs

### If All Pass → Proceed to Cleanup

```bash
# Scale down blue deployment
kubectl -n astra scale deploy/bridge --replicas=0

# After 1 hour of stable green, delete blue
kubectl -n astra delete deploy/bridge
```

---

## ❌ Rollback (If Needed)

### Immediate Rollback Command

```bash
# Switch service back to blue
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'

# Scale up blue if scaled down
kubectl -n astra scale deploy/bridge --replicas=2

# Verify
kubectl -n astra get endpoints bridge
bash scripts/cutover_status.sh
```

**Rollback if:**
- Error rate > 2% for 5+ minutes
- P95 latency > 3s for 5+ minutes
- Pods crash-looping
- Critical alerts firing

---

## 🔇 Optional: Alertmanager Silence

### Before Cutover (Reduce Noise)

```bash
# Create 45-minute silence
amtool silence add \
  alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95|BridgeUnexpectedRestart" \
  --duration=45m \
  --comment="Cutover to prod-v1.0.0" \
  --author="oncall@example.com"

# Save the silence ID
echo "SILENCE_ID: <copy from output>"
```

### After Successful Cutover (T+30)

```bash
# Remove silence early
amtool silence expire <SILENCE_ID>
```

---

## 📋 Quick Troubleshooting

### Script Fails: "Port-forward failed"

**Fix:**
```bash
# Check green pod exists
kubectl -n astra get pods -l app=bridge-green

# If no pods, check deployment
kubectl -n astra describe deploy bridge-green
```

### Script Fails: "Green health check FAILED"

**Fix:**
```bash
# Check green pod logs
kubectl -n astra logs -l app=bridge-green --tail=100

# Common issues:
# - Missing secrets (bridge-keys)
# - Bad image tag
# - Config errors
```

### Script Fails: "Blue error rate high"

**Fix:**
```bash
# Check current production health
bash scripts/cutover_status.sh

# If blue is broken, fix before deploying green
# Don't deploy broken code over broken system!
```

### "Prometheus unreachable"

**Fix:**
```bash
# Check Prometheus URL
curl -s "$PROM_URL/api/v1/status/config" | jq .

# If external, ensure ingress/firewall allows access
# If internal, run script from within cluster
```

---

## 🎯 One-Command Cutover (Advanced)

```bash
# Complete cutover with monitoring (single command)
export NS=astra && \
export DEP_BLUE=bridge && \
export DEP_GREEN=bridge-green && \
export SVC=bridge && \
export PROM_URL="http://prometheus.monitoring:9090" && \
bash scripts/cutover_canary.sh && \
echo "✅ Cutover complete - monitoring for 60 minutes..." && \
for i in {1..12}; do \
  sleep 300; \
  bash scripts/cutover_status.sh; \
done
```

**This will:**
1. Run canary cutover
2. Monitor every 5 minutes for 60 minutes
3. Display status snapshots

---

## 📞 Emergency Contacts

| Issue | Action |
|-------|--------|
| **Error rate >5%** | Rollback immediately, page on-call |
| **Pods crash-looping** | Rollback, check logs |
| **Qdrant down** | Check Qdrant pod, docs will failover to keyword |
| **Disk full** | Stop ingests, clear space, rollback |
| **Need help** | Slack #sre-incidents, escalate to engineering lead |

---

## ✅ Post-Cutover Tasks (T+2h)

- [ ] Remove Alertmanager silence
- [ ] Rotate admin key: `.\scripts\rotate_bridge_key.ps1`
- [ ] Scale down blue: `kubectl -n astra scale deploy/bridge --replicas=0`
- [ ] Update deployment docs with new version
- [ ] Post-mortem if any issues (even minor ones)

---

**Keep this guide open during cutover for quick reference!** 🚀
