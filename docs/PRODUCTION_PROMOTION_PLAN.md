# 🚀 ASTRA Core - Production Promotion Plan

**Purpose**: Full production promotion procedures with rollback criteria  
**Audience**: DevOps, SRE, Engineering Team  
**Status**: ACTIVE

---

## 📋 Overview

This document defines the complete production promotion process for ASTRA Core, including:
- Pre-promotion validation
- Promotion execution
- Post-promotion monitoring
- Rollback procedures
- Success criteria

---

## 🎯 Promotion Criteria

Before promoting to production, ALL criteria must be met:

### **Technical Validation**
- ✅ All unit tests passing (100% coverage on critical paths)
- ✅ All integration tests passing
- ✅ Load tests passed with P95 < 2500ms
- ✅ Security scan completed (no critical/high vulnerabilities)
- ✅ Staging environment stable for 24+ hours
- ✅ Canary deployment successful (if applicable)

### **Operational Readiness**
- ✅ Monitoring dashboards configured
- ✅ Alerts configured and tested
- ✅ Runbooks updated
- ✅ Team trained on new features
- ✅ Rollback plan documented and rehearsed
- ✅ Communication plan prepared

### **Business Approval**
- ✅ Product owner sign-off
- ✅ Change request approved
- ✅ Maintenance window scheduled (if required)
- ✅ Customer communication sent (if customer-facing changes)

---

## 🚦 Promotion Phases

### **Phase 1: Pre-Promotion (T-24h)**

#### **1.1 Final Validation**

```bash
# Run full test suite
cd tests/
pytest --cov=astra_core --cov-report=html

# Run load tests
python tools/simple_load_test.py http://staging-astra-core:8001

# Validate staging metrics
python tools/check_metrics.py http://staging-astra-core:8001

# Security scan
trivy image astra-core:v1.1.0 --severity HIGH,CRITICAL

# Verify Docker image
docker pull astra-core:v1.1.0
docker inspect astra-core:v1.1.0
```

#### **1.2 Backup Current Production**

```bash
# Backup production configuration
kubectl get deployment astra-core -n astra-production -o yaml > \
  backups/astra-core-deployment-$(date +%Y%m%d-%H%M%S).yaml

# Backup production data (if applicable)
kubectl exec -n astra-production deployment/astra-core -- \
  /app/backup.sh > backups/astra-core-data-$(date +%Y%m%d-%H%M%S).tar.gz

# Backup database (if applicable)
pg_dump -h prod-db -U astra -d astra_db > \
  backups/astra-db-$(date +%Y%m%d-%H%M%S).sql
```

#### **1.3 Prepare Rollback**

```bash
# Tag current production as rollback candidate
kubectl label deployment astra-core \
  rollback=v1.0.0 \
  -n astra-production

# Create rollback script
cat > rollback.sh << 'EOF'
#!/bin/bash
echo "Rolling back ASTRA Core to v1.0.0..."
kubectl set image deployment/astra-core \
  astra-core=astra-core:v1.0.0 \
  -n astra-production
kubectl rollout status deployment/astra-core -n astra-production
echo "Rollback complete!"
EOF
chmod +x rollback.sh
```

#### **1.4 Communication**

```bash
# Send pre-promotion notification
# Subject: ASTRA Core v1.1.0 Production Deployment Tomorrow

Team,

ASTRA Core v1.1.0 will be deployed to production tomorrow at [TIME].

Changes:
- [List major changes]

Impact:
- Expected downtime: None (rolling update)
- Traffic routing: Canary deployment (10% → 100%)

Monitoring:
- Dashboard: [Link]
- Alerts: [Slack Channel]
- War Room: [Zoom Link]

Please review and acknowledge.
```

---

### **Phase 2: Promotion Execution (T0)**

#### **2.1 Pre-Flight Checks**

```bash
# Verify production is healthy
kubectl get pods -n astra-production
kubectl top nodes
kubectl top pods -n astra-production

# Check current metrics
curl http://astra-core.prod/metrics | grep -E "(error|latency|uptime)"

# Verify monitoring is working
curl http://prometheus.prod/api/v1/query?query=up{job="astra-core"}

# Test rollback script
./rollback.sh --dry-run
```

#### **2.2 Enable Maintenance Mode (Optional)**

If zero-downtime is not guaranteed:

```bash
# Enable maintenance page
kubectl apply -f k8s/maintenance/maintenance-page.yaml

# Wait for traffic to drain
sleep 30

# Verify no active requests
kubectl exec -n astra-production deployment/astra-core -- \
  curl http://localhost:8001/metrics | grep "requests_in_progress"
```

#### **2.3 Execute Deployment**

**Option A: Canary Deployment (Recommended)**

