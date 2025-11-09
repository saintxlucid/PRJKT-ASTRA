# ASTRA Production Cutover - Pre-Flight Checklist

**Date:** _____________  
**Engineer:** _____________  
**Environment:** Production K8s cluster  
**Version:** _____________

---

## ✅ Security & Secrets

- [ ] **K8s Secret Created** — `kubectl -n astra get secret bridge-keys` shows secret exists
- [ ] **No Plaintext Keys** — Keys file JSON is mounted from secret (not ConfigMap)
- [ ] **Vault Integration** (optional) — If using Vault, secret path configured and tested
- [ ] **TLS Certificate Issued** — `kubectl -n astra get certificate` shows Ready=True
- [ ] **HTTPS Redirect Verified** — `curl -I http://bridge.example.com` returns 301/308 → HTTPS
- [ ] **Ingress TLS Secret Mounted** — `kubectl -n astra describe ingress` shows TLS secret name

**Verification Commands:**
```bash
# Check secret exists
kubectl -n astra get secret bridge-keys -o jsonpath='{.data.bridge_keys}' | base64 -d | jq .

# Verify TLS certificate
kubectl -n astra get certificate astra-tls -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'

# Test HTTPS redirect
curl -I http://bridge.example.com 2>&1 | grep -E "HTTP|Location"
```

---

## ✅ RBAC & Key Management

- [ ] **Admin Key Created** — At least one key with scopes: `["bridge:admin", "docs:ingest", "docs:search"]`
- [ ] **Agent Key Created** — At least one key with scopes: `["bridge:call", "docs:search"]` (NO `tool:shell`)
- [ ] **No Shell Scope Issued** — Verified no keys have `tool:shell` scope (or shell adapter removed)
- [ ] **Key Rotation Plan** — Admin key rotation scheduled for 24h post-cutover
- [ ] **BRIDGE_KEYS_FILE Mounted** — Deployment env shows `BRIDGE_KEYS_FILE=/run/secrets/bridge_keys`

**Verification Commands:**
```bash
# Check keys file for dangerous scopes
kubectl -n astra exec -it deploy/bridge -- cat /run/secrets/bridge_keys | jq 'to_entries[] | select(.value.scopes | index("tool:shell"))'
# Should return empty

# List all keys (admin only - requires admin key)
curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/admin/usage | jq 'keys'
```

**Test Admin Key:**
```bash
export ADMIN_KEY="admin-key-from-secret"
curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/tools | jq .
```

**Test Agent Key:**
```bash
export AGENT_KEY="agent-key-from-secret"
curl -sS -X POST "https://bridge.example.com/call" \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"llama","args":{"messages":[{"role":"user","content":"test"}],"max_tokens":10}}' | jq .
```

---

## ✅ Metrics & Monitoring

- [ ] **Prometheus Scraping Bridge** — Target `bridge:8888/metrics` UP in Prometheus
- [ ] **Prometheus Scraping Docs** — Target `docs:8777/metrics` UP in Prometheus
- [ ] **Prometheus Scraping Qdrant** — Target `qdrant:6333/metrics` UP (if available)
- [ ] **Grafana Dashboards Imported** — Bridge dashboard and Docs dashboard visible
- [ ] **Alert Rules Loaded** — `kubectl -n monitoring get prometheusrule` shows astra-alerts
- [ ] **Test Alert Fired** — Manually trigger a test alert and verify on-call receives it

**Verification Commands:**
```bash
# Check Prometheus targets
kubectl -n monitoring port-forward svc/prometheus 9090:9090 &
curl -sS http://127.0.0.1:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | contains("bridge") or contains("docs") or contains("qdrant")) | {job: .labels.job, health: .health}'

# List alert rules
kubectl -n monitoring get prometheusrule

# Test alert (create a fake high-error-rate condition)
# ... or use Prometheus alert UI to force-fire a test alert
```

