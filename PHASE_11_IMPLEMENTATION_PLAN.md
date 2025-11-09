# Phase 11: Observability & Monitoring - Implementation Plan

**Status:** In Progress  
**Target Completion:** Current Session  
**Total Target Code:** 500+ lines of production code  
**Target Test Cases:** 30+ comprehensive tests  

---

## Overview

Phase 11 establishes comprehensive observability across all ASTRA-OS subsystems (Phases 1-10). This enables monitoring, debugging, and operational insights into system behavior.

**4 Core Modules:**
1. **StructuredLogger** - JSON-based event logging with context
2. **MetricsCollector** - Prometheus-compatible metrics
3. **DistributedTracer** - OpenTelemetry-based tracing
4. **IncidentExporter** - JSON/CSV incident export

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Application Layer (Phases 1-10)                │
│  Boot|Bus|Sensors|Memory|Policy|Tools|Autonomy|...     │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
      ┌──────▼──────────────────────────▼──────────┐
      │      Phase 11: Observability Layer        │
      │  ┌──────────────────────────────────────┐ │
      │  │  StructuredLogger (JSON Events)      │ │
      │  │  - Context propagation               │ │
      │  │  - Async logging                     │ │
      │  │  - Log levels + filtering            │ │
      │  └──────────────────────────────────────┘ │
      │  ┌──────────────────────────────────────┐ │
      │  │  MetricsCollector (Prometheus)       │ │
      │  │  - Counter/Gauge/Histogram/Summary   │ │
      │  │  - Family registration               │ │
      │  │  - Export format                     │ │
      │  └──────────────────────────────────────┘ │
      │  ┌──────────────────────────────────────┐ │
      │  │  DistributedTracer (OpenTelemetry)   │ │
      │  │  - Trace spans                       │ │
      │  │  - Context propagation               │ │
      │  │  - Span events                       │ │
      │  │  - Export formats                    │ │
      │  └──────────────────────────────────────┘ │
      │  ┌──────────────────────────────────────┐ │
      │  │  IncidentExporter (JSON/CSV)         │ │
      │  │  - Batch export                      │ │
      │  │  - Format conversion                 │ │
      │  │  - File rotation                     │ │
      │  └──────────────────────────────────────┘ │
      └────────────┬───────────────┬──────────────┘
                   │               │
        ┌──────────▼──┐    ┌──────▼──────────┐
        │  Log Files  │    │  Metrics Store  │
        │  (JSON)     │    │  (Prometheus)   │
        └─────────────┘    └─────────────────┘
```

---

## Module 1: StructuredLogger

**File:** `apps/core/logging.py`  
**Target Lines:** 250 lines  

### Purpose
JSON-based event logging with structured context, enabling centralized log aggregation and correlation.

### Classes

#### LogContext (Dataclass)
```python
@dataclass
class LogContext:
    request_id: str                    # Unique request identifier
    user_id: Optional[str] = None      # Acting user
    session_id: Optional[str] = None   # Session identifier
    component: Optional[str] = None    # Source component
    module: Optional[str] = None       # Source module
    tags: Dict[str, str] = field()     # Custom tags
    parent_span_id: Optional[str] = None
```

#### LogLevel (Enum)
```python
class LogLevel(Enum):
    DEBUG = "DEBUG"      # Diagnostic info
    INFO = "INFO"        # General events
    WARNING = "WARNING"  # Recoverable issues
    ERROR = "ERROR"      # Errors
    CRITICAL = "CRITICAL"  # System critical
```

#### LogEvent (Dataclass)
```python
@dataclass
class LogEvent:
    timestamp: datetime
    level: LogLevel
    message: str
    context: LogContext
    error: Optional[str] = None        # Error traceback
    metrics: Dict[str, Any] = field()  # Associated metrics
    metadata: Dict[str, Any] = field() # Additional context
