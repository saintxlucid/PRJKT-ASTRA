# 🎯 ASTRA Core - Canary Deployment Runbook

**Purpose**: Safe deployment of new ASTRA Core versions using canary analysis  
**Duration**: ~30-60 minutes  
**Risk Level**: Low (gradual rollout with automatic rollback)

---

## 📋 Prerequisites

- [ ] New Docker image built and pushed: `astra-core:v1.1.0`
- [ ] All tests passing in staging environment
- [ ] Prometheus and Grafana configured
- [ ] kubectl access to production namespace
- [ ] Rollback plan reviewed
- [ ] Team on standby for monitoring

---

## 🚀 Deployment Options

### **Option A: Automated Canary (with Flagger)**

Flagger automatically manages canary analysis and promotion.

```bash
# Install Flagger (if not already installed)
kubectl apply -k github.com/fluxcd/flagger//kustomize/istio

# Apply canary configuration
kubectl apply -f k8s/canary/canary-deployment.yaml

# Update deployment image
kubectl set image deployment/astra-core \
  astra-core=astra-core:v1.1.0 \
  -n astra-production

# Watch canary progress
kubectl get canary astra-core -n astra-production -w

# Monitor logs
kubectl logs -n astra-production \
  -l app.kubernetes.io/name=flagger \
  --tail=100 -f
```

**Canary Analysis Steps** (automatic):
1. **Initialization** (0% canary traffic)
   - Flagger creates canary deployment
   - Runs pre-rollout webhook (load test)
   
2. **Traffic Shift** (10% → 50% in 10% increments)
   - Every 1 minute, increase traffic by 10%
   - Run acceptance tests at each step
   - Check metrics: success rate >99%, P95 latency <2500ms
   
3. **Promotion or Rollback**
   - If 5 consecutive checks pass → Promote to 100%
   - If any check fails → Automatic rollback

---

### **Option B: Manual Canary (without Flagger)**

More control, requires manual intervention.

#### **Step 1: Deploy Canary**

```bash
# Apply manual canary manifests
kubectl apply -f k8s/canary/manual-canary.yaml

# Verify canary pods are running
kubectl get pods -n astra-production -l version=canary

# Check canary readiness
kubectl get pods -n astra-production \
  -l version=canary \
  -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'
```

#### **Step 2: Test Canary Directly**

```bash
# Port-forward to canary pod
kubectl port-forward -n astra-production \
  deployment/astra-core-canary 8002:8001

# Run health checks
curl http://localhost:8002/live
curl http://localhost:8002/ready
curl http://localhost:8002/health/full

# Test /answer endpoint
curl -X POST http://localhost:8002/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"test canary deployment","max_tokens":100}'

# Check metrics
curl http://localhost:8002/metrics
```

#### **Step 3: Route 10% Traffic to Canary**

**Option 3a: Using Istio VirtualService**

```bash
# Already configured in manual-canary.yaml
# Verify VirtualService
kubectl get virtualservice astra-core -n astra-production -o yaml

# Test with canary header
curl -H "x-canary: true" http://astra-core:8001/live
```

**Option 3b: Using Replica Count (Simple)**

```bash
# Current: 3 stable + 1 canary = 25% canary traffic
# For 10%: 9 stable + 1 canary

kubectl scale deployment astra-core-stable \
  --replicas=9 -n astra-production
```

#### **Step 4: Monitor Canary Metrics (10 minutes)**

```bash
# Watch Prometheus metrics
# Check Grafana dashboard: "ASTRA Core Production Metrics"

# Query canary success rate
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Open http://localhost:9090 and run:
sum(rate(astra_requests_total{version="canary"}[5m])) - 
sum(rate(astra_errors_total{version="canary"}[5m])) /
sum(rate(astra_requests_total{version="canary"}[5m])) * 100

# Query canary P95 latency
histogram_quantile(0.95,
  sum(rate(astra_request_duration_seconds_bucket{version="canary"}[5m])) by (le)
) * 1000

# Compare with stable
# Canary vs Stable success rate should be within 1%
# Canary vs Stable P95 latency should be within 10%
```

#### **Step 5: Gradual Traffic Increase**

**Wait 10 minutes between each step, monitoring metrics**

```bash
# 25% canary traffic (3 stable + 1 canary)
kubectl scale deployment astra-core-stable --replicas=3 -n astra-production
kubectl scale deployment astra-core-canary --replicas=1 -n astra-production

# Wait 10 min, check metrics...

# 50% canary traffic (1 stable + 1 canary)
kubectl scale deployment astra-core-stable --replicas=1 -n astra-production
kubectl scale deployment astra-core-canary --replicas=1 -n astra-production

# Wait 10 min, check metrics...

# 75% canary traffic (1 stable + 3 canary)
kubectl scale deployment astra-core-stable --replicas=1 -n astra-production
kubectl scale deployment astra-core-canary --replicas=3 -n astra-production

# Wait 10 min, check metrics...

# 100% canary traffic
kubectl scale deployment astra-core-stable --replicas=0 -n astra-production
kubectl scale deployment astra-core-canary --replicas=3 -n astra-production
```

#### **Step 6: Promote Canary to Stable**

```bash
# Update stable deployment with canary image
kubectl set image deployment/astra-core-stable \
  astra-core=astra-core:v1.1.0 \
  -n astra-production

# Scale stable back up
kubectl scale deployment astra-core-stable --replicas=3 -n astra-production

# Wait for stable pods to be ready
kubectl rollout status deployment/astra-core-stable -n astra-production

# Remove canary deployment
kubectl scale deployment astra-core-canary --replicas=0 -n astra-production

# Or delete canary deployment
kubectl delete deployment astra-core-canary -n astra-production
```

