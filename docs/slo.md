# ASTRA System Service Level Objectives (SLOs)

This document outlines the Service Level Objectives (SLOs) for the ASTRA system, along with their measurement methods and alerting thresholds.

## API Performance

### Latency SLO
- **Target**: 95th percentile latency ≤ 500ms
- **Measurement**: Using Prometheus histogram metrics
- **Metric**: `astra_api_latency_seconds_bucket`
- **Alert**: Triggers when p95 exceeds 500ms for 5 minutes
- **Severity**: Warning

## WebSocket Reliability

### Uptime SLO
- **Target**: ≥ 99% uptime
- **Measurement**: Heartbeat success ratio
- **Metric**: `astra_ws_uptime_ratio`
- **Alert**: Triggers when uptime drops below 99% for 5 minutes
- **Severity**: Critical

## Resource Utilization

### Context Size SLO
- **Target**: Total context size ≤ 100MB
- **Measurement**: Sum of all context bytes
- **Metric**: `astra_context_bytes_total`
- **Alert**: Triggers when total exceeds 100MB for 5 minutes
- **Severity**: Warning

## Error Rates

### System Error Rate SLO
- **Target**: < 1 error per second
- **Measurement**: Rate of error counter increases
- **Metric**: `astra_errors_total`
- **Alert**: Triggers when error rate exceeds 1/s for 5 minutes
- **Severity**: Critical

## Log Management

### Log Sampling Rate
- **Target**: ≥ 1% sampling rate
- **Measurement**: Ratio of sampled to total logs
- **Metrics**: `astra_logs_sampled_total` / `astra_logs_total`
- **Alert**: Triggers when sampling rate drops below 1% for 5 minutes
- **Severity**: Warning

## Monitoring Implementation

### Dashboards
- Grafana dashboard available at `/monitoring/dashboards/astra-metrics.json`
- Real-time visualization of all SLO metrics
- 10-second refresh rate
- 6-hour default time window

### Alerting
- Prometheus alerting rules at `/monitoring/rules/astra-alerts.yml`
- All alerts use 5-minute evaluation windows
- Notifications configured through Prometheus Alertmanager
- Severity levels:
  - Critical: Immediate action required
  - Warning: Investigation needed

### Log Sampling
- Priority-based sampling implementation
- Configurable sampling rates by log level
- Force sampling for critical events
- Context-aware sampling decisions

## Success Criteria

✅ Grafana dashboard implemented and accessible  
✅ Prometheus alerting rules configured  
✅ Log sampling system operational  
✅ All SLOs documented and measurable  
✅ Alert thresholds aligned with SLO targets  