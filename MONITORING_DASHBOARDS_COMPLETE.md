# ASTRA Monitoring Dashboards & Prometheus Alerts

## Overview

Comprehensive monitoring for ASTRA Phase-C with Grafana dashboards and Prometheus alerting.

**Dashboards**: 4 main panels
**Alerts**: 4 critical alerts
**Data Source**: Prometheus with event bus metrics

## Architecture

```plaintext
Event Bus → Prometheus Exporter → Prometheus → Grafana Dashboards
              (metrics collection)     (storage)   (visualization)
```

## Prometheus Metrics

### Core Metrics

#### 1. Route Mix Metrics

```plaintext
astra_router_calls_total{mode="code|vision|audio|text"}
astra_router_evolution_phases_total{phase="sense|plan|act|learn|reflect"}
astra_router_response_time_seconds{quantile="0.5|0.95|0.99"}
```

#### 2. Latency Metrics

```plaintext
astra_tool_execution_duration_seconds{tool="name", status="success|failed|timeout"}
astra_plan_generation_duration_seconds
astra_plan_execution_duration_seconds{status="success|failed"}
astra_consent_approval_time_seconds
```

#### 3. Consent & Budget Metrics

```plaintext
astra_consent_requests_total{status="approved|rejected"}
astra_consent_bypass_attempts_total
astra_budget_exhaustion_events_total{component="steps|tool_calls|walltime"}
astra_acт_phase_gates_total{result="allowed|blocked"}
```

#### 4. OS Actions Metrics

```plaintext
astra_os_action_total{operator="file|process|network|resource", status="success|failed"}
astra_os_action_duration_seconds{operator="file|process|network|resource"}
```

## Grafana Dashboards

### Dashboard 1: Route Mix Panel

**Purpose**: Visualize request distribution across modalities

**Metrics**:

- astra_router_calls_total by mode
- Evolution phase distribution

**Visualization**: Pie chart + time series
**Refresh**: 10s
**Time Range**: Last 1 hour

```json
{
  "title": "Route Mix (Modes)",
  "targets": [
    {
      "expr": "sum by (mode) (rate(astra_router_calls_total[5m]))",
      "legendFormat": "{{mode}}"
    }
  ],
  "type": "piechart",
  "unit": "short"
}
```

### Dashboard 2: Latency Panel

**Purpose**: Monitor response times across components

**Metrics**:

- Tool execution latency (p50, p95, p99)
- Plan generation time
- Consent approval time

**Visualization**: Graph with percentiles
**Refresh**: 10s
**Time Range**: Last 1 hour

```json
{
  "title": "Latency Monitoring",
  "targets": [
    {
      "expr": "histogram_quantile(0.95, rate(astra_tool_execution_duration_seconds_bucket[5m]))",
      "legendFormat": "Tool Exec P95"
    },
    {
      "expr": "histogram_quantile(0.99, rate(astra_tool_execution_duration_seconds_bucket[5m]))",
      "legendFormat": "Tool Exec P99"
    }
  ],
  "type": "graph",
  "unit": "s"
}
```

### Dashboard 3: Consent Blocks Panel

**Purpose**: Track consent decisions and security events

**Metrics**:

- Consent approvals vs rejections
- Bypass attempts
- ACT phase gate blocks
- Budget exhaustion events

**Visualization**: Stacked bar + gauge
**Refresh**: 5s
**Time Range**: Last 4 hours

```json
{
  "title": "Consent & Security Events",
  "targets": [
    {
      "expr": "sum by (status) (rate(astra_consent_requests_total[5m]))",
      "legendFormat": "{{status}}"
    },
    {
      "expr": "rate(astra_consent_bypass_attempts_total[5m])",
      "legendFormat": "Bypass Attempts"
    }
  ],
  "type": "stat",
  "unit": "ops"
}
```

### Dashboard 4: OS Actions Panel

**Purpose**: Monitor OS operator activities

**Metrics**:

- File operations (read/write/delete)
- Process operations
- Network operations
- Resource monitoring

**Visualization**: Table + time series
**Refresh**: 10s
**Time Range**: Last 1 hour

```json
{
  "title": "OS Operator Actions",
  "targets": [
    {
      "expr": "sum by (operator, status) (rate(astra_os_action_total[5m]))",
      "format": "table",
      "instant": true
    }
  ],
  "type": "table"
}
```

## Prometheus Alerts

### Alert 1: High Text Latency (P95)

**Condition**: Tool execution P95 > 2 seconds
**Severity**: Warning
**Action**: Check tool performance

```yaml
- alert: HighTextLatencyP95
  expr: |
    histogram_quantile(0.95, rate(astra_tool_execution_duration_seconds_bucket[5m])) > 2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High tool latency detected (P95: {{ $value }}s)"
    description: "Tool execution latency exceeds 2s threshold"
```

### Alert 2: Error Rate Spike

**Condition**: Tool failure rate > 10%
**Severity**: Critical
**Action**: Investigate failures

```yaml
- alert: ErrorRateSpike
  expr: |
    (sum by (tool) (rate(astra_tool_execution_duration_seconds_bucket{status="failed"}[5m])) /
     sum by (tool) (rate(astra_tool_execution_duration_seconds_bucket[5m]))) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "High error rate for {{ $labels.tool }}"
    description: "Error rate: {{ $value | humanizePercentage }}"
```

### Alert 3: Consent Bypass Attempt

**Condition**: Any consent bypass attempt detected
**Severity**: Critical
**Action**: Immediate investigation

