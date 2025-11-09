# ASTRA Monitoring Setup Guide

**Deploy before cutover for T+0→T+2h visibility**

---

## 🎯 Quick Setup (5 Minutes)

### Prerequisites

- Prometheus Operator installed in cluster
- Grafana deployed and accessible
- `kubectl` access to cluster

---

## 📊 Step 1: Deploy Prometheus Rules (2 min)

### Apply PrometheusRule

```bash
# Apply alert rules
kubectl apply -f k8s/prometheusrule-astrasafety.yaml

# Verify rules loaded
kubectl -n monitoring get prometheusrule astra-critical-rules

# Check Prometheus UI
# Navigate to: http://prometheus.example.com/rules
# Look for: astra-critical group with 18 alerts
```

### Verify Alerting Works

```bash
# Check Prometheus targets are being scraped
curl -s http://prometheus.example.com/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="bridge" or .labels.job=="docs" or .labels.job=="qdrant")'

# Expected: 3 targets (bridge, docs, qdrant) with state="up"
```

### Configure Alertmanager (Optional)

If you want alerts routed to Slack/PagerDuty:

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-main
  namespace: monitoring
stringData:
  alertmanager.yaml: |
    global:
      slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    
    route:
      group_by: ['alertname', 'severity']
      group_wait: 10s
      group_interval: 5m
      repeat_interval: 3h
      receiver: 'slack-critical'
      routes:
      - match:
          severity: page
        receiver: 'pagerduty'
      - match:
          severity: critical
        receiver: 'slack-critical'
      - match:
          severity: warn
        receiver: 'slack-warnings'
    
    receivers:
    - name: 'slack-critical'
      slack_configs:
      - channel: '#astra-alerts'
        title: '🚨 {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
    
    - name: 'slack-warnings'
      slack_configs:
      - channel: '#astra-ops'
        title: '⚠️  {{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
    
    - name: 'pagerduty'
      pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

Apply:

```bash
kubectl apply -f alertmanager-config.yaml
```

---

## 📈 Step 2: Import Grafana Dashboard (3 min)

### Option A: UI Import (Easiest)

1. Open Grafana: `https://grafana.example.com`
2. Click **"+"** → **"Import"**
3. Paste contents of `k8s/grafana-dashboard-astra-ops.json`
4. Click **"Load"**
5. Select datasource: **Prometheus**
6. Click **"Import"**

**Dashboard URL:** `https://grafana.example.com/d/astra-ops`

### Option B: ConfigMap Auto-Provisioning

```yaml
# grafana-dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: astra-ops-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  astra-ops.json: |
    # Paste contents of k8s/grafana-dashboard-astra-ops.json here
```

Apply:

```bash
kubectl apply -f grafana-dashboard-configmap.yaml

# Grafana will auto-discover and load dashboard within 60 seconds
```

### Verify Dashboard

Open: `https://grafana.example.com/d/astra-ops`

**Expected panels:**
1. ✅ Bridge - Error Rate (%) — Gauge showing < 1%
2. ✅ Bridge - P95 Latency (s) — Gauge showing < 1s
3. ✅ Qdrant - Status — Shows "1" (UP)
4. ✅ Bridge - Calls/sec — Timeseries graph
5. ✅ Docs - Search/min — Timeseries graph
6. ✅ Docs - Ingest/sec — Timeseries graph
7. ✅ Bridge - Error Rate (Timeseries) — Graph with threshold line at 1%
8. ✅ Bridge - Latency Percentiles — P50/P90/P95/P99 lines
9. ✅ Bridge - Calls by Status — Stacked success/error
10. ✅ PV /data - Usage % — Gauge with thresholds at 70%/85%
11. ✅ Active Pods — Stat showing pod counts
12. ✅ Pod Restarts (1h) — Stat showing restart count
13. ✅ Bridge - Rate Limit Hits/sec — Graph of rate limit hits

---

## 🔍 Step 3: Test Monitoring Stack

### Generate Test Traffic

```powershell
# Set API keys
$env:ADMIN_KEY = "your-admin-key"
$env:AGENT_KEY = "your-agent-key"

# Generate 100 requests
1..100 | ForEach-Object {
    Invoke-WebRequest -Uri "https://bridge.example.com/call" `
        -Method POST `
        -Headers @{"x-api-key"=$env:AGENT_KEY; "Content-Type"="application/json"} `
        -Body '{"tool":"llama","params":{"prompt":"test"}}' `
        -UseBasicParsing | Out-Null
    
    Write-Host "." -NoNewline
}
Write-Host " Done"
```

### Check Metrics Appear

```bash
# Check bridge metrics endpoint
curl -sS https://bridge.example.com/metrics | grep bridge_calls_total

# Expected output:
# bridge_calls_total{status="success"} 100.0
```

### Verify Grafana Shows Data

Open dashboard: `https://grafana.example.com/d/astra-ops`

**Expected:**
- "Bridge - Calls/sec" panel shows spike
- "Bridge - Error Rate" panel shows 0%
- "Bridge - P95 Latency" panel shows < 1s

---

## 🚨 Step 4: Test Alerting (Optional)

### Trigger Test Alert

```bash
# Scale bridge to 0 (simulates outage)
kubectl -n astra scale deployment bridge --replicas=0

# Wait 2 minutes

# Check Prometheus alerts
curl -s http://prometheus.example.com/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="BridgeDown")'

# Expected: Alert in FIRING state
```

### Check Alert Notification

- **Slack:** Check `#astra-alerts` channel for alert
- **PagerDuty:** Check incidents dashboard

### Restore Service

```bash
# Scale back up
kubectl -n astra scale deployment bridge --replicas=2

# Wait 2 minutes for alert to resolve
```

---

## 📋 Critical Alerts Reference

