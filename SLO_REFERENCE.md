# ASTRA Service Level Objectives (SLOs) & Error Budgets

**Last Updated:** October 16, 2025  
**Review Cadence:** Monthly

---

## 🎯 SLO Targets

### Bridge Service

| Metric | Target | Measurement Window | Budget/30d |
|--------|--------|-------------------|------------|
| **Availability** | 99.5% | 30 days | 216.0 minutes |
| **P95 Latency** | < 500ms | 30 days | - |
| **P99 Latency** | < 1s | 30 days | - |
| **Error Rate** | < 0.5% | 30 days | - |

### Docs Service

| Metric | Target | Measurement Window | Budget/30d |
|--------|--------|-------------------|------------|
| **Availability** | 99.5% | 30 days | 216.0 minutes |
| **Ingest Success** | > 95% | 30 days | - |
| **Search P95 Latency** | < 2s | 30 days | - |

### Qdrant

| Metric | Target | Measurement Window | Budget/30d |
|--------|--------|-------------------|------------|
| **Availability** | 99.9% | 30 days | 43.2 minutes |

---

## 📊 Error Budget Reference

### Availability Tiers

| SLO | Max Downtime/30d | Max Downtime/Day | Budget % |
|-----|------------------|------------------|----------|
| 99.99% | 4.32 minutes | 8.6 seconds | 0.01% |
| 99.95% | 21.6 minutes | 43 seconds | 0.05% |
| **99.9%** | **43.2 minutes** | **86 seconds** | **0.1%** |
| **99.5%** | **216.0 minutes** | **7.2 minutes** | **0.5%** |
| 99.0% | 432.0 minutes | 14.4 minutes | 1.0% |

**ASTRA Standard:** 99.5% (3.6 hours/month downtime budget)

---

## 🔥 Error Budget Burn Rate

### Burn Rate Thresholds

| Burn Rate | Budget Exhausted In | Action Required |
|-----------|---------------------|-----------------|
| **36x** | 20 hours | 🚨 CRITICAL - Immediate rollback |
| **10x** | 3 days | 🔴 Page on-call, investigate |
| **3x** | 10 days | 🟡 High priority fix |
| **1x** | 30 days | 🟢 Normal operation |
| **0.5x** | 60 days | 🟢 Under budget |

### Prometheus Query (1-hour burn)

```promql
# 1-hour error budget burn rate
sum_over_time((1 - clamp_max(
  sum(rate(bridge_calls_total{status="error"}[5m]))
  / clamp_min(sum(rate(bridge_calls_total[5m])), 1), 1)
)[1h:5m]) < 0.95
```

**Interpretation:**
- `< 0.95` = Burned >5% of budget in 1 hour
- At this rate, budget exhausted in 20 hours
- Trigger: Page on-call, investigate immediately

---

## 📈 Tracking Error Budget

### Prometheus Recording Rules

```promql
# 1-hour availability
bridge:availability:1h

# 24-hour availability
bridge:availability:24h

# 30-day availability (SLO measurement)
bridge:availability:30d

# Error budget remaining
bridge:error_budget_remaining:30d
```

### Grafana Dashboard Panels

**Panel 1: Current Availability (30d)**
```promql
bridge:availability:30d * 100
```
Display: Stat panel with thresholds (99.5% = green)

**Panel 2: Error Budget Remaining**
```promql
bridge:error_budget_remaining:30d * 100
```
Display: Gauge (0% = red, 100% = green)

**Panel 3: Burn Rate (1h)**
```promql
(0.005 - (1 - bridge:availability:1h)) / 0.005
```
Display: Graph with threshold at 1x (normal burn)

---

## 🚦 Operational Guidelines

### Budget Allocation

**Planned maintenance:** 30% of budget (64.8 min/month)  
**Unplanned incidents:** 50% of budget (108 min/month)  
**Reserve:** 20% of budget (43.2 min/month)

### Cutover Windows

Each cutover consumes error budget:

| Cutover Type | Estimated Budget | Frequency Limit |
|--------------|------------------|-----------------|
| **Rolling update** | 5-10 minutes | 10-20/month |
| **Blue/Green** | 2-5 minutes | 20-40/month |
| **Hotfix** | 10-15 minutes | 5-10/month |

