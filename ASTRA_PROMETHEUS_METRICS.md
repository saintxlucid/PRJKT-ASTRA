# 📊 ASTRA CORE - PROMETHEUS METRICS INVENTORY

**Date**: 2025-11-01  
**Metrics Format**: OpenMetrics 0.0.4  
**Endpoint**: `http://localhost:8080/metrics`  
**Source**: [`astra_core.py:111-170`]

---

## 🎯 EXPORTED METRICS

### 1. System Information

**astra_info** (gauge)
```prometheus
# HELP astra_info ASTRA Core information
# TYPE astra_info gauge
astra_info{version="1.0.0"} 1
```

**Location**: [`astra_core.py:109-112`]  
**Labels**: `version`  
**Purpose**: Version metadata for dashboards

---

### 2. Uptime

**astra_uptime_seconds** (counter)
```prometheus
# HELP astra_uptime_seconds Uptime in seconds
# TYPE astra_uptime_seconds counter
astra_uptime_seconds 3600.25
```

**Location**: [`astra_core.py:115-118`]  
**Calculation**: `time.time() - self.start_time`  
**Purpose**: Track service restarts, detect crashes

---

### 3. Request Counts

**astra_requests_total** (counter)
```prometheus
# HELP astra_requests_total Total requests by endpoint
# TYPE astra_requests_total counter
astra_requests_total{endpoint="/answer"} 150
astra_requests_total{endpoint="/live"} 500
astra_requests_total{endpoint="/metrics"} 50
```

**Location**: [`astra_core.py:121-124`]  
**Labels**: `endpoint`  
**Increment**: `record_request_start(endpoint)` [`astra_core.py:93`]  
**Purpose**: Traffic patterns, endpoint popularity

---

### 4. Requests In Progress

**astra_requests_in_progress** (gauge)
```prometheus
# HELP astra_requests_in_progress Current requests in progress
# TYPE astra_requests_in_progress gauge
astra_requests_in_progress{endpoint="/answer"} 3
astra_requests_in_progress{endpoint="/stream"} 1
```

**Location**: [`astra_core.py:127-132`]  
**Labels**: `endpoint`  
**Increment**: `record_request_start()` (adds +1) [`astra_core.py:94`]  
**Decrement**: `record_request_end()` (subtracts -1) [`astra_core.py:97`]  
**Purpose**: Detect backpressure, queue depth

---

### 5. Request Duration (Latency)

**astra_request_duration_seconds** (summary)
```prometheus
# HELP astra_request_duration_seconds Request duration in seconds
# TYPE astra_request_duration_seconds summary
astra_request_duration_seconds{endpoint="/answer",quantile="0.5"} 0.0850
astra_request_duration_seconds{endpoint="/answer",quantile="0.95"} 0.1100
astra_request_duration_seconds{endpoint="/answer",quantile="0.99"} 0.1100
astra_request_duration_seconds_sum{endpoint="/answer"} 12.5000
astra_request_duration_seconds_count{endpoint="/answer"} 150
```

**Location**: [`astra_core.py:134-149`]  
**Labels**: `endpoint`, `quantile`  
**Quantiles**: P50, P95, P99  
**Calculation**: Sorts durations, extracts quantiles [`astra_core.py:141-144`]  
**Purpose**: SLO validation (P95 <2.5s, P99 <5s)

**Alert Rule** (recommended):
```yaml
- alert: HighP95Latency
  expr: astra_request_duration_seconds{quantile="0.95"} > 2.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P95 latency exceeded SLO (>2.5s)"
```

---

### 6. Error Counts

**astra_errors_total** (counter)
```prometheus
# HELP astra_errors_total Total errors by endpoint and status
# TYPE astra_errors_total counter
astra_errors_total{error="/answer_429"} 5
astra_errors_total{error="/stream_500"} 2
```

**Location**: [`astra_core.py:152-155`]  
**Labels**: `error` (format: `{endpoint}_{status_code}`)  
**Increment**: `record_request_end()` if `status_code >= 400` [`astra_core.py:99`]  
**Purpose**: Error rate tracking, detect failures

**Alert Rule** (recommended):
```yaml
- alert: HighErrorRate
  expr: rate(astra_errors_total[5m]) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Error rate >1% (current: {{ $value | humanizePercentage }})"
```

---

### 7. Circuit Breaker Trips

