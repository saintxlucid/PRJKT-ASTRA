# Alertmanager Silence Guide for Cutover

**Use silences during cutover to reduce noise while maintaining critical visibility**

---

## 🔇 When to Use Silences

**DO silence:**
- ✅ Expected transient errors during rolling updates
- ✅ Brief latency spikes during pod restarts
- ✅ HPA scaling events
- ✅ Planned pod restarts

**DO NOT silence:**
- ❌ Critical alerts (BridgeDown, QdrantDown, PVUsageCritical)
- ❌ Synthetic endpoint checks
- ❌ Security alerts
- ❌ Data corruption alerts

---

## 📋 Pre-Cutover Silence (Recommended)

### Silence Duration: 45 minutes

**Covers:**
- Rolling update: ~10 minutes
- Initial monitoring: ~30 minutes
- Buffer: ~5 minutes

### Create Silence

```bash
# Using amtool (Alertmanager CLI)
amtool silence add \
  alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95|BridgeUnexpectedRestart|HPAMaxedOut" \
  --duration=45m \
  --comment="Cutover window - Rolling update to prod-v1.0.0" \
  --author="oncall@example.com"
```

**Expected output:**
```
Created silence with ID: abc123def456
```

**Save this ID!** You'll need it to remove the silence early if needed.

---

## 🎯 Silence Templates

### Template 1: Rolling Update (Minimal Noise)

```bash
amtool silence add \
  alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95" \
  severity="page" \
  --duration=30m \
  --comment="Rolling update - Expected transient errors" \
  --author="oncall@example.com"
```

**Silences:** Error rate and latency alerts only  
**Duration:** 30 minutes  
**Keeps:** Critical alerts (down, disk full, restarts)

### Template 2: Blue/Green Cutover (Safe)

```bash
amtool silence add \
  alertname=~"BridgeUnexpectedRestart|HPAMaxedOut" \
  --duration=45m \
  --comment="Blue/Green deployment - Traffic switch" \
  --author="oncall@example.com"
```

**Silences:** HPA and restart alerts (expected during traffic switch)  
**Duration:** 45 minutes  
**Keeps:** Error rate, latency, endpoint checks

### Template 3: Hotfix (Aggressive Monitoring)

```bash
# NO SILENCE for hotfixes
# Keep all alerts enabled to catch regressions immediately
```

---

## 📊 Check Active Silences

### List All Silences

```bash
amtool silence query
```

**Output:**
```
ID          Starts              Ends                Matchers                  Comment
abc123...   2025-10-16 14:00    2025-10-16 14:45    alertname=~Bridge.*       Cutover window
```

### Query Specific Silence

```bash
amtool silence query alertname=~"Bridge.*"
```

---

## ❌ Remove Silence Early

### If Cutover Completes Successfully Early

```bash
# Use the silence ID from creation
amtool silence expire abc123def456
```

**Do this if:**
- ✅ Cutover completed in <10 minutes
- ✅ All metrics green
- ✅ Smoke tests passed
- ✅ Want full alerting restored

### Remove All Silences (Emergency)

```bash
# If something goes wrong and you need ALL alerts
amtool silence expire $(amtool silence query -q | awk '{print $1}')
```

**Use only if:** Major incident and you need full visibility NOW.

---

## 🚦 Cutover Workflow with Silences

### T-10 Minutes: Create Silence

```bash
# Create 45-minute silence
SILENCE_ID=$(amtool silence add \
  alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95|BridgeUnexpectedRestart" \
  --duration=45m \
  --comment="Cutover window - $(date)" \
  --author="oncall@example.com" \
  -o json | jq -r .silenceID)

echo "Silence ID: $SILENCE_ID" > /tmp/cutover_silence_id.txt
```

### T-0: Execute Cutover

```bash
# Deploy as normal
kubectl -n astra set image deployment/bridge bridge=ghcr.io/org/astra-bridge:prod-v1.0.0
```

### T+10 Minutes: Check Metrics

```bash
# Check Grafana dashboard
# If green → continue monitoring under silence
# If red → remove silence immediately and investigate
```

### T+30 Minutes: Assess Success

**If successful:**
```bash
# Remove silence early
amtool silence expire $(cat /tmp/cutover_silence_id.txt)

# Restore full alerting
echo "✅ Cutover successful - Full alerting restored"
```

