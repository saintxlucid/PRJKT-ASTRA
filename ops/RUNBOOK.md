# ASTRA CORE v1.0 - Production Runbook

**Last Updated:** October 16, 2025  
**Status:** Production Ready ✅  
**Maintainer:** Saint Lucid

---

## 🚀 Quick Start (30 Seconds)

### Start Services

```powershell
# Terminal 1: Start llama.cpp server
cd X:\PROJECT_ASTRA_1.0
.\scripts\start_gptoss_server.ps1

# Terminal 2: Start ASTRA API
cd X:\PROJECT_ASTRA_1.0
.\LAUNCH_ASTRA.ps1
```

### Verify Health

```powershell
.\scripts\smoke_test.ps1
```

**Expected:** All 5 checks pass ✅

---

## 📊 Health Checks

### Manual Health Check

```powershell
# LLM Server
curl -fsS http://localhost:8001/health

# API Server
curl -fsS http://localhost:8080/v1/system/health

# Bridge Module
curl -fsS http://localhost:8080/v1/bridge/healthz

# Metrics
curl -fsS http://localhost:8080/metrics | Select-String "astra_"
```

### Expected Response (API Health)

```json
{
  "status": "healthy",
  "components": {
    "database": {"ok": true},
    "memory": {"ok": true, "count": 21000},
    "llm": {"ok": true, "latency_ms": 150}
  },
  "version": "2.0.0"
}
```

---

## 🔧 Common Operations

### Rotate API Keys

```powershell
# Generate new key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
# ASTRA_API_KEYS=old_key,new_key

# Restart API server
# Clients can migrate to new key
# Remove old key from .env when done
```

### Clear Semantic Cache

```powershell
curl -X DELETE http://localhost:8080/v1/cache \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Backup Data

```powershell
.\scripts\backup_production.ps1
```

**Creates:** `data/backups/astra_backup_YYYYMMDD_HHMMSS.zip`

### Check Memory Stats

```python
from src.astra.core.memory_engine import get_memory_engine

engine = get_memory_engine()
stats = engine.get_memory_stats()
print(f"Semantic: {stats['semantic']}")
print(f"Episodic: {stats['episodic']}")
print(f"Procedural: {stats['procedural']}")
```

---

## 🚨 Troubleshooting

### Issue: LLM Calls Timing Out

**Symptoms:** 503 errors, circuit breaker open

**Diagnosis:**
```powershell
# Check llama.cpp
curl http://localhost:8001/health

# Check circuit breaker state
curl http://localhost:8080/v1/system/health | jq '.components.llm.circuit_breaker'
```

**Resolution:**
1. Restart llama.cpp server
2. Wait 30s for circuit breaker to close
3. Verify: `.\scripts\smoke_test.ps1`

### Issue: High Memory Usage

**Symptoms:** API slow, memory > 4GB

**Diagnosis:**
```powershell
# Check metrics
curl http://localhost:8080/metrics | Select-String "process_resident_memory"

# Check cache stats
curl http://localhost:8080/v1/cache/stats
```

**Resolution:**
1. Clear semantic cache
2. Restart API if memory doesn't drop
3. Check for memory leaks in logs

### Issue: Rate Limit Blocking Users

**Symptoms:** Many 429 responses

**Diagnosis:**
```powershell
# Check rate limit metrics
curl http://localhost:8080/metrics | Select-String "astra_limiter_per_key_blocked"
```

**Resolution:**
```powershell
# Increase limits in .env
# ASTRA_RATE_LIMIT_REQUESTS=240  # was 120
# ASTRA_RATE_LIMIT_WINDOW=60

# Restart API server
```

### Issue: BGE-M3 Migration Blocked

**Symptoms:** Disk space error during re-embed

**Resolution:**
```powershell
# Clear temp files
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Temp\*"
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\pip\*"
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\*.tmp"

# Verify space (need ~3GB free)
Get-PSDrive C

