# Incident Retrospective Template

**Incident ID**: INC-YYYYMMDD-XXX  
**Severity**: P0 / P1 / P2 / P3  
**Date/Time (UTC)**: YYYY-MM-DD HH:MM - HH:MM  
**Duration**: XX minutes / XX hours  
**Status**: RESOLVED / MITIGATED / ONGOING

---

## 1. Executive Summary (≤3 lines)

Describe the incident in plain language for non-technical stakeholders.

Example:
> On 2025-11-01 from 14:30-15:15 UTC, the Q&A service experienced elevated latency (P95 5.2s vs 2.5s SLO) affecting 12% of requests. Root cause was a database connection pool exhaustion triggered by a sudden 3× traffic spike from a new partner integration. Service was restored by increasing pool size and implementing per-client rate limiting.

---

## 2. Timeline (UTC, minute-by-minute)

| Time (UTC) | Event | Actor | Action Taken |
|------------|-------|-------|--------------|
| 14:28 | Traffic spike detected (+300%) | Monitoring | Alert fired: `traffic_anomaly` |
| 14:30 | P95 latency degraded to 4.2s | Monitoring | Alert fired: `p95_latency_breach` |
| 14:32 | SRE acknowledged alert | Alice (SRE) | Opened incident INC-20251101-001 |
| 14:35 | DB connection pool saturated | Alice (SRE) | Diagnosed via `kubectl logs` |
| 14:40 | Increased pool size 10→50 | Alice (SRE) | `kubectl set env DB_POOL_SIZE=50` |
| 14:45 | Latency improved to 3.1s | Monitoring | Partial recovery |
| 14:50 | Enabled per-client rate limiting | Bob (Eng) | Feature flag: `rate_limit_v2=true` |
| 15:00 | Latency restored to 2.3s | Monitoring | SLO compliance achieved |
| 15:15 | Incident closed | Alice (SRE) | All metrics green for 15 minutes |

---

## 3. Customer Impact

**Quantitative**:
- **Affected Requests**: 45,000 requests (12% of total traffic)
- **Error Rate**: 2.3% (870 failed requests, 503 errors)
- **Latency**: P95 5.2s, P99 8.7s (vs SLO 2.5s/5.0s)
- **Duration**: 45 minutes
- **Affected Users**: ~1,200 unique clients

**Qualitative**:
- User-reported issues: 8 support tickets
- Social media mentions: 3 tweets about "slow responses"
- Partner escalation: NewPartnerCo contacted via Slack

**Evidence**:
- Grafana: [link to dashboard snapshot]
- Support tickets: #12345, #12346, #12347...
- Error logs: `audit/incident_logs_20251101.txt`

---

## 4. What Failed vs What Worked

### ❌ What Failed
- **DB connection pool sizing**: Undersized for burst traffic (10 connections)
- **Rate limiting**: Not enforced per-client (allowed single client to monopolize)
- **Capacity planning**: No early warning for 3× traffic increase
- **Runbook coverage**: No runbook for "sudden partner integration traffic"

### ✅ What Worked
- **Monitoring**: Alerts fired within 2 minutes of degradation
- **Incident response**: SRE acknowledged in 4 minutes, MTTR 45 minutes
- **Rollback safety**: No deployments during incident (change freeze respected)
- **Communication**: Stakeholders notified via Slack within 10 minutes

---

## 5. Five Whys (Root Cause Analysis)

1. **Why did latency degrade?**  
   → Database connection pool was exhausted.

2. **Why was the connection pool exhausted?**  
   → Traffic spiked 3× due to new partner integration going live.

3. **Why didn't we anticipate this traffic increase?**  
   → Partner launch communication was not shared with SRE team.

4. **Why wasn't rate limiting effective?**  
   → Rate limiting was global (per-service), not per-client, allowing one client to consume all capacity.

5. **Why didn't autoscaling prevent this?**  
   → HPA was scaling pods, but DB connection pool size is configured statically (not auto-scaled).

**Root Cause**: Lack of per-client rate limiting + static DB pool configuration + communication gap between product and SRE teams.