**Key Metrics to Monitor:**
- Bridge: `bridge_calls_total`, `bridge_call_duration_seconds_bucket`, `bridge_errors_total`
- Docs: `docs_ingest_total`, `docs_search_total`, `docs_search_duration_seconds_bucket`
- Qdrant: collection size, query latency (via Qdrant metrics)

---

## ✅ Backups & Disaster Recovery

- [ ] **Model Backup Verified** — Models PV snapshot exists or S3 sync completed
- [ ] **Qdrant Snapshot Created** — Manual snapshot triggered and file verified
- [ ] **Restore Test Completed** — At least one restore from backup tested in staging
- [ ] **Backup Schedule Configured** — CronJob or Velero schedule active
- [ ] **Backup Retention Policy Set** — Old snapshots pruned (e.g., keep last 7 days)

**Verification Commands:**
```bash
# Check PVC for models
kubectl -n astra get pvc astra-models -o jsonpath='{.status.capacity.storage}'

# Trigger Qdrant snapshot (if API available)
curl -X POST "http://qdrant:6333/collections/astra_docs/snapshots" -sS | jq .

# List snapshots
kubectl -n astra exec -it $(kubectl -n astra get pods -l app=qdrant -o jsonpath='{.items[0].metadata.name}') -- ls -lh /qdrant/storage/snapshots/

# Verify backup CronJob
kubectl -n astra get cronjob backup-qdrant -o yaml
```

**Restore Test (Run in Staging):**
```bash
# Stop Qdrant, restore snapshot, restart, verify collection count
kubectl -n staging scale deployment qdrant --replicas=0
# ... restore snapshot to PV
kubectl -n staging scale deployment qdrant --replicas=1
curl -sS http://qdrant-staging:6333/collections | jq .
```

---

## ✅ Disk & Resource Monitoring

- [ ] **PV Usage < 80%** — All PVs (models, qdrant, bridge data) have headroom
- [ ] **Disk Alerts Configured** — Alert fires if PV > 80% or PV > 90%
- [ ] **Resource Requests/Limits Set** — Bridge and Docs deployments have CPU/memory requests
- [ ] **HPA Configured** — HorizontalPodAutoscaler exists for bridge (and optionally docs)
- [ ] **HPA Min/Max Verified** — min=2, max=10 (or your settings)

