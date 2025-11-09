# ASTRA Production Cutover Runbook

**Version:** 1.0  
**Last Updated:** October 16, 2025  
**Owner:** SRE / Platform Engineering

---

## Overview

This runbook covers the production deployment and cutover for ASTRA Bridge and Documents services to Kubernetes. It includes:

- Rolling update (simple, zero-downtime)
- Blue/Green deployment (safer for major changes)
- Rollback procedures
- Post-cutover monitoring
- Security hardening steps

**Prerequisites:** Complete `PRE_CUTOVER_CHECKLIST.md` and confirm GO decision.

---

## Deployment Options

### Option A: Rolling Update (Recommended for Minor Updates)

**Pros:** Simple, built-in K8s, zero-downtime if probes configured  
**Cons:** Can't easily A/B test; rollback is via undo

**Use when:** Deploying patch releases, config changes, minor version bumps

### Option B: Blue/Green (Recommended for Major Changes)

**Pros:** Full validation before switching traffic; instant rollback  
**Cons:** Requires 2x resources temporarily; more manual steps

**Use when:** Major version upgrades, schema changes, critical fixes

---

## Option A: Rolling Update Procedure

### Step 1: Build and Push Image

```bash
# Set version tag
export VERSION=prod-v1.2.3
export REGISTRY=ghcr.io/your-org

# Build bridge image
docker build -t $REGISTRY/astra-bridge:$VERSION -f services/bridge/Dockerfile .
docker push $REGISTRY/astra-bridge:$VERSION

# Build docs image
docker build -t $REGISTRY/astra-docs:$VERSION -f services/documents/Dockerfile .
docker push $REGISTRY/astra-docs:$VERSION
```

### Step 2: Update Deployment Image

```bash
# Update bridge deployment
kubectl -n astra set image deployment/bridge \
  bridge=$REGISTRY/astra-bridge:$VERSION \
  --record

# Update docs deployment (if exists)
kubectl -n astra set image deployment/docs \
  docs=$REGISTRY/astra-docs:$VERSION \
  --record
```

### Step 3: Watch Rollout

```bash
# Monitor rollout status
kubectl -n astra rollout status deployment/bridge
kubectl -n astra rollout status deployment/docs

# Watch pods in real-time
kubectl -n astra get pods -w -l app=bridge
```

**Expected Output:**

```
Waiting for deployment "bridge" rollout to finish: 1 out of 2 new replicas have been updated...
Waiting for deployment "bridge" rollout to finish: 1 old replicas are pending termination...
deployment "bridge" successfully rolled out
```

### Step 4: Tail Logs (New Pods)

```bash
# Get latest pod name
export NEW_POD=$(kubectl -n astra get pods -l app=bridge --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

# Tail logs
kubectl -n astra logs -f $NEW_POD
```

**Look for:**

- `[INFO] Starting ASTRA Bridge...`
- `[INFO] Loaded X keys from /run/secrets/bridge_keys`
- No error or crash loops

### Step 5: Monitor Metrics (5-15 Minutes)

Open Grafana dashboard and watch:

- **Error Rate:** Should be < 0.5%
- **P95 Latency:** Within SLO (e.g., < 500ms)
- **Request Rate:** Steady or increasing normally
- **CPU/Memory:** Stable, no spikes

**Grafana URL:** `https://grafana.example.com/d/astra-bridge`

**Prometheus Queries:**

```promql
# Error rate
rate(bridge_errors_total[5m]) / rate(bridge_calls_total[5m])

# P95 latency
histogram_quantile(0.95, rate(bridge_call_duration_seconds_bucket[5m]))
```

### Step 6: Run Smoke Tests

```bash
# Quick smoke test
export AGENT_KEY="your-agent-key"

# Bridge call
curl -sS -X POST "https://bridge.example.com/call" \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"llama","args":{"messages":[{"role":"user","content":"test"}],"max_tokens":10}}' \
  | jq .result

# Docs search
curl -sS -G "https://docs.example.com/v1/documents/search" \
  -H "x-api-key: $AGENT_KEY" \
  --data-urlencode "q=test" \
  | jq '.[].text' | head -n 3
```

**Expected:** Both return successful responses.

### Step 7: Verify Audit Logs

```bash
export ADMIN_KEY="your-admin-key"

curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/admin/usage | jq .
```

**Look for:** Recent requests from agent key, no unexpected keys.

### Step 8: Gradual Traffic Increase (Optional)

If you have a canary ingress or traffic split:

```bash
# Increase canary weight from 10% → 50% → 100%
kubectl -n astra patch ingress astra-canary -p '{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/canary-weight":"50"}}}'

# Wait 5 minutes, monitor metrics, then:
kubectl -n astra patch ingress astra-canary -p '{"metadata":{"annotations":{"nginx.ingress.kubernetes.io/canary-weight":"100"}}}'
```

### Decision Point: Continue or Rollback?

**Continue if:**

- Error rate < 0.5%
- No critical alerts
- Smoke tests pass
- Logs show no errors

**Rollback if:**

- Error rate spikes > 2%
- P95 latency > 2x baseline
- New pods crash-looping
- Critical alerts firing

---

## Option B: Blue/Green Deployment Procedure

### Step 1: Prepare Green Deployment

```bash
# Copy current deployment manifest
kubectl -n astra get deployment bridge -o yaml > bridge-green.yaml

# Edit bridge-green.yaml:
# 1. Change metadata.name: bridge → bridge-green
# 2. Change spec.selector.matchLabels.app: bridge → bridge-green
# 3. Change spec.template.metadata.labels.app: bridge → bridge-green
# 4. Update image to new version

# Example sed commands (adjust for your manifest structure):
sed -i 's/name: bridge$/name: bridge-green/' bridge-green.yaml
sed -i 's/app: bridge$/app: bridge-green/g' bridge-green.yaml
sed -i "s|image: .*astra-bridge:.*|image: $REGISTRY/astra-bridge:$VERSION|" bridge-green.yaml
```

### Step 2: Deploy Green

```bash
kubectl -n astra apply -f bridge-green.yaml

# Wait for green to be ready
kubectl -n astra rollout status deployment/bridge-green
```

### Step 3: Test Green via Port-Forward

```bash
# Port-forward to green deployment
kubectl -n astra port-forward deployment/bridge-green 8889:8888 &

# Run smoke tests against localhost:8889
curl -sS http://127.0.0.1:8889/health | jq .

curl -sS -X POST "http://127.0.0.1:8889/call" \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"llama","args":{"messages":[{"role":"user","content":"green test"}],"max_tokens":10}}' \
  | jq .
```

**Expected:** All tests pass on green.

### Step 4: Switch Service Selector to Green

```bash
# Update service to point to green
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge-green"}}}'

# Verify service endpoints
kubectl -n astra get endpoints bridge
```

**Traffic is now flowing to green deployment.**

### Step 5: Monitor Green for 10-15 Minutes

Watch Grafana metrics (same as rolling update Step 5).

### Step 6: Decision Point

**If green is stable:**

```bash
# Scale down blue (old deployment)
kubectl -n astra scale deployment bridge --replicas=0

# Optional: delete blue after 24 hours
kubectl -n astra delete deployment bridge
```

**If green has issues, rollback (see Rollback section).**

---

## Rollback Procedures

### Rollback from Rolling Update

```bash
# Undo last rollout
kubectl -n astra rollout undo deployment/bridge
kubectl -n astra rollout undo deployment/docs

# Check status
kubectl -n astra rollout status deployment/bridge

# Verify old version is running
kubectl -n astra get pods -l app=bridge -o jsonpath='{.items[*].spec.containers[*].image}'
```

### Rollback from Blue/Green

```bash
# Switch service back to blue
kubectl -n astra patch svc bridge -p '{"spec":{"selector":{"app":"bridge"}}}'

# Verify endpoints
kubectl -n astra get endpoints bridge

# Scale up blue if scaled down
kubectl -n astra scale deployment bridge --replicas=2

# Delete green
kubectl -n astra delete deployment bridge-green
```

### Emergency Rollback (Scale Down)

If all else fails:

```bash
# Scale new deployment to 0
kubectl -n astra scale deployment bridge-green --replicas=0

# Ensure old deployment is running
kubectl -n astra scale deployment bridge --replicas=2

# Check service is routing to blue
kubectl -n astra get endpoints bridge
```

---

## Post-Cutover: First 2 Hours

### Monitoring Checklist

- [ ] **Watch Grafana Dashboard** — Error rate, latency, throughput
- [ ] **Check Logs** — `kubectl -n astra logs -l app=bridge -f --tail=100`
- [ ] **Monitor Alerts** — No critical alerts firing
- [ ] **Check Audit Logs** — Unusual keys or spikes in usage
- [ ] **CPU/Memory** — No resource exhaustion (< 80% of limits)

### Key Metrics Thresholds (Adjust to Your SLO)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | < 0.5% | Normal |
| Error Rate | 0.5% - 2% | Investigate |
| Error Rate | > 2% | Rollback |
| P95 Latency | < 500ms | Normal |
| P95 Latency | 500ms - 1s | Investigate |
| P95 Latency | > 1s | Rollback |
| CPU Usage | < 80% | Normal |
| CPU Usage | > 80% | Scale up (HPA should auto-scale) |
| Disk Usage | < 80% | Normal |
| Disk Usage | > 80% | Expand PV or clean up |