### Page-Level Alerts (Immediate Action Required)

| Alert | Threshold | Action |
|-------|-----------|--------|
| **BridgeHighErrorRate** | >1% for 5m | Check logs, rollback if recent deploy |
| **BridgeHighLatencyP95** | >1s for 5m | Check LLM/Qdrant latency, scale up |
| **BridgeCriticalLatencyP95** | >3s for 2m | IMMEDIATE: Check downstream services |
| **BridgeDown** | Service unreachable 1m | Check pod status, ingress, endpoints |
| **QdrantDown** | Unreachable 2m | Check Qdrant pod, PV, network |
| **PVUsageHigh** | >85% for 5m | Stop ingests, clear space |
| **PVUsageCritical** | >95% for 1m | EMERGENCY: Stop all writes |
| **BridgeUnexpectedRestart** | Any restart in 10m | Check logs for OOM/crash |

### Warning-Level Alerts (Monitor & Plan)

| Alert | Threshold | Action |
|-------|-----------|--------|
| **DocsIngestDrop** | <0.1/sec for 15m | Check Qdrant connection, ingest workers |
| **DocsIngestFailureRate** | >5% for 5m | Check Qdrant capacity, embedder health |
| **DocsSearchLatencyHigh** | P95 >2s for 5m | Check Qdrant query perf, index size |
| **BridgeRateLimitHitFrequent** | >10/sec for 5m | Check for abuse, adjust quotas |
| **BridgePodCPUThrottling** | >30% throttled 10m | Increase CPU limits |
| **DocsPodMemoryHigh** | >90% for 5m | Check for leaks, increase limits |
| **HPAMaxedOut** | At max replicas 10m | Increase maxReplicas |

---

## 📊 Key Metrics to Watch During Cutover

### T+0 to T+10 (Deployment Phase)

**Watch continuously:**
1. **Bridge - Error Rate (%)** — MUST stay < 1%
2. **Bridge - P95 Latency** — MUST stay < 1s
3. **Qdrant - Status** — MUST show "1" (UP)
4. **Active Pods** — Should show expected count (2+ each)

**If ANY metric fails:**
- STOP deployment
- Execute rollback (see CUTOVER_RUNBOOK.md)
- Investigate issue before retry

### T+10 to T+30 (Initial Monitoring)

**Check every 5 minutes:**
1. Error rate still < 0.5%
2. P95 latency still < 500ms
3. No pod restarts
4. No alerts firing

### T+30 to T+120 (Extended Monitoring)

**Check every 10 minutes:**
1. All metrics stable
2. Disk usage not growing abnormally
3. Rate limit hits expected
4. No memory/CPU throttling

**Run smoke tests:**
```powershell
.\scripts\smoke_tests_production.ps1
```

### T+120 (Success Criteria)

**Required for GO decision:**
- ✅ Error rate < 0.5% for 2 hours
- ✅ P95 latency < 500ms for 2 hours
- ✅ Zero pod restarts in last hour
- ✅ Zero critical alerts in last hour
- ✅ Smoke tests passing
- ✅ Disk usage stable

---

## 🔥 Emergency Response

### High Error Rate (>2%)

```bash
# 1. Check recent logs
kubectl -n astra logs -l app=bridge --tail=200 --since=5m | grep ERROR

# 2. Check downstream services
curl -sS http://qdrant:6333/health
curl -sS http://llama:8001/v1/models

# 3. If recent deploy, ROLLBACK
kubectl -n astra rollout undo deployment/bridge
```

### High Latency (>3s)

```bash
# 1. Check Qdrant latency
curl -sS http://qdrant:6333/metrics | grep search_duration

# 2. Check LLM latency
curl -sS http://llama:8001/metrics | grep generation_duration

# 3. Scale up bridge (more workers)
kubectl -n astra scale deployment bridge --replicas=4
```

### Qdrant Down

```bash
# 1. Check pod status
kubectl -n astra get pods -l app=qdrant

# 2. Check PV
kubectl -n astra get pvc qdrant-data

# 3. Check logs
kubectl -n astra logs -l app=qdrant --tail=100

# 4. Restart if needed
kubectl -n astra delete pod -l app=qdrant
```

### Disk Full (>95%)

```bash
# IMMEDIATE: Stop ingestion
kubectl -n astra scale deployment docs --replicas=0

# Clear space
kubectl -n astra exec -it deploy/qdrant -- du -sh /data/*
kubectl -n astra exec -it deploy/qdrant -- rm -rf /data/tmp/*

# Resume when < 80%
kubectl -n astra scale deployment docs --replicas=2
```

---

## 📞 Monitoring URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana Dashboard** | https://grafana.example.com/d/astra-ops | Primary ops view |
| **Prometheus Alerts** | http://prometheus.example.com/alerts | Active alerts |
| **Prometheus Targets** | http://prometheus.example.com/targets | Scrape health |
| **Bridge Metrics** | https://bridge.example.com/metrics | Raw bridge metrics |
| **Docs Metrics** | https://docs.example.com/metrics | Raw docs metrics |
| **Qdrant Metrics** | http://qdrant:6333/metrics | Raw Qdrant metrics |

---

## ✅ Pre-Cutover Monitoring Checklist

- [ ] PrometheusRule deployed and loaded
- [ ] Grafana dashboard imported and showing data
- [ ] Alertmanager configured (Slack/PagerDuty)
- [ ] Test alert triggered and received
- [ ] Metrics endpoints accessible (bridge, docs, qdrant)
- [ ] Dashboard panels showing real data
- [ ] All 18 alert rules loaded in Prometheus
- [ ] Team trained on alert response procedures
- [ ] Runbook URLs updated with your domains
- [ ] Slack channels configured and tested

---

**Deploy monitoring BEFORE cutover — it's your safety net!** 🛡️