# Run migration
.\scripts\reembed_bge_m3.ps1
```

---

## 📈 Monitoring

### Key Metrics to Watch

| Metric | Target | Alert |
|--------|--------|-------|
| **API p95 Latency** | ≤ 1.2s | > 1.2s for 5m |
| **LLM p95 Latency** | ≤ 1.5s | > 1.5s for 5m |
| **Error Rate** | < 1% | > 5% for 3m |
| **Queue Depth** | < 32 | > 32 for 2m |
| **Memory Usage** | < 4GB | > 4GB for 5m |
| **Cache Hit Ratio** | > 20% | < 10% for 10m |

### Prometheus Queries

```promql
# Request rate
rate(astra_requests_total[5m])

# Error rate
sum(rate(astra_requests_total{status=~"5.."}[5m])) 
  / sum(rate(astra_requests_total[5m]))

# p95 latency
histogram_quantile(0.95, 
  sum(rate(astra_request_duration_seconds_bucket[5m])) by (le))

# Cache hit ratio
sum(rate(astra_cache_hits_total[5m])) 
  / (sum(rate(astra_cache_hits_total[5m])) 
     + sum(rate(astra_cache_misses_total[5m])))
```

### Alert Setup

```yaml
# Add to Prometheus config
rule_files:
  - "ops/prometheus/astra_alerts.yml"

# Reload config
curl -X POST http://localhost:9090/-/reload
```

---

## 🔒 Security Checklist

- [ ] API keys rotated every 90 days
- [ ] `.env` file not in version control
- [ ] CORS restricted to known origins
- [ ] Swagger disabled in production (`ASTRA_ENVIRONMENT=production`)
- [ ] Rate limits tuned for expected load
- [ ] Logs sanitized (no API keys, secrets)

---

## 📦 Deployment Checklist

### Pre-Deploy

- [ ] All tests pass: `pytest tests/ -v --cov=src/astra`
- [ ] Coverage ≥ 94%: Check coverage report
- [ ] Smoke test passes: `.\scripts\smoke_test.ps1`
- [ ] Load test passes: p95 ≤ 1.2s @ 10 RPS

### Deploy

- [ ] Tag release: `git tag v1.0.0 && git push --tags`
- [ ] Update changelog
- [ ] Backup production data
- [ ] Stop old service
- [ ] Pull new code
- [ ] Run migrations (if any)
- [ ] Start new service
- [ ] Run smoke test
- [ ] Monitor metrics for 10 minutes

### Post-Deploy

- [ ] Verify health dashboard
- [ ] Check logs for errors
- [ ] Test one chat completion end-to-end
- [ ] Alert team: "ASTRA v1.0.0 deployed ✅"

---

## 📞 Escalation

### On-Call Contacts

- **Primary:** Saint Lucid
- **Slack:** #astra-alerts
- **PagerDuty:** astra-core team

### Severity Levels

- **P0 (Critical):** API down, no responses
  - **Action:** Immediate restart, notify team
  
- **P1 (High):** Error rate > 10%, LLM offline
  - **Action:** Restart LLM, check logs
  
- **P2 (Medium):** Latency SLO breach, queue backlog
  - **Action:** Monitor, tune capacity

- **P3 (Low):** Cache miss ratio low, warnings in logs
  - **Action:** Log ticket, fix in next deploy

---

## 🔄 Maintenance Windows

**Recommended:** Weekly Sunday 02:00-04:00 UTC

**Tasks:**
- Data backup
- Memory consolidation (`scripts/consolidate_memories.py`)
- Log rotation
- Security updates
- Performance tuning

---

## 📚 Reference Links

- [Architecture Documentation](../ARCHITECTURE_PRODUCTION.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE_CONSOLIDATED.md)
- [Testing Report](../TESTING_REPORT.md)
- [API Documentation](http://localhost:8080/docs) (dev only)
- [Prometheus Metrics](http://localhost:8080/metrics)