---

## 🚨 Rollback Procedures

### **Immediate Rollback (if critical issue detected)**

```bash
# Scale canary to 0
kubectl scale deployment astra-core-canary --replicas=0 -n astra-production

# Scale stable to full capacity
kubectl scale deployment astra-core-stable --replicas=3 -n astra-production

# Or if using Flagger
kubectl delete canary astra-core -n astra-production
kubectl rollout undo deployment/astra-core -n astra-production
```

### **Rollback Triggers**

- ❌ Success rate drops below 99%
- ❌ P95 latency exceeds 2500ms
- ❌ Error rate increases by >1%
- ❌ Circuit breaker trips increase
- ❌ Memory/CPU usage spikes unexpectedly
- ❌ Customer reports or alerts triggered

---

## 📊 Validation Checklist

### **Pre-Deployment**
- [ ] Staging tests passed
- [ ] Docker image scanned for vulnerabilities
- [ ] Database migrations (if any) tested
- [ ] Feature flags configured
- [ ] Monitoring dashboards ready

### **During Canary (each traffic increase)**
- [ ] Success rate ≥ 99%
- [ ] P95 latency < 2500ms
- [ ] Error rate < 1%
- [ ] No circuit breaker trips
- [ ] Memory usage stable
- [ ] CPU usage within limits
- [ ] No unusual logs/errors

### **Post-Deployment**
- [ ] All pods healthy
- [ ] Metrics looking good for 30+ minutes
- [ ] No customer complaints
- [ ] Logs reviewed
- [ ] Documentation updated
- [ ] Canary deployment cleaned up

---

## 📈 Monitoring Queries

### **Prometheus Queries**

```promql
# Success Rate Comparison
sum(rate(astra_requests_total{version="canary"}[5m])) by (version)

# Latency Comparison (P95)
histogram_quantile(0.95,
  sum(rate(astra_request_duration_seconds_bucket[5m])) by (version, le)
) * 1000

# Error Rate
rate(astra_errors_total[5m])

# Queue Depth
astra_queue_depth_avg{version="canary"}

# Circuit Breaker Trips
increase(astra_circuit_breaker_trips_total{version="canary"}[10m])
```

### **Grafana Alerts**

Create alerts in Grafana:

1. **High Canary Error Rate**
   - `rate(astra_errors_total{version="canary"}[5m]) > 0.01`
   - Severity: Critical
   - Action: Page on-call

2. **High Canary Latency**
   - `histogram_quantile(0.95, rate(astra_request_duration_seconds_bucket{version="canary"}[5m])) > 2.5`
   - Severity: Warning
   - Action: Notify team

3. **Canary Circuit Breaker**
   - `increase(astra_circuit_breaker_trips_total{version="canary"}[5m]) > 0`
   - Severity: Critical
   - Action: Auto-rollback

---

## 🔍 Troubleshooting

### **Issue: Canary pods not starting**

```bash
# Check pod status
kubectl describe pod -n astra-production -l version=canary

# Check events
kubectl get events -n astra-production --sort-by='.lastTimestamp'

# Check logs
kubectl logs -n astra-production -l version=canary --tail=100
```

### **Issue: High error rate in canary**

```bash
# Get detailed logs
kubectl logs -n astra-production -l version=canary -f | grep ERROR

# Check specific error patterns
kubectl logs -n astra-production -l version=canary | jq 'select(.level=="error")'

# Compare with stable
kubectl logs -n astra-production -l version=stable | grep ERROR | wc -l
```

### **Issue: Traffic not routing to canary**

```bash
# Check service endpoints
kubectl get endpoints astra-core -n astra-production

# Check VirtualService (if using Istio)
kubectl get virtualservice astra-core -n astra-production -o yaml

# Test direct canary access
kubectl port-forward -n astra-production deployment/astra-core-canary 8002:8001
curl http://localhost:8002/live
```

---

## 📝 Communication Template

### **Pre-Deployment Announcement**

```
Subject: ASTRA Core v1.1.0 Canary Deployment Starting

Team,

Starting canary deployment of ASTRA Core v1.1.0 at [TIME].

Changes:
- [Feature 1]
- [Feature 2]
- [Bug Fix 1]

Rollout Plan:
- 10% traffic for 10 minutes
- Gradual increase to 50% over 30 minutes
- Full promotion if metrics look good

Monitoring: [Link to Grafana Dashboard]
War Room: [Slack Channel]

-- [Your Name]
```

### **Post-Deployment Summary**

```
Subject: ASTRA Core v1.1.0 Successfully Deployed

Team,

ASTRA Core v1.1.0 canary deployment completed successfully.

Results:
✅ Success Rate: 99.8% (target: >99%)
✅ P95 Latency: 110ms (target: <2500ms)
✅ Zero incidents
✅ All health checks passing

Timeline:
- 14:00 - Canary deployed (10% traffic)
- 14:30 - Increased to 50% traffic
- 15:00 - Promoted to 100%

-- [Your Name]
```

---

## 📚 References

- [Flagger Documentation](https://docs.flagger.app/)
- [Kubernetes Progressive Delivery](https://kubernetes.io/blog/2020/05/29/progressive-delivery-on-kubernetes/)
- [Canary Deployments Best Practices](https://cloud.google.com/blog/products/devops-sre/canary-analysis-lessons-from-trenches)
- ASTRA Core Production Runbooks: `docs/runbooks/`

---

**Last Updated**: 2025-11-01  
**Next Review**: After each canary deployment
