# ASTRA Service Level Objectives (SLOs)

## Overview

This document defines ASTRA's Service Level Objectives (SLOs) - our targets for system performance and reliability. These SLOs help us monitor system health and drive improvements.

## Core SLOs

### 1. API Latency

**Target**: 95% of requests complete within 2.5 seconds
- Metric: `astra_tool_execution_duration_seconds`
- Alert: Triggers when p95 > 2.5s for 5min
- Measurement: Rolling 1-hour window
- Exclusions: Background tasks, batch operations

**Implementation**:
```promql
histogram_quantile(0.95, rate(astra_tool_execution_duration_seconds_bucket[1h])) <= 2.5
```

### 2. WebSocket Uptime

**Target**: 99.9% uptime measured by successful heartbeats
- Metric: `astra_router_heartbeat_success_total / astra_router_heartbeat_total`
- Alert: Triggers when success rate < 99.9% for 5min
- Measurement: Rolling 24-hour window
- Exclusions: Planned maintenance windows

**Implementation**:
```promql
sum(rate(astra_router_heartbeat_success_total[24h])) / sum(rate(astra_router_heartbeat_total[24h])) >= 0.999
```

### 3. Context Size Management

**Target**: 90% of requests use < 8K tokens
- Metric: `astra_context_tokens_total`
- Alert: Triggers when p90 > 8000 for 15min
- Measurement: Per-request basis
- Exclusions: Special long-context modes

**Implementation**:
```promql
histogram_quantile(0.90, rate(astra_context_tokens_bucket[15m])) <= 8000
```

### 4. Error Rate

**Target**: < 1% error rate across all operations
- Metric: `sum(astra_tool_execution_total{status="error"}) / sum(astra_tool_execution_total)`
- Alert: Triggers when rate > 1% for 5min
- Measurement: Rolling 5-minute window
- Exclusions: Client-side validation errors

**Implementation**:
```promql
sum(rate(astra_tool_execution_total{status="error"}[5m])) / sum(rate(astra_tool_execution_total[5m])) < 0.01
```

## OSOP-Specific SLOs

### 5. Consent Compliance

**Target**: 100% consent capture for privileged operations
- Metric: `astra_osop_actions_total{consent_given="true"} / astra_osop_actions_total`
- Alert: Triggers on any non-consented privileged action
- Measurement: Per-operation basis
- Exclusions: None - all privileged actions require consent

**Implementation**:
```promql
sum(increase(astra_osop_actions_total{consent_given="false"}[5m])) == 0
```

### 6. OS Action Performance

**Target**: 95% of OS operations complete within 500ms
- Metric: `astra_os_action_duration_seconds`
- Alert: Triggers when p95 > 0.5s for 5min
- Measurement: Rolling 5-minute window
- Exclusions: File operations > 1MB

**Implementation**:
```promql
histogram_quantile(0.95, rate(astra_os_action_duration_seconds_bucket[5m])) <= 0.5
```

## Memory System SLOs

### 7. Memory Sync Reliability

**Target**: < 0.1% reconciliation differences
- Metric: `astra_memory_sync_diffs_total / astra_memory_entries_total`
- Alert: Triggers when diff rate > 0.1%
- Measurement: Nightly reconciliation
- Exclusions: Entries marked for deletion

**Implementation**:
```promql
sum(increase(astra_memory_sync_diffs_total[24h])) / sum(astra_memory_entries_total) < 0.001
```

### 8. Memory Operation Latency

**Target**: 95% of memory operations complete within 250ms
- Metric: `astra_memory_operation_duration_seconds`
- Alert: Triggers when p95 > 0.25s for 5min
- Measurement: Rolling 5-minute window
- Exclusions: Bulk operations

**Implementation**:
```promql
histogram_quantile(0.95, rate(astra_memory_operation_duration_seconds_bucket[5m])) <= 0.25
```

## Budget & Resource SLOs

### 9. Budget Utilization

**Target**: < 5% budget exhaustion events
- Metric: `astra_budget_exhaustion_events_total / astra_tool_execution_total`
- Alert: Triggers when rate > 5% for 15min
- Measurement: Rolling 1-hour window
- Exclusions: Development/testing environments

**Implementation**:
```promql
sum(rate(astra_budget_exhaustion_events_total[1h])) / sum(rate(astra_tool_execution_total[1h])) < 0.05
```

### 10. Resource Efficiency

**Target**: < 70% average CPU utilization
- Metric: `astra_cpu_usage_percent`
- Alert: Triggers when avg > 70% for 10min
- Measurement: Rolling 5-minute window
- Exclusions: Startup/shutdown periods

**Implementation**:
```promql
avg_over_time(astra_cpu_usage_percent[5m]) < 70
```

## SLO Monitoring

### Dashboards
- Main SLO dashboard in Grafana
- Historical SLO performance trends
- Error budget consumption tracking
- Alert history visualization

### Reports
- Daily SLO compliance summary
- Weekly trend analysis
- Monthly SLO review
- Quarterly adjustments based on data

## Error Budget Policy

1. **Budget Calculation**:
   - 99.9% target = 43.8 minutes downtime/month
   - Error budget = (100% - SLO target)
   - Measured per calendar month

2. **Budget Consumption**:
   - Track via Prometheus metrics
   - Alert on high consumption rates
   - Emergency response > 50% consumed

3. **Response Actions**:
   - 25% consumed: Review and plan
   - 50% consumed: Implement fixes
   - 75% consumed: Feature freeze
   - 90% consumed: Emergency mode

## Review & Adjustment

- Monthly review of SLO performance
- Quarterly adjustment of targets
- Annual comprehensive review
- Feedback incorporation process

## Implementation Checklist

1. [x] Create new metrics for missing SLOs
   - Added WebSocket heartbeat metrics
   - Added context token tracking
   - Added memory operation metrics
   - Added CPU usage monitoring
2. [x] Update Prometheus alert rules
   - Added SLO-specific alerts
   - Configured critical severity for SLO breaches
   - Added proper alerting thresholds
3. [x] Create SLO-specific Grafana dashboard
   - Created SLO overview panel
   - Added detailed metric panels
   - Configured alerts in dashboard
4. [x] Set up error budget tracking
   - Implemented in Prometheus queries
   - Added to SLO dashboard
   - Alert rules for budget consumption
5. [ ] Implement automated reporting
   - Daily SLO summary email
   - Weekly trend report
   - Monthly review deck
6. [x] Document response procedures
   - Added to SLO definitions
   - Included escalation paths
   - Documented recovery actions
7. [ ] Train team on SLO monitoring
   - Schedule training session
   - Create runbook
   - Practice incident response
8. [ ] Establish review schedule
   - Set up monthly reviews
   - Plan quarterly adjustments
   - Create annual review template