**If issues detected:**
```bash
# Keep silence until resolved
echo "⚠️  Issues detected - Keeping silence active, investigating"
```

---

## 📝 Silence Best Practices

### DO:

1. ✅ **Document every silence** with comment and author
2. ✅ **Use shortest duration** needed (prefer 30m over 45m)
3. ✅ **Expire early** when cutover completes successfully
4. ✅ **Save silence IDs** for quick removal
5. ✅ **Communicate** in Slack: "Silences active for next 45m during cutover"

### DON'T:

1. ❌ **Silence critical alerts** (down, disk full, data loss)
2. ❌ **Create open-ended silences** (always set duration)
3. ❌ **Forget to remove** after cutover
4. ❌ **Silence all alerts** (defeats the purpose)
5. ❌ **Use silences as permanent mutes** (fix the root cause instead)

---

## 🔍 Silence Monitoring

### Check if Alert Would Fire (But is Silenced)

```bash
# Query Prometheus for alerts that would fire
curl -s http://prometheus.example.com/api/v1/alerts | \
  jq '.data.alerts[] | select(.state=="pending" or .state=="firing") | {alert: .labels.alertname, state: .state}'
```

**If you see firing alerts during silence:**
- They're being suppressed
- Check if they're critical (should NOT be silenced)
- Review silence matchers

---

## 🚨 Emergency: Silence Override

### If Critical Alert is Accidentally Silenced

```bash
# 1. Remove ALL silences immediately
amtool silence expire $(amtool silence query -q | awk '{print $1}')

# 2. Verify alerts are flowing
curl -s http://alertmanager.example.com/api/v2/alerts | jq '.[] | select(.status.state=="active")'

# 3. Respond to alerts as normal
```

---

## 📞 Silence Commands Reference

| Action | Command |
|--------|---------|
| **Create silence** | `amtool silence add alertname=X --duration=30m` |
| **List silences** | `amtool silence query` |
| **Expire silence** | `amtool silence expire <ID>` |
| **Expire all** | `amtool silence expire $(amtool silence query -q \| awk '{print $1}')` |
| **Check if silenced** | `amtool alert query alertname=X` |

---

## 📋 Cutover Silence Checklist

**Before Cutover:**
- [ ] Identify alerts to silence (error rate, latency, restarts)
- [ ] Determine silence duration (30-45 minutes)
- [ ] Create silence with proper comment and author
- [ ] Save silence ID to file
- [ ] Communicate in Slack: "#sre-oncall Silences active for cutover"

**During Cutover:**
- [ ] Monitor Grafana dashboard (silences don't affect metrics)
- [ ] Watch for critical alerts (should NOT be silenced)
- [ ] Check logs for errors

**After Cutover:**
- [ ] If successful: Expire silence early
- [ ] If issues: Keep silence, investigate, remove when resolved
- [ ] Verify full alerting restored
- [ ] Document any alerts that fired despite silence

---

## 🎯 Example: Complete Cutover with Silences

```bash
#!/bin/bash
# Complete cutover script with silence management

set -e

# 1. Create silence
echo "Creating 45-minute silence..."
SILENCE_ID=$(amtool silence add \
  alertname=~"BridgeHighErrorRate|BridgeHighLatencyP95|BridgeUnexpectedRestart" \
  --duration=45m \
  --comment="Cutover to prod-v1.0.0 - $(date)" \
  --author="oncall@example.com" \
  -o json | jq -r .silenceID)

echo "Silence ID: $SILENCE_ID"

# 2. Deploy
echo "Deploying new image..."
kubectl -n astra set image deployment/bridge \
  bridge=ghcr.io/org/astra-bridge:prod-v1.0.0 --record

# 3. Wait for rollout
echo "Waiting for rollout..."
kubectl -n astra rollout status deployment/bridge --timeout=10m

# 4. Smoke tests
echo "Running smoke tests..."
./scripts/smoke_tests_production.ps1

# 5. Check metrics
echo "Checking Grafana metrics..."
sleep 30

# 6. Remove silence if successful
echo "Cutover successful, removing silence..."
amtool silence expire $SILENCE_ID

echo "✅ Cutover complete with full alerting restored"
```

---

**Remember:** Silences are a tool for noise reduction, not incident hiding. Use responsibly! 🔇