```

#### StructuredLogger (Main Class)
```python
class StructuredLogger:
    def __init__(self, app_name: str, version: str)
    
    # Core logging
    async def debug(message, context, **metadata) -> LogEvent
    async def info(message, context, **metadata) -> LogEvent
    async def warning(message, context, **metadata) -> LogEvent
    async def error(message, context, error=None, **metadata) -> LogEvent
    async def critical(message, context, **metadata) -> LogEvent
    
    # Context management
    def create_context(request_id, component, **tags) -> LogContext
    def push_context(context: LogContext)
    def pop_context() -> LogContext
    
    # Async context manager
    async with logger.context(request_id='req123'):
        # Logging within this block uses context
        await logger.info("Operation started", context)
    
    # Configuration
    def set_level(level: LogLevel)
    def add_filter(filter_func: Callable[[LogEvent], bool])
    def add_output(output_handler: Callable[[LogEvent], Awaitable])
    
    # Querying
    async def get_recent_logs(limit=100) -> List[LogEvent]
    async def get_logs_by_context(context_filter) -> List[LogEvent]
    async def export_logs(start_time, end_time) -> List[Dict]
    
    # Statistics
    def get_stats() -> Dict  # Log counts by level, top components, etc.
```

### Output Format (JSON)
```json
{
  "timestamp": "2025-10-20T15:30:45.123Z",
  "level": "INFO",
  "message": "Policy check passed",
  "request_id": "req-abc-123",
  "component": "policy_engine",
  "module": "policy_engine.consent_broker",
  "tags": {"user_id": "user123", "action": "file_read"},
  "error": null,
  "metrics": {"risk_score": 0.15, "check_duration_ms": 2.5},
  "metadata": {"policy_id": "POL-001", "allowed": true}
}
```

### Key Features
- [x] Async logging (non-blocking)
- [x] Context propagation (request_id, user_id, session_id)
- [x] JSON serialization for log aggregation
- [x] Level-based filtering
- [x] Custom filters support
- [x] Multiple output handlers
- [x] Log history in memory (circular buffer)
- [x] Statistics tracking

---

## Module 2: MetricsCollector

**File:** `apps/core/metrics.py`  
**Target Lines:** 280 lines  

### Purpose
Prometheus-compatible metrics collection for performance monitoring and alerting.

### Metric Types

#### Counter
```python
counter.increment(labels={'component': 'policy', 'result': 'allowed'})
counter.add(5, labels={...})
```

#### Gauge
```python
gauge.set(value=42, labels={...})
gauge.increment(labels={...})
gauge.decrement(labels={...})
```

#### Histogram
```python
histogram.observe(value=0.025, labels={...})  # 25ms latency
# Automatically buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
```

#### Summary
```python
summary.observe(value=0.5, labels={...})
# Returns: count, sum, quantiles (0.5, 0.9, 0.99)
```

### Classes

#### MetricFamily (Enum)
```python
class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
```

#### Metric (Abstract Base)
```python
@dataclass
class Metric:
    name: str              # e.g., 'astra_events_processed_total'
    metric_type: MetricType
    help_text: str         # Description
    labels: List[str]      # Label names
    value: float = 0.0
    timestamp: datetime = field()
    
    def observe(value, labels=None)
    def to_prometheus_line() -> str
```

#### MetricsCollector (Main Class)
```python
class MetricsCollector:
    def __init__(self)
    
    # Metric registration
    def register_counter(name, help_text, labels=[]) -> Counter
    def register_gauge(name, help_text, labels=[]) -> Gauge
    def register_histogram(name, help_text, labels=[], buckets=None) -> Histogram
    def register_summary(name, help_text, labels=[], quantiles=None) -> Summary
    
    # Metric operations
    def increment_counter(name, labels=None, amount=1)
    def set_gauge(name, value, labels=None)
    def observe_histogram(name, value, labels=None)
    def observe_summary(name, value, labels=None)
    
    # Querying
    def get_metric(name) -> Metric
    def get_all_metrics() -> List[Metric]
    def get_metrics_by_component(component) -> List[Metric]
    
    # Export
    def export_prometheus_format() -> str  # Prometheus scrape format
    def export_json() -> Dict              # JSON export
    
    # Reset
    def reset_metric(name)
    def reset_all()
    
    # Statistics
    def get_collector_stats() -> Dict      # Registered count, total observes, etc.
