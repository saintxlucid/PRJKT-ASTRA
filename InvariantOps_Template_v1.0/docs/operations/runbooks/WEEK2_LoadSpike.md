# Week-2 Load-Spike Runbook (10× Traffic)

**Objective**: Maintain SLOs during a surprise 10× traffic surge  
**MTTR Target**: 15 minutes  
**Severity**: P1  
**On-Call**: SRE rotation

---

## 1. DETECT (0-2 minutes)

### Alerts Firing
- `p95_latency > 2.0s for 5m`
- `queue_depth > 50 for 5m`
- `hpa_at_max_replicas for 10m`
- `five_xx_rate > 0.5% for 3m`
- `rate_limit_429_spike`

### Dashboard Check
- **Canary Health**: Grafana → ASTRA Core → Request Rate panel
- **Rate Limit Heatmap**: Check per-client distribution
- **Vector DB Metrics**: Query latency, connection pool saturation

### Diagnosis Commands
```bash
# Current load
kubectl top pods -n production -l app=your-service

# HPA status
kubectl get hpa -n production

# Request rate by client
kubectl logs -n production -l app=your-service --tail=1000 | grep "client_id" | sort | uniq -c | sort -rn | head -20

# Circuit breaker trips
kubectl logs -n production -l app=your-service | grep "CircuitBreakerTripped"
```

---

## 2. STABILIZE (2-10 minutes)

### Immediate Actions

#### A. Raise HPA Floor (Priority 1)
```bash
# Increase minimum replicas from 3 to 6
kubectl patch hpa your-service -n production --type merge -p '{"spec":{"minReplicas":6}}'

# Verify scaling
watch kubectl get pods -n production -l app=your-service
```

#### B. Enable Admission Control (Priority 1)
```bash
# Set queue depth threshold to 80 (reject when >=80)
kubectl set env deployment/your-service -n production ADMISSION_QUEUE_THRESHOLD=80

# Verify config
kubectl describe deployment your-service -n production | grep ADMISSION
```

**Effect**: Service responds with `503 Retry-After: 5` when overloaded

#### C. Lower Per-Client Burst Allowance (Priority 2)
```bash
# Reduce burst from 100 to 50 requests/minute
kubectl set env deployment/your-service -n production RATE_LIMIT_BURST=50

# Reload rate limiter (if hot-reload supported)
curl -X POST http://your-service-admin:8001/admin/reload-rate-limits \
  -H "x-astra-admin: $ADMIN_KEY"
```

#### D. Prewarm Critical Paths (Priority 2)
```bash
# Send warmup requests to LLM/model/DB pools
for i in {1..10}; do
  curl -X POST http://your-service:8001/answer \
    -H "Content-Type: application/json" \
    -H "x-astra-key: warmup-key" \
    -d '{"query":"warmup","max_tokens":1}' &
done
```

---

## 3. SCALE (10-20 minutes)

### Horizontal Scaling

#### A. Vector Database
```bash
# Increase Qdrant replicas
kubectl scale statefulset qdrant -n production --replicas=6

# Tune ANN parameters (reduce precision for speed)
# Edit Qdrant config: ef_search=50 (down from 100)
kubectl edit configmap qdrant-config -n production
kubectl rollout restart statefulset qdrant -n production
```

#### B. Model Pool
```bash
# Add GPU nodes to cluster (if autoscaler not reacting fast enough)
gcloud container clusters resize your-cluster --num-nodes=8 --zone=us-central1-a

# Pin model pods to new nodes
kubectl label nodes <new-node-1> <new-node-2> workload=model
kubectl patch deployment model-pool -n production -p '{"spec":{"template":{"spec":{"nodeSelector":{"workload":"model"}}}}}'
```

#### C. Enable Response Cache (Temporary)
```bash
# Enable Redis cache for identical prompts (TTL=5 minutes)
kubectl set env deployment/your-service -n production ENABLE_RESPONSE_CACHE=true CACHE_TTL_SECONDS=300

# Monitor cache hit rate
kubectl logs -n production -l app=your-service | grep "cache_hit_rate"
```

---

## 4. VERIFY (20-30 minutes)

### SLO Compliance Check
```bash
# Query Prometheus for past 10 minutes
curl -s "http://prometheus:9090/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.95, rate(request_duration_seconds_bucket[10m]))' \
  | jq '.data.result[0].value[1]'
```

**Success Criteria** (hold for 10 consecutive minutes):
- ✅ p95 < 2.5s
- ✅ Success rate ≥ 99%
- ✅ 5xx rate < 1%
- ✅ Circuit breaker trips = 0
- ✅ Queue depth < 50

### Gradual Throttle Removal
```bash
# Step 1: Restore burst allowance (after 10 min stability)
kubectl set env deployment/your-service -n production RATE_LIMIT_BURST=100

# Step 2: Disable admission control (after 20 min stability)
kubectl set env deployment/your-service -n production ADMISSION_QUEUE_THRESHOLD=100

# Step 3: Lower HPA floor to normal (after 30 min stability)
kubectl patch hpa your-service -n production --type merge -p '{"spec":{"minReplicas":3}}'
```

---

## 5. POST-INCIDENT (30+ minutes)

### Grafana Annotation
```bash
# Tag the event for future analysis
curl -X POST http://grafana:3000/api/annotations \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -d '{
    "time": '$(date +%s000)',
    "text": "Load spike: 10× traffic handled via runbook",
    "tags": ["load-spike", "week2", "sre-action"]
  }'
```

### Incident Retrospective
- Open incident ticket: `INC-$(date +%Y%m%d)-LoadSpike`
- Document timeline in `docs/operations/Incident_Retrospective_Template.md`
- Calculate actual throughput: `kubectl logs | grep requests_per_second`
- Identify root cause: Marketing campaign? Bot attack? Partner integration?
- Action items:
  - [ ] Tune HPA thresholds based on actual load
  - [ ] Increase baseline capacity if growth is organic
  - [ ] Add rate limiting by IP or API key if abuse detected
  - [ ] Improve cache hit rate (analyze cache misses)

### Capacity Planning Update
- Update `docs/operations/Capacity_Planning_Policy.md`
- If load is sustained: File ticket for permanent capacity increase
- If load is bursty: Improve autoscaler response time (reduce cooldown)

---

## 6. ROLLBACK PLAN

**If SLOs cannot be restored within 15 minutes:**

1. **Enable maintenance mode**:
   ```bash
   kubectl set env deployment/your-service -n production MAINTENANCE_MODE=true
   ```
   - Returns `503 Service Unavailable` with retry guidance

2. **Revert recent deployments**:
   ```bash
   kubectl rollout undo deployment/your-service -n production
   ```

3. **Activate DR cluster** (if multi-region):
   ```bash
   kubectl --context=dr-cluster scale deployment/your-service --replicas=10
   # Update DNS to point to DR
   ```

4. **Notify stakeholders**:
   - Slack: `#incidents` channel
   - Status page: Update with degraded service message

---

## Contacts

- **SRE On-Call**: PagerDuty escalation
- **Engineering Lead**: Slack `@eng-lead`
- **Incident Commander**: [Name/Phone]
- **Runbook Owner**: SRE Team

---

**Last Tested**: 2025-10-15  
**Test Outcome**: SUCCESS (10× load handled in 12 minutes)  
**Next Test**: 2025-11-15