**Policy:** No more than 3 cutovers/week to preserve budget.

### When Budget is Low (<20%)

- ❌ **STOP** all non-critical deployments
- ❌ **DEFER** feature rollouts to next month
- ✅ **ALLOW** only critical security/bug fixes
- ✅ **USE** Blue/Green deployment exclusively
- ✅ **EXTEND** monitoring to 4-hour post-cutover

### When Budget is Exhausted (0%)

- 🚨 **FREEZE** all changes
- 🚨 **INCIDENT** declared automatically
- 🚨 **REVIEW** required before next deployment
- 📊 **POSTMORTEM** mandatory with action items

---

## 📋 Monthly SLO Review Checklist

**Review Date:** _______________  
**Participants:** _______________

- [ ] Measure 30-day availability: _____ %
- [ ] Compare to target (99.5%): [ ] Met / [ ] Missed
- [ ] Error budget consumed: _____ % (should be ≤100%)
- [ ] Number of incidents: _____
- [ ] Longest incident: _____ minutes
- [ ] Planned maintenance: _____ minutes
- [ ] Unplanned downtime: _____ minutes
- [ ] Cutover count: _____
- [ ] Review burn rate alerts: [ ] Fired / [ ] Clean
- [ ] Action items from misses: _____
- [ ] Budget allocation for next month: _____

**Next Review:** _______________

---

## 🎯 SLI Definitions (How We Measure)

### Availability SLI

**Definition:** Percentage of successful requests

**Formula:**
```
Availability = (Total Requests - Error Requests) / Total Requests
```

**Prometheus:**
```promql
1 - clamp_max(
  sum(rate(bridge_calls_total{status="error"}[30d]))
  / clamp_min(sum(rate(bridge_calls_total[30d])), 1), 1)
```

**Exclusions:**
- Client errors (4xx except 429)
- Requests during planned maintenance windows
- Health check probes

**Inclusions:**
- 5xx errors (server errors)
- Timeouts (>30s)
- Rate limit rejections (429)

### Latency SLI

**Definition:** P95 of successful request latency

**Formula:**
```
P95 Latency = 95th percentile of response times
```

**Prometheus:**
```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(bridge_call_duration_seconds_bucket{status="success"}[30d]))
)
```

**Measurement:** Only successful requests (2xx, 3xx)

---

## 🔍 Troubleshooting High Burn Rate

### Immediate Actions

1. **Check Grafana** - Identify error spike time
2. **Check Recent Deploys** - Correlate with cutover
3. **Check Logs** - Look for error patterns
4. **Check Dependencies** - LLM, Qdrant, DB health

### Common Causes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Spike in 5xx errors | Bad deployment | Rollback immediately |
| Gradual error increase | Resource exhaustion | Scale up, check memory/CPU |
| Timeout errors | Downstream latency | Check LLM/Qdrant, add capacity |
| All errors at once | Service down | Restart pods, check ingress |

### Burn Rate Alert Response

**Alert fires:** `BridgeErrorBudgetBurnHigh`

1. **T+0 min** - Acknowledge alert, check Grafana
2. **T+5 min** - Identify root cause
3. **T+10 min** - Execute fix (rollback or scale)
4. **T+15 min** - Verify burn rate decreasing
5. **T+30 min** - Post-incident review

**If burn rate continues:** Escalate to engineering lead.

---

## 📞 Contact & Escalation

| Role | Contact | Escalation Threshold |
|------|---------|---------------------|
| **On-Call SRE** | PagerDuty | Burn rate >10x |
| **Engineering Lead** | Slack DM | Budget <10% remaining |
| **VP Engineering** | Phone | SLO miss (end of month) |

**Slack Channels:**
- **#sre-oncall** - Real-time burn rate monitoring
- **#astra-slo** - Monthly reviews and reports

---

## 📚 References

- **Error Budget Math:** https://sre.google/workbook/implementing-slos/
- **Burn Rate Alerts:** https://sre.google/workbook/alerting-on-slos/
- **ASTRA Runbook:** `CUTOVER_QUICK_REF.md`
- **Grafana Dashboard:** https://grafana.example.com/d/astra-ops

---

**Remember:** Error budgets exist to be spent! Use them to ship features, but spend wisely. 🎯

