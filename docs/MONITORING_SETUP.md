# ASTRA Monitoring Setup Guide

## Overview

This guide describes how to set up comprehensive monitoring for the ASTRA system using:
- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for notifications

## Prerequisites

- Docker and Docker Compose installed
- Network access to ports 8000 (metrics), 9090 (Prometheus), 3000 (Grafana)
- Python environment with prometheus_client package

## Quick Start (5 Minutes)

1. Start the monitoring stack:
```bash
cd ops
docker-compose up -d prometheus grafana
```

2. Verify metrics endpoint:
```bash
curl http://localhost:8000/metrics
```

3. Access Grafana:
- URL: http://localhost:3000
- Default credentials: admin/admin
- Import dashboard from ops/grafana/grafana_astra_dashboard.json

## Configuration Details

### Prometheus Configuration 
Located at `ops/prometheus/prometheus.yml`:
- Scrape interval: 15s
- Evaluation interval: 15s
- Three scrape jobs:
  - astra: Core metrics (port 8000)
  - astra-tools: Tools metrics (port 8001)
  - astra-desktop: Desktop UI metrics (port 8002)

### Alert Rules
Located at `ops/prometheus/alerts.yml`:

Critical Alerts:
- ConsentBypassSpike: Multiple consent bypass attempts
- OSOPDestructiveActionsObserved: Destructive operations detected

Warning Alerts:
- HighToolLatencyP95: Tool latency p95 > 5s
- HighPlanGenerationLatencyP95: Plan generation p95 > 10s
- HighToolErrorRate: Error rate > 10%
- OSOPActionSpike: High rate of OSOP actions
- ConsentBlocksObserved: Multiple consent blocks

### Grafana Dashboard
Located at `ops/grafana/grafana_astra_dashboard.json`:

Four main sections:
1. Route Mix Overview
   - Request distribution by mode
   - Evolution phase execution rates

2. Latency Overview
   - Tool execution latency (p50/p95/p99)
   - Plan generation latency gauge

3. Consent & Budget
   - Consent request status
   - Budget exhaustion events

4. OS Operations
   - OS action status
   - OSOP actions table

## Key Metrics Reference

### Counter Metrics
- astra_router_calls_total: Requests by mode
- astra_tool_execution_total: Tool executions by status
- astra_consent_requests_total: Consent decisions
- astra_osop_actions_total: OSOP capability usage

### Histogram Metrics
- astra_tool_execution_duration_seconds: Tool timing
- astra_plan_generation_duration_seconds: Plan generation timing
- astra_consent_approval_time_seconds: Consent decision timing

### Gauge Metrics
- astra_active_plans: Current executing plans
- astra_active_consent_requests: Pending consents
- astra_remaining_budget_tokens: Budget status

## Troubleshooting

1. Metrics not appearing:
   - Check metrics exporter is running: curl http://localhost:8000/metrics
   - Verify Prometheus targets: http://localhost:9090/targets
   - Check event bus subscriptions

2. Dashboard empty:
   - Verify Prometheus data source in Grafana
   - Check time range selection
   - Validate metric names in panel queries

3. Alerts not firing:
   - Check alert rule syntax
   - Verify alert manager configuration
   - Review alert thresholds

## Best Practices

1. Metric Naming:
   - Use consistent prefix: astra_*
   - Include units in name: *_seconds, *_bytes
   - Use appropriate type (counter vs gauge)

2. Alert Design:
   - Set appropriate thresholds based on baseline
   - Use "for" duration to avoid flapping
   - Include clear descriptions

3. Dashboard Organization:
   - Group related metrics
   - Use consistent time ranges
   - Include legends and documentation

## Next Steps

1. Set up alerting channels:
   - Configure AlertManager
   - Add PagerDuty/Slack integration
   - Test alert delivery

2. Fine-tune thresholds:
   - Monitor baseline metrics
   - Adjust alert thresholds
   - Add new metrics as needed

3. Add custom dashboards:
   - Create role-specific views
   - Add SLO tracking
   - Include capacity planning