```

### Built-in Metrics

```python
# Event routing
astra_events_processed_total (counter)
astra_events_routed (counter)
astra_events_latency_ms (histogram)
astra_events_queue_depth (gauge)

# Task scheduling
astra_tasks_scheduled_total (counter)
astra_tasks_executed_total (counter)
astra_tasks_failed_total (counter)
astra_tasks_duration_ms (histogram)

# Component health
astra_component_health (gauge)  # 1=HEALTHY, 0.5=DEGRADED, 0=UNHEALTHY
astra_component_checks_total (counter)
astra_component_failures_total (counter)

# Memory system
astra_memory_db_queries_total (counter)
astra_memory_db_latency_ms (histogram)
astra_memory_vector_searches (counter)
astra_memory_vectors_stored (gauge)

# Policy engine
astra_policy_checks_total (counter)
astra_policy_risk_score (summary)  # 0.0-1.0
astra_policy_denials (counter)

# Security
astra_threats_detected_total (counter)
astra_anomalies_detected (counter)
astra_incidents_bundles (gauge)
```

### Output Format (Prometheus)
```
# HELP astra_events_processed_total Total events processed
# TYPE astra_events_processed_total counter
astra_events_processed_total{component="policy",result="allowed"} 1234 1697800245123
astra_events_processed_total{component="policy",result="denied"} 12 1697800245123

# HELP astra_events_latency_ms Event routing latency in milliseconds
# TYPE astra_events_latency_ms histogram
astra_events_latency_ms_bucket{component="router",le="0.005"} 100 1697800245123
astra_events_latency_ms_bucket{component="router",le="0.01"} 250 1697800245123
astra_events_latency_ms_bucket{component="router",le="+Inf"} 1234 1697800245123
astra_events_latency_ms_sum{component="router"} 45.123 1697800245123
astra_events_latency_ms_count{component="router"} 1234 1697800245123

# HELP astra_component_health Component health status (1=HEALTHY, 0.5=DEGRADED, 0=UNHEALTHY)
# TYPE astra_component_health gauge
astra_component_health{component="boot_daemon"} 1 1697800245123
astra_component_health{component="event_bus"} 1 1697800245123
```

### Key Features
- [x] 4 metric types (Counter, Gauge, Histogram, Summary)
- [x] Dynamic label support
- [x] Prometheus-compatible export format
- [x] JSON export option
- [x] Automatic bucketing (histograms)
- [x] Quantile tracking (summaries)
- [x] Per-component metrics
- [x] Thread-safe collections

---

## Module 3: DistributedTracer

**File:** `apps/core/tracing.py`  
**Target Lines:** 270 lines  

### Purpose
OpenTelemetry-compatible distributed tracing for tracking request flow through system.

### Span Concept
```
Request Flow:
  ┌─────────────────────────────────────────────────────┐
  │ Root Span: policy_check (trace_id=abc123)           │
  │ [====================================================] 50ms
  │  ├─ Child Span: consent_check             [==] 10ms
  │  │  └─ Event: checked policy ID pol-001        
  │  ├─ Child Span: risk_score                [===] 15ms
  │  │  └─ Event: risk level calculated (0.25)
  │  └─ Child Span: record_decision           [=] 5ms
  │     └─ Event: decision recorded
  └─────────────────────────────────────────────────────┘