**astra_circuit_breaker_trips_total** (counter)
```prometheus
# HELP astra_circuit_breaker_trips_total Circuit breaker trips by component
# TYPE astra_circuit_breaker_trips_total counter
astra_circuit_breaker_trips_total{component="llm_provider"} 0
astra_circuit_breaker_trips_total{component="vector_store"} 0
```

**Location**: [`astra_core.py:158-161`]  
**Labels**: `component`  
**Increment**: `record_circuit_breaker_trip(component)` [`astra_core.py:103`]  
**Purpose**: Detect downstream failures, trigger rollback

**Alert Rule** (recommended):
```yaml
- alert: CircuitBreakerTripped
  expr: increase(astra_circuit_breaker_trips_total[5m]) > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Circuit breaker tripped for {{ $labels.component }}"
```

---

### 8. Queue Depth

**astra_queue_depth** (gauge)
```prometheus
# HELP astra_queue_depth Current queue depth
# TYPE astra_queue_depth gauge
astra_queue_depth 8
```

**Location**: [`astra_core.py:164-170`]  
**Calculation**: Median of last 1000 samples [`astra_core.py:167-168`]  
**Sample**: `record_queue_depth(depth)` [`astra_core.py:105`]  
**Purpose**: Backpressure detection, scaling trigger

**Alert Rule** (recommended):
```yaml
- alert: HighQueueDepth
  expr: astra_queue_depth > 50
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Queue depth high ({{ $value }}), possible backpressure"
```

---

## 📊 METRICS SUMMARY TABLE

| Metric | Type | Labels | Location | Purpose |
|--------|------|--------|----------|---------|
| **astra_info** | gauge | version | Line 111 | Version metadata |
| **astra_uptime_seconds** | counter | — | Line 117 | Uptime tracking |
| **astra_requests_total** | counter | endpoint | Line 122 | Traffic volume |
| **astra_requests_in_progress** | gauge | endpoint | Line 128 | Backpressure |
| **astra_request_duration_seconds** | summary | endpoint, quantile | Line 135 | Latency (P50/P95/P99) |
| **astra_errors_total** | counter | error | Line 153 | Error rate |
| **astra_circuit_breaker_trips_total** | counter | component | Line 159 | CB trips |
| **astra_queue_depth** | gauge | — | Line 165 | Queue backlog |

---

## 🚨 RECOMMENDED ALERT RULES

### SLO Alerts

**High P95 Latency** (SLO: <2.5s)
```yaml
groups:
  - name: astra_slo
    interval: 30s
    rules:
      - alert: HighP95Latency
        expr: astra_request_duration_seconds{quantile="0.95"} > 2.5
        for: 5m
        labels:
          severity: warning
          slo: latency
        annotations:
          summary: "P95 latency exceeded SLO (>2.5s for 5 min)"
          dashboard: "https://grafana.company.internal/d/astra-core"
```

**High P99 Latency** (SLO: <5s)
```yaml
      - alert: HighP99Latency
        expr: astra_request_duration_seconds{quantile="0.99"} > 5.0
        for: 5m
        labels:
          severity: critical
          slo: latency
        annotations:
          summary: "P99 latency exceeded SLO (>5s for 5 min)"
```

**High Error Rate** (SLO: <1%)
```yaml
      - alert: HighErrorRate
        expr: rate(astra_errors_total[5m]) / rate(astra_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
          slo: availability
        annotations:
          summary: "Error rate >1% (current: {{ $value | humanizePercentage }})"
```

### Operational Alerts

**Circuit Breaker Tripped**
```yaml
      - alert: CircuitBreakerTripped
        expr: increase(astra_circuit_breaker_trips_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker tripped for {{ $labels.component }}"
          runbook: "https://docs.company.internal/runbooks/circuit-breaker"
```

**High Queue Depth**
```yaml
      - alert: HighQueueDepth
        expr: astra_queue_depth > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Queue depth high ({{ $value }}), possible backpressure"
```

**Service Down**
```yaml
      - alert: AstraDown
        expr: up{job="astra-core"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ASTRA Core service is down"
```

---

## 📈 GRAFANA DASHBOARD PANELS

### Panel 1: Request Rate

**Query**:
```promql
rate(astra_requests_total[5m])
```

