# ASTRA Production Cutover - Quick Command Reference

**Emergency Contact:** SRE On-Call via PagerDuty  
**Grafana:** https://grafana.example.com/d/astra  
**Prometheus:** https://prometheus.example.com

---

## 🚨 Emergency Commands

```bash
# IMMEDIATE ROLLBACK
kubectl -n astra rollout undo deployment/bridge
kubectl -n astra rollout undo deployment/docs

# STOP TRAFFIC (scale to 0)
kubectl -n astra scale deployment bridge --replicas=0
kubectl -n astra scale deployment docs --replicas=0

# SCALE UP (emergency capacity)
kubectl -n astra scale deployment bridge --replicas=10
kubectl -n astra scale deployment docs --replicas=8

# RESTART (fix crash loops)
kubectl -n astra rollout restart deployment/bridge
kubectl -n astra rollout restart deployment/docs
```

---

## 📋 Pre-Cutover (T-30 minutes)

```powershell
# 1. Validate everything
.\scripts\validate_preconditions.ps1 -Namespace astra

# 2. Run smoke tests
$env:ADMIN_KEY = "your-admin-key"
$env:AGENT_KEY = "your-agent-key"
.\scripts\smoke_tests_production.ps1 -BridgeUrl "https://bridge.example.com" -DocsUrl "https://docs.example.com"

# 3. Check Grafana - confirm baseline metrics
# Error rate: <0.5%, P95 latency: <500ms

# 4. Get GO/NO-GO approval
```

---

## 🚀 Cutover - Rolling Update (T-0)

```bash
# 1. Build and push images
export VERSION=prod-v1.0.0
docker build -t ghcr.io/your-org/astra-bridge:$VERSION -f services/bridge/Dockerfile .
docker push ghcr.io/your-org/astra-bridge:$VERSION
docker build -t ghcr.io/your-org/astra-docs:$VERSION -f services/documents/Dockerfile .
docker push ghcr.io/your-org/astra-docs:$VERSION

# 2. Update deployments
kubectl -n astra set image deployment/bridge bridge=ghcr.io/your-org/astra-bridge:$VERSION --record
kubectl -n astra set image deployment/docs docs=ghcr.io/your-org/astra-docs:$VERSION --record

# 3. Watch rollout (wait 5-10 min)
kubectl -n astra rollout status deployment/bridge
kubectl -n astra rollout status deployment/docs
kubectl -n astra get pods -w

# 4. Check logs (new pods)
kubectl -n astra logs -l app=bridge -f --tail=100
kubectl -n astra logs -l app=docs -f --tail=100
```

---

## 📊 Monitoring (T+0 to T+2h)

```bash
# Watch Grafana dashboard continuously
open https://grafana.example.com/d/astra

# Check Prometheus targets
kubectl -n monitoring port-forward svc/prometheus 9090:9090 &
open http://localhost:9090/targets

# Key metrics to watch:
# - bridge_errors_total / bridge_calls_total < 0.005 (0.5%)
# - histogram_quantile(0.95, bridge_call_duration_seconds_bucket) < 0.5s
# - docs_search_duration_seconds < 0.3s
```

---

## ✅ Smoke Tests (Run Every 30 Min)

```powershell
# Quick bridge test
curl -sS -X POST "https://bridge.example.com/call" `
  -H "x-api-key: $env:AGENT_KEY" `
  -H "Content-Type: application/json" `
  -d '{"tool_name":"llama","args":{"messages":[{"role":"user","content":"test"}],"max_tokens":5}}' | jq .

# Quick docs search
curl -sS -G "https://docs.example.com/v1/documents/search" `
  -H "x-api-key: $env:AGENT_KEY" `
  --data-urlencode "q=test" | jq '.[0].text'

# Or run full suite
.\scripts\smoke_tests_production.ps1 -BridgeUrl "https://bridge.example.com" -DocsUrl "https://docs.example.com"
```

---

## 🔍 Debug Commands

```bash
# Get pod status
kubectl -n astra get pods -o wide