---

## 6. Operational Invariants Breached

Reference: `audit/OPERATIONAL_INVARIANTS.yml`

| Invariant | Threshold | Actual | Duration | Breach? |
|-----------|-----------|--------|----------|---------|
| `p95_ms` | <=2500 | 5200ms | 45 min | ✅ YES |
| `error_rate` | <=0.01 | 0.023 | 45 min | ✅ YES |
| `success_rate` | >=0.99 | 0.977 | 45 min | ✅ YES |
| `five_xx_rate` | <=0.005 | 0.023 | 45 min | ✅ YES |
| `circuit_breaker_trips` | ==0 | 0 | - | ❌ NO |

**Verdict**: 4 of 5 SLOs breached. Error budget consumed: 45 min / 43.2 min monthly = **104% of budget** (overdrawn).

---

## 7. Action Items

| ID | Action | Driver | Assignee | Target Date | Status |
|----|--------|--------|----------|-------------|--------|
| AI-1 | Implement per-client rate limiting (token bucket, 50 RPS/client) | Alice | Bob (Eng) | 2025-11-08 | 🟡 In Progress |
| AI-2 | Auto-scale DB connection pool based on pod count (10 + 5*replicas) | Alice | Carol (Infra) | 2025-11-08 | 🟡 In Progress |
| AI-3 | Add partner integration launch checklist to `docs/operations/Checklists/` | Alice | Dave (PM) | 2025-11-05 | 🟢 Complete |
| AI-4 | Create runbook: "Partner traffic surge" → `docs/operations/runbooks/PartnerTrafficSurge.md` | Alice | Alice (SRE) | 2025-11-10 | 🔴 Not Started |
| AI-5 | Implement early warning alert: `traffic_growth_7d > 50%` | Alice | Bob (Eng) | 2025-11-15 | 🔴 Not Started |
| AI-6 | Update capacity planning model to include partner traffic projections | Alice | Carol (Infra) | 2025-11-30 | 🔴 Not Started |
| AI-7 | Add DB pool size to Grafana dashboard | Alice | Bob (Eng) | 2025-11-05 | 🟢 Complete |

---

## 8. Evidence Pack Links

- **Grafana Dashboard**: https://grafana.company.com/d/incident-20251101-001
- **Prometheus Queries**: [saved in `audit/prometheus_queries_20251101.txt`]
- **Application Logs**: `audit/incident_logs_20251101.txt`
- **PRs Created**:
  - Rate limiting v2: https://github.com/org/repo/pull/1234
  - DB pool autoscaling: https://github.com/org/repo/pull/1235
- **SBOM**: `audit/SBOM_cyclonedx.json` (dependency snapshot at incident time)
- **Runbook Used**: `docs/operations/runbooks/WEEK2_LoadSpike.md` (partially effective)

---

## 9. Learning Outcomes

### For SRE Team
- **Positive**: Incident response time was excellent (4 min acknowledgment, 45 min MTTR)
- **Improvement**: Need better visibility into product launch calendar
- **Process Change**: Mandate SRE review for any new partner integrations (checklist item)

### For Engineering Team
- **Positive**: Feature flag for rate limiting v2 was ready and worked immediately
- **Improvement**: DB connection pool sizing should be a function of replica count
- **Process Change**: Add connection pool metrics to pre-deployment checklist

### For Product Team
- **Positive**: Quick communication once incident was escalated
- **Improvement**: Partner launch must include capacity planning review
- **Process Change**: Add "SRE Capacity Review" as mandatory gate for partner integrations

---

## 10. Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Incident Commander** | Alice Smith (SRE) | 2025-11-02 | ✅ Approved |
| **Engineering Lead** | Bob Johnson (Eng) | 2025-11-02 | ✅ Approved |
| **Product Manager** | Dave Lee (PM) | 2025-11-03 | ✅ Approved |

---

**Retrospective Completed**: 2025-11-03  
**Next Review**: 2025-12-01 (verify action items completed)  
**Related Incidents**: INC-20250915-003 (similar DB pool issue)
