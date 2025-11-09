# 🎯 ASTRA Core - Quick Reference Card

**Version**: v1.0.0  
**Status**: ✅ PRODUCTION READY  
**Date**: 2025-11-01

---

## 🚀 Quick Start

```bash
# Start ASTRA Core
python astra_core.py

# Check Health
curl http://localhost:8001/live
curl http://localhost:8001/ready
curl http://localhost:8001/health/full

# View Metrics
python tools/check_metrics.py

# Test Rate Limiting
python tools/test_rate_limiting.py

# Run Load Test
python simple_load_test.py
```

---

## 📊 Key Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Success Rate | 100% | ≥99% | ✅ |
| P95 Latency | 110ms | <2500ms | ✅ |
| Error Rate | 0% | <1% | ✅ |
| Uptime | 100% | ≥99.9% | ✅ |

---

## 🔧 Key Features

- ✅ **Rate Limiting**: Token bucket, per-endpoint limits
- ✅ **Metrics**: Prometheus OpenMetrics 0.0.4 format
- ✅ **Health Checks**: /live, /ready, /health/full
- ✅ **SSE Streaming**: With backpressure handling
- ✅ **Circuit Breakers**: Automatic failure detection
- ✅ **Load Testing**: Async with latency percentiles

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `ENHANCEMENT_01_PROMETHEUS_METRICS.md` | Metrics implementation guide |
| `CANARY_DEPLOYMENT_RUNBOOK.md` | Deployment procedures |
| `PRODUCTION_PROMOTION_PLAN.md` | Full promotion process |
| `BACKUP_AND_SECURITY.md` | Security & DR procedures |
| `PRODUCTION_READINESS_COMPLETE.md` | Executive summary |

---

## 🚦 Deployment Commands

```bash
# Canary Deployment
kubectl apply -f k8s/canary/canary-deployment.yaml

# Manual Canary
kubectl apply -f k8s/canary/manual-canary.yaml

# Check Canary Status
kubectl get pods -n astra-production -l version=canary

# Promote Canary
kubectl set image deployment/astra-core-stable \
  astra-core=astra-core:v1.1.0 -n astra-production

# Rollback
./rollback.sh
```

---

## 🔒 Security Checklist

- [x] Rate limiting active
- [x] Secrets encrypted
- [x] TLS enabled
- [x] Backups automated
- [x] DR tested
- [x] Compliance docs ready

---

## 📞 Emergency Contacts

- **DevOps**: #astra-devops
- **SRE On-Call**: PagerDuty
- **Security**: security@company.com

---

## 🎯 Quick Commands

```bash
# Check server status
curl http://localhost:8001/live

# View current metrics
curl http://localhost:8001/metrics

# Test endpoint
curl -X POST http://localhost:8001/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"test","max_tokens":100}'

# Check logs
kubectl logs -n astra-production -l app=astra-core --tail=50

# Scale deployment
kubectl scale deployment astra-core --replicas=5 -n astra-production

# Get pod status
kubectl get pods -n astra-production -l app=astra-core
```

---

**Last Updated**: 2025-11-01  
**Maintained By**: DevOps Team
