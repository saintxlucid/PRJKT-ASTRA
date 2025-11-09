# Error Budget Policy

**SLO Window**: 30 days (rolling)  
**Availability Target**: 99.9%  
**Error Budget**: 0.1% = 43.2 minutes downtime/month

## Budget Spend Rules

### ≥50% Budget Spent (21.6 min consumed)
- **Action**: Freeze risky changes (new features, refactors)
- **Cadence**: Daily SLO standup (10 min)
- **Focus**: Stability over velocity

### ≥75% Budget Spent (32.4 min consumed)
- **Action**: Deploy freeze (hotfixes only, with SRE approval)
- **Cadence**: Twice-daily SLO review
- **Rollback**: Noncritical features disabled via feature flags

### ≥90% Budget Spent (38.9 min consumed)
- **Action**: Incident command activated
- **Cadence**: Hourly SLO review + stakeholder updates
- **Capacity**: Immediate capacity adds (no approval needed)
- **Features**: Disable experimental flags, reduce resource-heavy endpoints

## Budget Recovery

### Earn-Down via Stability
- Each 24h period with 100% availability earns back 1.44 min
- 7-day clean period = 10 min recovered

### Reliability PRs Prioritized
- Flaky test fixes
- Retry logic improvements
- Circuit breaker tuning
- Observability enhancements

## Reporting
- Weekly email to eng@ with budget status
- Grafana dashboard: `Error_Budget_SLO`
- Alerts:
  - `error_budget_50pct_consumed` (warning)
  - `error_budget_75pct_consumed` (critical)
  - `error_budget_90pct_consumed` (page SRE)

---
**Policy Owner**: SRE Lead  
**Last Updated**: 2025-11-01