**Verification Commands:**
```bash
# Check PV usage
kubectl -n astra exec -it $(kubectl -n astra get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}') -- df -h /data

kubectl -n astra exec -it $(kubectl -n astra get pods -l app=qdrant -o jsonpath='{.items[0].metadata.name}') -- df -h /qdrant/storage

# Check HPA
kubectl -n astra get hpa

# Check resource limits
kubectl -n astra get deployment bridge -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

**Alert Rule Example (Prometheus):**
```yaml
- alert: PVCUsageHigh
  expr: kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes > 0.80
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "PVC {{ $labels.persistentvolumeclaim }} usage > 80%"
```

---

## ✅ Security Hardening

- [ ] **Shell Adapter Removed** — `shell` tool removed from bridge or no keys with `tool:shell`
- [ ] **RunAsNonRoot Enabled** — Deployment spec has `securityContext.runAsNonRoot: true`
- [ ] **NetworkPolicy Applied** — Bridge can only reach llama, qdrant, and egress for metrics
- [ ] **Ingress Rate Limiting** — NGINX `limit_req` configured (optional but recommended)
- [ ] **Client Max Body Size Set** — NGINX `client_max_body_size` ≤ 50M for docs uploads
- [ ] **Admin Endpoints Protected** — `/admin/*` routes require admin scope or IP allowlist

**Verification Commands:**
```bash
# Check runAsNonRoot
kubectl -n astra get deployment bridge -o jsonpath='{.spec.template.spec.securityContext.runAsNonRoot}'

# Check NetworkPolicy
kubectl -n astra get networkpolicy

# Check Ingress annotations
kubectl -n astra get ingress astra-ingress -o yaml | grep -A5 annotations
```

**NetworkPolicy Example (apply if missing):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: bridge-egress
  namespace: astra
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
          port: 9090  # Prometheus push
```

---

## ✅ Load Test Readiness

- [ ] **Load Test Script Ready** — `scripts/load_test_bridge.ps1` or `hey` command prepared
- [ ] **Target QPS Defined** — Expected load: _____ req/sec (e.g., 50 RPS sustained)
- [ ] **Smoke Scripts Ready** — `smoke_semantic_search.ps1` and `smoke_docs.ps1` pass
- [ ] **Baseline Metrics Captured** — P95 latency and error rate recorded pre-cutover

**Load Test Command (Example with `hey`):**
```bash
# Install hey: go install github.com/rakyll/hey@latest

# Prepare payload
cat > payload.json <<EOF
{
  "tool_name": "llama",
  "args": {
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 20
  }
}
EOF

# Run load test (200 requests, 20 concurrent)
hey -n 200 -c 20 -m POST \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -D payload.json \
  https://bridge.example.com/call

# Watch metrics in Grafana during test
```

---

## ✅ Smoke Tests (Run Now)

### 1. Bridge Health & Tools List

```bash
# Health (public endpoint)
curl -fsS https://bridge.example.com/health | jq .
# Expected: {"ok": true, "version": "..."}

# List tools (admin key)
curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/tools | jq .
# Expected: ["llama", "file_read"]
```

### 2. Bridge Tool Call (Agent Key)

```bash
curl -sS -X POST "https://bridge.example.com/call" \
  -H "x-api-key: $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "llama",
    "args": {
      "messages": [{"role": "user", "content": "ping"}],
      "max_tokens": 16
    }
  }' | jq .
# Expected: {"result": {"choices": [...]}}
```

### 3. Docs Ingest (Agent Key)

```bash
curl -sS -X POST "https://docs.example.com/v1/documents/ingest" \
  -H "x-api-key: $AGENT_KEY" \
  -F "file=@/path/to/sample.pdf" | jq .
# Expected: {"ingested_chunks": 12, "collection": "astra_docs"}
```

### 4. Docs Semantic Search (Agent Key)

```bash
curl -sS -G "https://docs.example.com/v1/documents/search" \
  -H "x-api-key: $AGENT_KEY" \
  --data-urlencode "q=introduction" \
  --data-urlencode "top=5" | jq .
# Expected: [{"id": "...", "text": "...", "score": 0.9}, ...]
```

### 5. Qdrant Collections Check

```bash
# Port-forward (if not exposed publicly)
kubectl -n astra port-forward svc/qdrant 6333:6333 &

curl -sS http://127.0.0.1:6333/collections | jq .
# Expected: {"result": {"collections": [{"name": "astra_docs"}]}}
```

### 6. Audit Log & Usage (Admin Key)

```bash
curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/admin/usage | jq .
# Expected: {"key1": {"count": 5, ...}, ...}

# If audit endpoint exists
curl -sS -H "x-api-key: $ADMIN_KEY" https://bridge.example.com/audit/recent | jq .
```

---

## ✅ Go / No-Go Criteria

### **GO** if all pass:
- ✅ All smoke tests return expected results
- ✅ Error rate < 0.5% in last 15 minutes
- ✅ P95 latency < 500ms (or your SLO)
- ✅ No critical alerts firing
- ✅ Disk usage < 80% on all PVs
- ✅ Backup/restore tested successfully

### **NO-GO** if any fail:
- ❌ Ingest or search returns errors
- ❌ Qdrant unreachable or collection missing
- ❌ Disk usage > 80%
- ❌ Unknown API keys detected in audit log
- ❌ TLS cert not issued or expired
- ❌ Alert rules not firing (test alert failed)

---

## 📋 Sign-Off

**Checklist Completed By:** _____________  
**Date/Time:** _____________  
**Approval (SRE Lead):** _____________  
**Approval (Engineering Lead):** _____________  

**Decision:** [ ] GO / [ ] NO-GO  

**Notes:**
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