**Visualization**: Time series (lines by endpoint)  
**Y-Axis**: Requests per second  
**Legend**: `{{endpoint}}`

### Panel 2: Latency (P50/P95/P99)

**Query**:
```promql
astra_request_duration_seconds{quantile="0.5"}
astra_request_duration_seconds{quantile="0.95"}
astra_request_duration_seconds{quantile="0.99"}
```

**Visualization**: Time series (3 lines)  
**Y-Axis**: Seconds  
**Thresholds**: Yellow at 2.5s (P95 SLO), Red at 5s (P99 SLO)

### Panel 3: Error Rate

**Query**:
```promql
rate(astra_errors_total[5m]) / rate(astra_requests_total[5m])
```

**Visualization**: Time series  
**Y-Axis**: Percentage  
**Threshold**: Red at 1% (SLO)

### Panel 4: Requests In Progress

**Query**:
```promql
astra_requests_in_progress
```

**Visualization**: Time series (stacked area by endpoint)  
**Y-Axis**: Count  
**Purpose**: Backpressure visualization

### Panel 5: Circuit Breaker Status

**Query**:
```promql
astra_circuit_breaker_trips_total
```

**Visualization**: Stat panel (single value)  
**Color**: Green if 0, Red if >0

### Panel 6: Queue Depth

**Query**:
```promql
astra_queue_depth
```

**Visualization**: Gauge  
**Thresholds**: Green <20, Yellow 20-50, Red >50

### Panel 7: Uptime

**Query**:
```promql
astra_uptime_seconds / 86400
```

**Visualization**: Stat panel  
**Unit**: Days  
**Purpose**: Show uptime in days

---

## 🔍 METRIC GAPS & RECOMMENDATIONS

### Missing Metrics (Recommended to Add)

1. **astra_memory_operations_total** (counter)
   - Labels: `operation` (store, retrieve, consolidate)
   - Purpose: Track memory system usage

2. **astra_rag_retrieval_duration_seconds** (histogram)
   - Labels: `stage` (query_gen, dense_retrieval, fusion, rerank)
   - Purpose: RAG pipeline performance breakdown

3. **astra_identity_alignment_checks_total** (counter)
   - Labels: `result` (pass, fail, blocked)
   - Purpose: Identity enforcement tracking

4. **astra_consent_requests_total** (counter)
   - Labels: `status` (approved, rejected, expired)
   - Purpose: Consent queue monitoring

5. **astra_signed_plans_executed_total** (counter)
   - Labels: `result` (success, rollback)
   - Purpose: Signed plan compliance

6. **astra_memory_integrity_failures_total** (counter)
   - Purpose: Detect memory poisoning attempts (F-002)

7. **astra_model_checksum_failures_total** (counter)
   - Purpose: Detect supply chain attacks (F-003)

8. **astra_sandbox_escape_attempts_total** (counter)
   - Purpose: Security monitoring (F-004)

9. **astra_prompt_injection_attempts_total** (counter)
   - Purpose: Red-line defense monitoring (F-005)

10. **astra_provenance_attached_total** (counter)
    - Labels: `attached` (true, false)
    - Purpose: RAG provenance coverage (F-008)

---

## ✅ METRICS ACCEPTANCE CRITERIA

**Metrics system passes audit if**:
- [ ] All 8 current metrics export correctly (curl `/metrics` succeeds)
- [ ] OpenMetrics 0.0.4 format validated (Prometheus scrapes without errors)
- [ ] P95/P99 latency metrics match SLO targets (<2.5s, <5s)
- [ ] Error rate metric tracks all 4xx/5xx responses
- [ ] Circuit breaker metrics increment on downstream failures
- [ ] Queue depth metric samples every request
- [ ] 10 new metrics added (memory, RAG, identity, consent, security)
- [ ] Alert rules deployed to Prometheus (8+ rules)
- [ ] Grafana dashboard operational (7+ panels)

---

## 📁 ARTIFACTS

**Metrics Endpoint**: `http://localhost:8080/metrics`  
**Source Code**: [`astra_core.py:76-170`]  
**Alert Rules**: `k8s/monitoring/prometheusrule.yaml` (if exists)  
**Grafana Dashboard**: `k8s/monitoring/grafana-dashboard.json` (if exists)

---

📊 **Prometheus metrics inventory complete. 8 metrics exported, 10 recommended to add.**