```bash
# Use the canary runbook
# See: docs/CANARY_DEPLOYMENT_RUNBOOK.md

# Deploy canary
kubectl apply -f k8s/canary/manual-canary.yaml

# Monitor canary for 10 minutes
kubectl get pods -n astra-production -l version=canary -w

# Gradually increase traffic
# 10% → 25% → 50% → 75% → 100%

# Promote to stable
kubectl set image deployment/astra-core-stable \
  astra-core=astra-core:v1.1.0 \
  -n astra-production
```

**Option B: Rolling Update (Fast)**

```bash
# Update image
kubectl set image deployment/astra-core \
  astra-core=astra-core:v1.1.0 \
  -n astra-production

# Watch rollout
kubectl rollout status deployment/astra-core -n astra-production

# Verify new pods
kubectl get pods -n astra-production -l app=astra-core
```

**Option C: Blue/Green Deployment (Zero Downtime)**

```bash
# Deploy green environment
kubectl apply -f k8s/blue-green/green-deployment.yaml

# Wait for green to be ready
kubectl wait --for=condition=available \
  deployment/astra-core-green \
  -n astra-production \
  --timeout=300s

# Switch traffic to green
kubectl patch service astra-core -n astra-production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Monitor for 5 minutes
# If successful, delete blue
kubectl delete deployment astra-core-blue -n astra-production
```

#### **2.4 Smoke Tests**

```bash
# Health checks
curl http://astra-core.prod/live
curl http://astra-core.prod/ready
curl http://astra-core.prod/health/full

# Functional test
curl -X POST http://astra-core.prod/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"production smoke test","max_tokens":100}'

# Load test (light)
for i in {1..10}; do
  curl -X POST http://astra-core.prod/answer \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"test $i\",\"max_tokens\":50}" &
done
wait

# Check metrics
python tools/check_metrics.py http://astra-core.prod
```

#### **2.5 Disable Maintenance Mode**

```bash
# Remove maintenance page
kubectl delete -f k8s/maintenance/maintenance-page.yaml

# Verify traffic is flowing
curl http://astra-core.prod/metrics | grep "requests_total"
```

---

### **Phase 3: Post-Promotion Monitoring (T+0 to T+2h)**

#### **3.1 Immediate Monitoring (T+0 to T+15m)**

```bash
# Watch logs for errors
kubectl logs -n astra-production -l app=astra-core -f --tail=100 | grep -E "(ERROR|CRITICAL)"

# Monitor metrics in real-time
watch -n 5 'curl -s http://astra-core.prod/metrics | grep -E "(error|latency|uptime)"'

# Check Grafana dashboard
open https://grafana.prod/d/astra-core-production

# Monitor alerts
# Check Slack/PagerDuty for any triggered alerts
```

**Key Metrics to Watch:**
- ✅ Success rate ≥ 99%
- ✅ P95 latency < 2500ms
- ✅ Error rate < 1%
- ✅ No circuit breaker trips
- ✅ Memory/CPU within normal range
- ✅ Request rate matches historical patterns

#### **3.2 Extended Monitoring (T+15m to T+2h)**

```bash
# Generate hourly report
python tools/generate_health_report.py \
  --start="15 minutes ago" \
  --end=now \
  > reports/promotion-t15m-health.txt

# Compare with baseline
python tools/compare_metrics.py \
  --baseline=v1.0.0 \
  --current=v1.1.0 \
  --window=15m

# Check customer impact
# Review support tickets, user reports, social media
```

#### **3.3 Success Confirmation**

After 2 hours of stable operation:

```bash
# Generate promotion report
python tools/generate_promotion_report.py \
  --version=v1.1.0 \
  --start="2 hours ago" \
  > reports/promotion-v1.1.0-success.md

# Send success notification
# Subject: ASTRA Core v1.1.0 Production Deployment Successful
```

---

## 🚨 Rollback Procedures

### **Rollback Decision Tree**

```
Is the issue critical?
├─ YES: Immediate rollback
│   ├─ Success rate < 95%
│   ├─ P95 latency > 5000ms
│   ├─ Multiple circuit breaker trips
│   ├─ Production outage
│   └─ Data corruption
│
└─ NO: Evaluate severity
    ├─ Can it be hotfixed in < 30 min? → Hotfix
    ├─ Does it impact < 5% users? → Monitor closely
    └─ Otherwise → Rollback
```

### **Immediate Rollback (< 5 minutes)**

```bash
# Execute rollback script
./rollback.sh

# Or manually
kubectl rollout undo deployment/astra-core -n astra-production

# Verify rollback
kubectl rollout status deployment/astra-core -n astra-production

# Confirm with smoke test
curl http://astra-core.prod/live
python tools/check_metrics.py http://astra-core.prod

# Send rollback notification
# Subject: ASTRA Core v1.1.0 Rolled Back - v1.0.0 Restored
```

### **Rollback from Canary**

```bash
# Scale canary to 0
kubectl scale deployment astra-core-canary --replicas=0 -n astra-production

# Scale stable to full
kubectl scale deployment astra-core-stable --replicas=3 -n astra-production

# Verify traffic is 100% on stable
kubectl get pods -n astra-production
python tools/check_metrics.py http://astra-core.prod
```