### Run Hourly Smoke Tests

```bash
# Automate with cron or K8s CronJob
while true; do
  echo "[$(date)] Running smoke test..."
  curl -sS -X POST "https://bridge.example.com/call" \
    -H "x-api-key: $AGENT_KEY" \
    -H "Content-Type: application/json" \
    -d '{"tool_name":"llama","args":{"messages":[{"role":"user","content":"hourly test"}],"max_tokens":5}}' \
    | jq -e '.result' || echo "SMOKE TEST FAILED"
  sleep 3600
done
```

---

## Post-Cutover: First 24 Hours

### Housekeeping Tasks

1. **Validate Nightly Backup Ran**

   ```bash
   # Check backup CronJob logs
   kubectl -n astra logs -l job-name=backup-qdrant --tail=50
   
   # Verify snapshot file created
   kubectl -n astra exec -it $(kubectl -n astra get pods -l app=qdrant -o jsonpath='{.items[0].metadata.name}') -- \
     ls -lh /qdrant/storage/snapshots/
   ```

2. **Rotate Admin Key (Best Practice)**

   ```bash
   # Generate new admin key
   NEW_ADMIN_KEY=$(openssl rand -hex 32)
   
   # Update keys JSON file
   # Edit keys file to add new key with admin scopes, remove old admin key
   
   # Update K8s secret
   kubectl -n astra create secret generic bridge-keys \
     --from-file=bridge_keys=./keys-updated.json \
     --dry-run=client -o yaml | kubectl apply -f -
   
   # Trigger key reload
   curl -sS -X POST -H "x-api-key: $OLD_ADMIN_KEY" \
     https://bridge.example.com/admin/reload-keys
   
   # Test new admin key
   curl -sS -H "x-api-key: $NEW_ADMIN_KEY" https://bridge.example.com/tools | jq .
   ```

3. **Review Audit Logs for Anomalies**

   ```bash
   # Download audit log
   kubectl -n astra exec -it $(kubectl -n astra get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}') -- \
     cat /data/bridge_audit.log | tail -n 1000 > audit-last-1000.log
   
   # Look for unknown keys
   cat audit-last-1000.log | jq '.api_key' | sort | uniq -c | sort -rn
   ```

4. **Check for Resource Bottlenecks**

   ```bash
   # Top pods by CPU
   kubectl -n astra top pods --sort-by=cpu
   
   # Top pods by memory
   kubectl -n astra top pods --sort-by=memory
   
   # Check HPA status
   kubectl -n astra get hpa -w
   ```

---

## Security Hardening (Immediate Post-Cutover)

### 1. Apply NetworkPolicy (If Not Already Done)

```bash
kubectl -n astra apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: bridge-egress-restrict
spec:
  podSelector:
    matchLabels:
      app: bridge
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: llama
      ports:
        - protocol: TCP
          port: 8001
    - to:
        - podSelector:
            matchLabels:
              app: qdrant
      ports:
        - protocol: TCP
          port: 6333
    - to:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443  # Allow HTTPS egress for external APIs if needed
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53  # DNS
EOF
```

### 2. Restrict Ingress to Admin Endpoints

**Option A: NGINX Ingress Annotation (IP Allowlist)**

```yaml
# Add to ingress metadata.annotations
nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8,192.168.1.0/24"
# Only allow admin endpoints from internal IPs
```

**Option B: Separate Ingress for Admin**

```bash
kubectl -n astra apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bridge-admin
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8"
spec:
  tls:
    - hosts:
        - bridge-admin.example.com
      secretName: bridge-admin-tls
  rules:
    - host: bridge-admin.example.com
      http:
        paths:
          - path: /admin
            pathType: Prefix
            backend:
              service:
                name: bridge
                port:
                  number: 8888
EOF
```

### 3. Set Client Max Body Size for Docs Ingress

```bash
# Add annotation to docs ingress
kubectl -n astra annotate ingress astra-docs \
  nginx.ingress.kubernetes.io/proxy-body-size=50m
```

### 4. Enable Rate Limiting (NGINX)

```bash
kubectl -n astra annotate ingress astra-ingress \
  nginx.ingress.kubernetes.io/limit-rps=100 \
  nginx.ingress.kubernetes.io/limit-burst-multiplier=5
```

---

## Operational Runbook Quick Reference