# Describe pod (see events)
kubectl -n astra describe pod <pod-name>

# Get logs (last 500 lines)
kubectl -n astra logs <pod-name> --tail=500

# Get previous pod logs (crash loop)
kubectl -n astra logs <pod-name> --previous

# Exec into pod
kubectl -n astra exec -it <pod-name> -- /bin/sh

# Check resource usage
kubectl -n astra top pods

# Check HPA status
kubectl -n astra get hpa

# Check PV usage
kubectl -n astra exec -it deploy/bridge -- df -h /data
kubectl -n astra exec -it deploy/qdrant -- df -h /qdrant/storage

# Port-forward for local testing
kubectl -n astra port-forward svc/bridge 8888:8888 &
kubectl -n astra port-forward svc/docs 8777:8777 &
```

---

## ❌ Rollback Decision Criteria

**Rollback IMMEDIATELY if:**

- Error rate > 2% for 5+ minutes
- P95 latency > 1s for 5+ minutes
- Pods crash-looping after 3 attempts
- Critical alerts firing (PagerDuty)
- Qdrant unreachable
- Key audit log shows breach

**Investigate (don't rollback yet) if:**

- Error rate 0.5% - 2%
- P95 latency 500ms - 1s
- 1-2 pod restarts (may be normal)
- Non-critical alerts

---

## 🔄 Rollback Procedure

```bash
# 1. Announce rollback in Slack #sre-incidents
# 2. Execute rollback
kubectl -n astra rollout undo deployment/bridge
kubectl -n astra rollout undo deployment/docs

# 3. Verify rollback success
kubectl -n astra rollout status deployment/bridge
kubectl -n astra rollout status deployment/docs

# 4. Check old version is running
kubectl -n astra get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# 5. Run smoke tests to confirm stability
.\scripts\smoke_tests_production.ps1

# 6. If still unstable, scale to 0 and use blue deployment
kubectl -n astra scale deployment bridge --replicas=0
kubectl -n astra scale deployment docs --replicas=0
# Point service to blue deployment or use backup instance
```

---

## 🎯 Success Criteria (T+2h)

- [ ] Error rate < 0.5%
- [ ] P95 latency < 500ms
- [ ] No crash loops
- [ ] No critical alerts
- [ ] Smoke tests passing
- [ ] Audit logs clean
- [ ] HPA responding (if load increased)

**If all pass:** Declare cutover successful, continue monitoring for 24h

---

## 📞 Escalation

| Severity | Action | Contact |
|----------|--------|---------|
| **P0** - Total outage | Page immediately | SRE On-Call (PagerDuty) |
| **P1** - Degraded | Slack alert | #sre-oncall |
| **P2** - Anomaly | Create ticket | Platform team |

---

## 📝 Post-Cutover Checklist (First 24h)

```bash
# 1. Rotate admin key (best practice)
# ... generate new key, update secret, reload

# 2. Check audit logs
kubectl -n astra exec -it deploy/bridge -- cat /data/bridge_audit.log | tail -n 1000 > audit.log

# 3. Verify backup ran
kubectl -n astra logs -l job-name=backup-qdrant

# 4. Apply NetworkPolicy (if not done)
kubectl apply -f k8s/networkpolicy.yaml

# 5. Configure alerts
kubectl apply -f k8s/prometheus-rules.yaml

# 6. Update runbook with lessons learned
```

---

## 🔗 Quick Links

- **Checklist:** [PRE_CUTOVER_CHECKLIST.md](./PRE_CUTOVER_CHECKLIST.md)
- **Runbook:** [CUTOVER_RUNBOOK.md](./CUTOVER_RUNBOOK.md)
- **Summary:** [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)
- **Grafana:** https://grafana.example.com/d/astra
- **Slack:** #sre-oncall, #astra-alerts

---

**Print this page and keep it handy during cutover!**