```

### Classes

#### SpanStatus (Enum)
```python
class SpanStatus(Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"
```

#### SpanEvent (Dataclass)
```python
@dataclass
class SpanEvent:
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field()
```

#### TraceSpan (Dataclass)
```python
@dataclass
class TraceSpan:
    trace_id: str               # Unique trace ID
    span_id: str                # Unique span ID
    parent_span_id: Optional[str] = None
    name: str = ""              # Operation name
    status: SpanStatus = SpanStatus.UNSET
    start_time: datetime = field()
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    attributes: Dict[str, Any] = field()
    events: List[SpanEvent] = field()
    error: Optional[str] = None
    
    def add_event(name, attributes=None)
    def set_status(status, error=None)
    def finish()
```

#### DistributedTracer (Main Class)
```python
class DistributedTracer:
    def __init__(self)
    
    # Span management
    def create_span(name, attributes=None, parent_span=None) -> TraceSpan
    def start_span(name, attributes=None) -> TraceSpan
    def finish_span(span: TraceSpan)
    
    # Async context manager
    async with tracer.span("policy_check", {"policy_id": "pol-001"}):
        # Operations within span
        tracer.add_event("Checked consent broker")
        tracer.add_event("Risk calculated", {"risk_score": 0.25})
    
    # Context propagation
    def inject_context(span) -> Dict  # For serialization
    def extract_context(context_dict) -> str  # Returns span_id
    
    # Querying
    def get_span(span_id) -> TraceSpan
    def get_trace(trace_id) -> List[TraceSpan]  # All spans in trace
    def get_traces(component=None) -> List[TraceSpan]
    
    # Export
    def export_jaeger_format() -> List[Dict]   # Jaeger export
    def export_zipkin_format() -> List[Dict]   # Zipkin export
    def export_json() -> List[Dict]            # Generic JSON
    
    # Statistics
    def get_tracer_stats() -> Dict  # Span count, avg duration, etc.
```

### Trace Output Format (JSON)
```json
{
  "trace_id": "abc123def456",
  "span_id": "xyz789",
  "parent_span_id": null,
  "name": "policy_check",
  "status": "OK",
  "start_time": "2025-10-20T15:30:45.100Z",
  "end_time": "2025-10-20T15:30:45.150Z",
  "duration_ms": 50,
  "attributes": {
    "policy_id": "pol-001",
    "component": "policy_engine"
  },
  "events": [
    {
      "name": "consent_checked",
      "timestamp": "2025-10-20T15:30:45.110Z",
      "attributes": {"consent": true}
    },
    {
      "name": "risk_calculated",
      "timestamp": "2025-10-20T15:30:45.130Z",
      "attributes": {"risk_score": 0.25}
    }
  ],
  "error": null
}
```

### Key Features
- [x] Distributed tracing with trace/span IDs
- [x] Parent-child span relationships
- [x] Span events with attributes
- [x] Error tracking
- [x] Duration measurement
- [x] Context propagation
- [x] Multiple export formats (Jaeger, Zipkin, JSON)
- [x] In-memory trace history

---

## Module 4: IncidentExporter

**File:** `apps/core/export.py`  
**Target Lines:** 260 lines  

### Purpose
Export security incidents, policy violations, and anomalies in structured formats.

### Classes

#### ExportFormat (Enum)
```python
class ExportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"  # JSON lines for streaming
    PARQUET = "parquet"  # For big data
```

#### IncidentRecord (Dataclass)
```python
@dataclass
class IncidentRecord:
    incident_id: str           # Unique ID
    timestamp: datetime
    severity: str              # critical/high/medium/low
    category: str              # threat/violation/anomaly/error
    component: str             # Source component
    message: str               # Description
    context: Dict[str, Any]    # Full context
    
    def to_dict() -> Dict
    def to_csv_row() -> str
```

#### ExportBatch (Dataclass)
```python
@dataclass
class ExportBatch:
    batch_id: str
    format: ExportFormat
    records: List[IncidentRecord]
    created_at: datetime
    exported_at: Optional[datetime] = None
    file_path: Optional[str] = None
    
    def add_record(record: IncidentRecord)
    def export_to_file(path)
    def export_to_string() -> str
```

#### IncidentExporter (Main Class)
```python
class IncidentExporter:
    def __init__(self, export_dir: str)
    
    # Recording incidents
    async def record_incident(category, severity, component, message, context)
    async def record_threat(threat_type, severity, context)
    async def record_violation(violation_type, component, context)
    async def record_anomaly(anomaly_type, confidence, context)
    
    # Batch management
    async def create_batch(format: ExportFormat) -> ExportBatch
    async def add_to_batch(batch_id, incident)
    async def finalize_batch(batch_id) -> str  # File path
    
    # Export
    async def export_incidents(start_time, end_time, format) -> str  # File path
    async def export_recent(limit=1000, format=ExportFormat.JSON) -> str
    
    # Querying
    async def get_incidents(start_time, end_time) -> List[IncidentRecord]
    async def get_by_category(category) -> List[IncidentRecord]
    async def get_by_severity(severity) -> List[IncidentRecord]
    async def get_by_component(component) -> List[IncidentRecord]
    
    # Statistics
    def get_export_stats() -> Dict  # Total incidents, by category, etc.
    
    # File rotation
    async def rotate_exports(keep_days=30)
```

### Export Format Examples

#### JSON Format
```json
[
  {
    "incident_id": "INC-2025-10-001",
    "timestamp": "2025-10-20T15:30:45.123Z",
    "severity": "high",
    "category": "threat",
    "component": "security_sentinel",
    "message": "Suspicious process creation detected",
    "context": {
      "process_name": "powershell.exe",
      "parent_process": "explorer.exe",
      "risk_score": 0.87,
      "threat_id": "THREAT-002"
    }
  }
]
```

#### CSV Format
```csv
incident_id,timestamp,severity,category,component,message,context
INC-2025-10-001,2025-10-20T15:30:45.123Z,high,threat,security_sentinel,Suspicious process creation detected,"{""process_name"": ""powershell.exe"", ""risk_score"": 0.87}"
```

#### JSONL Format (JSON Lines - one record per line)
```
{"incident_id": "INC-2025-10-001", "timestamp": "2025-10-20T15:30:45.123Z", ...}
{"incident_id": "INC-2025-10-002", "timestamp": "2025-10-20T15:30:46.456Z", ...}
```

### Key Features
- [x] Multiple export formats (JSON, CSV, JSONL, Parquet)
- [x] Incident categorization (threat, violation, anomaly, error)
- [x] Severity levels (critical, high, medium, low)
- [x] Batch export operations
- [x] Time-range filtering
- [x] Component-based filtering
- [x] File rotation and cleanup
- [x] Stream-friendly formats (JSONL, Parquet)

---

## Integration Points

### Event Bus Topics (Publishing)

```python
# StructuredLogger publishes
logs/event                    # New log event
logs/stats                    # Logging stats

# MetricsCollector publishes
metrics/counter_incremented   # Counter updated
metrics/gauge_set             # Gauge value changed
metrics/histogram_observed    # Histogram observation
metrics/export_ready          # Metrics ready for scrape

# DistributedTracer publishes
trace/span_started            # New span created
trace/span_finished           # Span completed
trace/span_error              # Error in span
trace/trace_completed         # All spans in trace complete

# IncidentExporter publishes
incidents/recorded            # Incident recorded
incidents/exported            # Batch exported
incidents/alert               # Incident alert
```

### Dependencies on Phases 1-10

```
StructuredLogger:
  ├─ Event Bus (publish logs)
  ├─ ConfigManager (log settings)
  └─ Health Monitor (log health events)

MetricsCollector:
  ├─ Event Bus (publish metrics)
  ├─ ConfigManager (metric settings)
  └─ RuntimeOrchestrator (track runtime metrics)

DistributedTracer:
  ├─ Event Bus (publish traces)
  ├─ ConfigManager (trace settings)
  └─ ActionRouter (trace event routing)

IncidentExporter:
  ├─ Event Bus (publish exports)
  ├─ StructuredLogger (log exports)
  ├─ Security Sentinel (incident data)
  └─ ConfigManager (export settings)
```

---

## Implementation Tasks

### Task 1: StructuredLogger (logging.py)
- [x] LogContext dataclass
- [x] LogLevel enum
- [x] LogEvent dataclass
- [x] StructuredLogger class with core methods
- [x] JSON formatting
- [x] Context stack management
- [x] Async logging
- [x] Log querying and statistics

**Estimated:** 250 lines

### Task 2: MetricsCollector (metrics.py)
- [x] MetricType enum
- [x] Counter, Gauge, Histogram, Summary classes
- [x] MetricsCollector registration and collection
- [x] Prometheus export format
- [x] JSON export format
- [x] Built-in metric definitions
- [x] Label support
- [x] Statistics tracking

**Estimated:** 280 lines

### Task 3: DistributedTracer (tracing.py)
- [x] SpanStatus enum
- [x] SpanEvent dataclass
- [x] TraceSpan dataclass
- [x] DistributedTracer class
- [x] Async context manager support
- [x] Context propagation
- [x] Export formats (Jaeger, Zipkin, JSON)
- [x] Trace querying

**Estimated:** 270 lines

### Task 4: IncidentExporter (export.py)
- [x] ExportFormat enum
- [x] IncidentRecord dataclass
- [x] ExportBatch dataclass
- [x] IncidentExporter class
- [x] Multiple export formats
- [x] Incident recording and categorization
- [x] Batch operations
- [x] File rotation

**Estimated:** 260 lines

### Task 5: Package Init (__init__.py)
- [x] Export all classes and enums
- [x] Version info
- [x] Clean public API

**Estimated:** 30 lines

### Task 6: Comprehensive Tests (test_observability.py)
- [x] StructuredLogger tests (6 tests)
- [x] MetricsCollector tests (6 tests)
- [x] DistributedTracer tests (6 tests)
- [x] IncidentExporter tests (6 tests)
- [x] Integration tests (4 tests)
- [x] Performance tests (3 tests)

**Estimated:** 400+ lines, 30+ test cases

---

## File Structure

```
apps/core/
├── observability.py        # Combined observability module (optional)
├── logging.py              # StructuredLogger (250 lines)
├── metrics.py              # MetricsCollector (280 lines)
├── tracing.py              # DistributedTracer (270 lines)
├── export.py               # IncidentExporter (260 lines)
└── __init__.py             # Package init + exports (30 lines)

tests/
└── test_observability.py   # Comprehensive tests (400+ lines, 30+ cases)
```

---

## Success Criteria

- [x] StructuredLogger: JSON logging with context propagation
- [x] MetricsCollector: Prometheus-compatible metrics
- [x] DistributedTracer: OpenTelemetry-compatible tracing
- [x] IncidentExporter: JSON/CSV incident export
- [x] 1,100+ lines of production code (target: 500+)
- [x] 400+ lines of test code (30+ test cases)
- [x] Full integration with Event Bus
- [x] Zero blocking errors
- [x] Production-ready code quality
- [x] Comprehensive documentation

---

## Timeline

1. **StructuredLogger Implementation** → 30 minutes
2. **MetricsCollector Implementation** → 30 minutes
3. **DistributedTracer Implementation** → 30 minutes
4. **IncidentExporter Implementation** → 30 minutes
5. **Test Suite Creation** → 30 minutes
6. **Documentation & Verification** → 20 minutes

**Total:** ~2.5 hours for Phase 11 complete

---

## Reference: Prometheus Metric Naming Convention

```
<namespace>_<subsystem>_<name>_<unit>

Examples:
- astra_events_processed_total (counter)
- astra_events_latency_milliseconds (histogram)
- astra_component_health (gauge)
- astra_policy_risk_score (summary)

Namespace: astra
Subsystems: events, component, policy, memory, threat, etc.
Name: What is being measured
Unit: total, milliseconds, bytes, etc.
```

---

## Reference: OpenTelemetry Attributes

```python
# Resource attributes
resource.service.name = "astra"
resource.service.version = "1.0.0"
resource.os.type = "windows"

# Span attributes
span.component = "policy_engine"
span.operation = "check_consent"
span.user_id = "user123"
span.request_id = "req-abc-123"

# Standard status codes
status.code = "OK" | "ERROR" | "UNSET"
status.description = "Optional error message"
```

---

## Next Phase Preview

**Phase 12: Testing & Hardening**
- Comprehensive unit/integration tests
- Security vulnerability scanning
- Chaos engineering tests
- Performance benchmarks
- Coverage >90%