### **Post-Rollback Actions**

1. **Root Cause Analysis**
   - Collect logs from failed deployment
   - Review metrics during incident
   - Identify what went wrong

2. **Fix and Re-Test**
   - Apply fixes to v1.1.1
   - Re-run full test suite
   - Deploy to staging

3. **Reschedule Promotion**
   - Review lessons learned
   - Update promotion plan
   - Schedule new promotion window

---

## ✅ Success Criteria

Promotion is considered successful when ALL criteria are met for 2 hours:

### **Performance Metrics**
- ✅ Success rate ≥ 99%
- ✅ P95 latency < 2500ms
- ✅ P99 latency < 5000ms
- ✅ Error rate < 1%
- ✅ Request throughput ≥ baseline

### **Reliability Metrics**
- ✅ Zero circuit breaker trips
- ✅ Zero pod crashes/restarts
- ✅ Memory usage < 80% limit
- ✅ CPU usage < 70% limit
- ✅ Disk usage < 80%

### **Business Metrics**
- ✅ Zero critical support tickets
- ✅ Zero customer escalations
- ✅ No negative social media mentions
- ✅ Response time SLA met (99th percentile)

---

## 📊 Promotion Checklist

### **Pre-Promotion (T-24h)**
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Staging validated
- [ ] Backups created
- [ ] Rollback script tested
- [ ] Communication sent
- [ ] Team briefed
- [ ] Monitoring configured

### **During Promotion (T0)**
- [ ] Pre-flight checks completed
- [ ] Maintenance mode enabled (if needed)
- [ ] Deployment executed
- [ ] Smoke tests passed
- [ ] Maintenance mode disabled
- [ ] Initial monitoring started

### **Post-Promotion (T+0 to T+2h)**
- [ ] Immediate monitoring (15 min) passed
- [ ] Extended monitoring (2 hours) passed
- [ ] Success criteria met
- [ ] Promotion report generated
- [ ] Team notified
- [ ] Documentation updated

---

## 📝 Communication Templates

### **Pre-Promotion Email**

```
Subject: ASTRA Core v1.1.0 Production Deployment - [DATE] [TIME]

Team,

This is a reminder that ASTRA Core v1.1.0 will be deployed to production:

Date: [DATE]
Time: [TIME] [TIMEZONE]
Duration: ~30-60 minutes
Method: Canary deployment (zero downtime)

Changes:
- [Feature 1]
- [Feature 2]
- [Bug Fix 1]

Monitoring:
- Dashboard: https://grafana.prod/d/astra-core
- Alerts: #astra-prod-alerts Slack channel
- War Room: [Zoom Link]

Rollback Plan:
- Automated rollback if success rate < 99%
- Manual rollback available within 5 minutes

Please acknowledge receipt and join the war room during deployment.

Thanks,
[Your Name]
```

### **Success Email**

```
Subject: ✅ ASTRA Core v1.1.0 Production Deployment Successful

Team,

ASTRA Core v1.1.0 has been successfully deployed to production.

Deployment Timeline:
- 14:00 - Deployment started
- 14:10 - Canary at 10% traffic
- 14:30 - Canary at 50% traffic
- 14:50 - Promoted to 100%
- 16:50 - 2 hours of stable operation confirmed

Key Metrics:
✅ Success Rate: 99.8% (target: >99%)
✅ P95 Latency: 120ms (target: <2500ms)
✅ Error Rate: 0.1% (target: <1%)
✅ Zero incidents

Thank you for your support!

[Your Name]
```

### **Rollback Email**

```
Subject: 🚨 ASTRA Core v1.1.0 Rolled Back - v1.0.0 Restored

Team,

ASTRA Core v1.1.0 has been rolled back to v1.0.0 due to [REASON].

Incident Timeline:
- 14:00 - v1.1.0 deployment started
- 14:15 - Issue detected: [DESCRIPTION]
- 14:20 - Rollback initiated
- 14:25 - v1.0.0 restored and stable

Impact:
- Duration: 25 minutes
- Affected Requests: ~1,500 (estimated)
- Customer Impact: [LOW/MEDIUM/HIGH]

Next Steps:
1. Root cause analysis scheduled for [TIME]
2. Fix will be prepared for v1.1.1
3. Re-deployment scheduled for [DATE]

Postmortem: [Link to document]

[Your Name]
```

---

## 📚 References

- Canary Deployment Runbook: `docs/CANARY_DEPLOYMENT_RUNBOOK.md`
- Monitoring Playbook: `docs/MONITORING_PLAYBOOK.md`
- Incident Response: `docs/INCIDENT_RESPONSE.md`
- SLO/SLA Documentation: `docs/SLO_SLA.md`

---

**Last Updated**: 2025-11-01  
**Version**: 1.0  
**Owner**: DevOps Team