| Scenario | Command |
|----------|---------|
| **Rollback deployment** | `kubectl -n astra rollout undo deployment/bridge` |
| **Scale up replicas** | `kubectl -n astra scale deployment bridge --replicas=5` |
| **Restart pods** | `kubectl -n astra rollout restart deployment/bridge` |
| **Check logs (last hour)** | `kubectl -n astra logs -l app=bridge --since=1h --tail=500` |
| **Port-forward for debug** | `kubectl -n astra port-forward svc/bridge 8888:8888` |
| **Reload keys** | `curl -X POST -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/admin/reload-keys` |
| **Trigger Qdrant snapshot** | `curl -X POST http://qdrant:6333/collections/astra_docs/snapshots` |
| **Check PV usage** | `kubectl -n astra exec -it deploy/bridge -- df -h /data` |
| **Get HPA status** | `kubectl -n astra get hpa` |
| **Describe pod (debug)** | `kubectl -n astra describe pod <pod-name>` |

---

## Troubleshooting Common Issues

### Issue: Pods Crash-Looping

**Symptoms:** `kubectl get pods` shows `CrashLoopBackOff`

**Debug Steps:**

```bash
# Check pod logs
kubectl -n astra logs <pod-name> --previous

# Describe pod for events
kubectl -n astra describe pod <pod-name>

# Common causes:
# - Missing secret (BRIDGE_KEYS_FILE)
# - OOM (check memory limits)
# - Startup probe failing
```

**Fix:**

```bash
# If missing secret, create it
kubectl -n astra create secret generic bridge-keys --from-file=bridge_keys=./keys.json

# If OOM, increase memory limit
kubectl -n astra patch deployment bridge -p '{"spec":{"template":{"spec":{"containers":[{"name":"bridge","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
```

### Issue: High Error Rate

**Symptoms:** Grafana shows error rate > 2%

**Debug Steps:**

```bash
# Check recent errors in logs
kubectl -n astra logs -l app=bridge --tail=200 | grep ERROR

# Check audit log for failing keys
kubectl -n astra exec -it deploy/bridge -- cat /data/bridge_audit.log | jq 'select(.level=="ERROR")' | tail -n 20
```

**Common Causes:**

- Llama service unreachable → Check `kubectl -n astra get svc llama`
- Rate limit exceeded → Check usage: `curl -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/admin/usage | jq`
- Invalid keys → Reload keys

### Issue: High Latency

**Symptoms:** P95 latency > 1s

**Debug Steps:**

```bash
# Check if llama is slow
kubectl -n astra logs -l app=llama --tail=100

# Check if Qdrant is slow
curl -sS http://qdrant:6333/metrics | grep request_duration

# Check CPU throttling
kubectl -n astra top pods
```

**Fix:**

```bash
# Scale up HPA max
kubectl -n astra patch hpa bridge -p '{"spec":{"maxReplicas":10}}'

# Or manually scale
kubectl -n astra scale deployment bridge --replicas=5
```

### Issue: Disk Full

**Symptoms:** Audit log write errors or Qdrant refusing writes

**Debug Steps:**

```bash
# Check PV usage
kubectl -n astra exec -it deploy/bridge -- df -h /data
kubectl -n astra exec -it deploy/qdrant -- df -h /qdrant/storage
```

**Fix:**

```bash
# Clean up old audit logs (manual)
kubectl -n astra exec -it deploy/bridge -- sh -c 'tail -n 10000 /data/bridge_audit.log > /data/audit_tmp.log && mv /data/audit_tmp.log /data/bridge_audit.log'

# Or expand PV (if supported by storage class)
kubectl -n astra patch pvc astra-models -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
```

---

## Contact & Escalation

| Role | Contact | Escalation Path |
|------|---------|-----------------|
| **On-Call SRE** | Slack: #sre-oncall | Page via PagerDuty |
| **Platform Lead** | email@example.com | Slack DM |
| **Security Team** | security@example.com | For key compromise |

**Emergency Rollback Authority:** On-call SRE or Platform Lead

---

## Appendix: Load Test Example

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Create payload
cat > payload.json <<EOF
{
  "tool_name": "llama",
  "args": {
    "messages": [{"role": "user", "content": "load test message"}],
    "max_tokens": 20
  }
}
EOF

# Run load test (1000 requests, 50 concurrent)
hey -n 1000 -c 50 -m POST \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -D payload.json \
  https://bridge.example.com/call

# Monitor in Grafana during test
```

**Expected Results (Adjust to Your Environment):**

- Total time: < 60s for 1000 requests
- Success rate: > 99%
- P95 latency: < 500ms

---

**End of Runbook**