```yaml
- alert: ConsentBypassAttempt
  expr: rate(astra_consent_bypass_attempts_total[1m]) > 0
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "SECURITY: Consent bypass attempt detected"
    description: "Unauthorized attempt to bypass consent gates"
```

### Alert 4: OS Operation Spike

**Condition**: OS operations exceed threshold
**Severity**: Warning
**Action**: Monitor resource usage

```yaml
- alert: OSOPActionSpike
  expr: |
    sum(rate(astra_os_action_total[5m])) > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "OS operation spike detected ({{ $value }} ops/sec)"
    description: "Unusual volume of OS operations"
```

## Setup Instructions

### 1. Prometheus Configuration

Add to `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'astra'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboard Setup

#### Import Dashboards

```bash
# Via CLI
grafana-cli dashboard import 1 --parameterized
```

#### Or Manual JSON Upload

1. Grafana → Dashboards → Import
2. Paste dashboard JSON
3. Select Prometheus data source
4. Click Import

#### Example Dashboard JSON

```json
{
  "dashboard": {
    "title": "ASTRA Phase-C Monitoring",
    "panels": [
      {
        "id": 1,
        "title": "Route Mix",
        "targets": [
          {
            "expr": "sum by (mode) (rate(astra_router_calls_total[5m]))"
          }
        ]
      },
      {
        "id": 2,
        "title": "Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(astra_tool_execution_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "id": 3,
        "title": "Consent Blocks",
        "targets": [
          {
            "expr": "sum by (status) (rate(astra_consent_requests_total[5m]))"
          }
        ]
      },
      {
        "id": 4,
        "title": "OS Actions",
        "targets": [
          {
            "expr": "sum by (operator) (rate(astra_os_action_total[5m]))"
          }
        ]
      }
    ],
    "refresh": "10s",
    "time": {
      "from": "now-1h",
      "to": "now"
    }
  }
}
```

### 3. Alert Rules Setup

Create `astra_alerts.yml`:

```yaml
groups:
  - name: astra_alerts
    interval: 30s
    rules:
      # Include all alerts from above
      - alert: HighTextLatencyP95
        ...
```

Load in Prometheus:

```yaml
# prometheus.yml
rule_files:
  - 'astra_alerts.yml'
```

### 4. Event Bus Metrics Exporter

```python
from astra.core.event_bus import get_event_bus
from prometheus_client import Counter, Histogram, Gauge
import asyncio

class MetricsExporter:
    def __init__(self):
        self.bus = get_event_bus()
        
        # Counters
        self.tool_calls = Counter(
            'astra_tool_execution_duration_seconds',
            'Tool execution duration',
            ['tool', 'status']
        )
        
        self.consent_requests = Counter(
            'astra_consent_requests_total',
            'Consent requests',
            ['status']
        )
        
        # Gauges
        self.active_plans = Gauge(
            'astra_active_plans',
            'Currently executing plans'
        )
        
        # Subscribe to events
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        self.bus.subscribe("astra.tool.executed", self._on_tool_executed)
        self.bus.subscribe("astra.plan.consent_decision", self._on_consent)
        self.bus.subscribe("astra.plan.execution_start", self._on_plan_start)
        self.bus.subscribe("astra.plan.execution_complete", self._on_plan_complete)
    
    def _on_tool_executed(self, event):
        status = "success" if event.data.get("success") else "failed"
        self.tool_calls.labels(
            tool=event.data["tool"],
            status=status
        ).inc()
    
    def _on_consent(self, event):
        status = "approved" if event.data["approved"] else "rejected"
        self.consent_requests.labels(status=status).inc()
    
    def _on_plan_start(self, event):
        self.active_plans.inc()
    
    def _on_plan_complete(self, event):
        self.active_plans.dec()
```

## Monitoring Best Practices

### 1. Set Appropriate Thresholds

- **Tool Latency P95**: 2-5 seconds (adjust based on tool type)
- **Error Rate**: 5-10% (depends on operation type)
- **OS Operation Spike**: 50-200 ops/sec (environment dependent)

### 2. Alert Routing

```yaml
# alertmanager.yml
receivers:
  - name: 'astra-team'
    slack_configs:
      - channel: '#astra-monitoring'
        api_url: 'YOUR_WEBHOOK_URL'

route:
  receiver: 'astra-team'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
```

### 3. Regular Dashboard Reviews

- Daily: Error rates and latency trends
- Weekly: Capacity planning and resource usage
- Monthly: Performance baselines and optimization opportunities

### 4. Metric Retention

```yaml
# prometheus.yml
global:
  retention: 30d
  retention_size: 50GB
```

## Troubleshooting

### No metrics showing

1. Verify event bus is emitting events
2. Check metrics exporter is running
3. Verify Prometheus scrape config
4. Check firewall rules

### High latency alerts firing

1. Check individual tool performance
2. Monitor system resources (CPU, memory)
3. Review query complexity
4. Consider scaling

### Consent blocks increasing

1. Review consent policies
2. Check if operations are legitimately risky
3. Adjust thresholds if needed
4. Investigate bypass attempts

## Next Steps

### Phase-D Monitoring

- Distributed tracing (Jaeger)
- Custom metrics per LLM provider
- Advanced anomaly detection
- Machine learning-based alerts

### Extended Metrics

- LLM token usage by model
- Memory consumption patterns
- Budget utilization analytics
- Consent decision trees

## Dashboard Export

To export dashboards:

```bash
# Export as JSON
curl http://localhost:3000/api/dashboards/uid/astra-phase-c \
  -H "Authorization: Bearer $GRAFANA_TOKEN" > dashboard.json
```

To import:

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -d @dashboard.json
```
