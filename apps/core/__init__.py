"""
ASTRA-OS Core Module

Central orchestration, runtime management, and observability engine for ASTRA-OS.

Provides:
- Phase 10: Orchestration & Runtime
  - RuntimeOrchestrator: Main orchestration controller
  - EventLoop: Core async event loop
  - ActionRouter: Intelligent event routing
  - ScheduleManager: Task scheduling
  - ConfigManager: Dynamic configuration
  - HealthMonitor: Component health tracking

- Phase 11: Observability & Monitoring
  - StructuredLogger: JSON-based event logging
  - MetricsCollector: Prometheus-compatible metrics
  - DistributedTracer: OpenTelemetry-compatible tracing
  - IncidentExporter: Incident and alert export

Usage:
    from apps.core import RuntimeOrchestrator, EventLoop, StructuredLogger
    
    orchestrator = RuntimeOrchestrator()
    await orchestrator.initialize()
    await orchestrator.start()
"""

# Phase 10: Orchestration & Runtime
from .orchestrator import RuntimeOrchestrator, RuntimeState, RuntimeMetrics, ComponentStatus
from .event_loop import EventLoop, EventLoopState, TaskContext
from .router import ActionRouter, RoutePattern, RoutingRule, RoutingStatistics
from .scheduler import ScheduleManager, ScheduleType, ScheduledTask
from .config import ConfigManager, ConfigSource, ConfigChange, ConfigValidator
from .health import HealthMonitor, ComponentHealth, HealthMetric, HealthCheck

# Phase 11: Observability & Monitoring
from .logging import StructuredLogger, LogContext, LogLevel, LogEvent, get_logger, set_logger
from .metrics import MetricsCollector, Counter, Gauge, Histogram, Summary, MetricType, get_collector, set_collector
from .tracing import DistributedTracer, TraceSpan, SpanEvent, SpanStatus, get_tracer, set_tracer
from .export import (
    IncidentExporter, IncidentRecord, ExportBatch, ExportFormat,
    IncidentCategory, SeverityLevel, get_exporter, set_exporter
)

__all__ = [
    # Phase 10: Orchestration & Runtime
    # Orchestrator
    'RuntimeOrchestrator',
    'RuntimeState',
    'RuntimeMetrics',
    'ComponentStatus',
    # EventLoop
    'EventLoop',
    'EventLoopState',
    'TaskContext',
    # Router
    'ActionRouter',
    'RoutePattern',
    'RoutingRule',
    'RoutingStatistics',
    # Scheduler
    'ScheduleManager',
    'ScheduleType',
    'ScheduledTask',
    # Config
    'ConfigManager',
    'ConfigSource',
    'ConfigChange',
    'ConfigValidator',
    # Health
    'HealthMonitor',
    'ComponentHealth',
    'HealthMetric',
    'HealthCheck',
    
    # Phase 11: Observability & Monitoring
    # Logging
    'StructuredLogger',
    'LogContext',
    'LogLevel',
    'LogEvent',
    'get_logger',
    'set_logger',
    # Metrics
    'MetricsCollector',
    'Counter',
    'Gauge',
    'Histogram',
    'Summary',
    'MetricType',
    'get_collector',
    'set_collector',
    # Tracing
    'DistributedTracer',
    'TraceSpan',
    'SpanEvent',
    'SpanStatus',
    'get_tracer',
    'set_tracer',
    # Export
    'IncidentExporter',
    'IncidentRecord',
    'ExportBatch',
    'ExportFormat',
    'IncidentCategory',
    'SeverityLevel',
    'get_exporter',
    'set_exporter',
]
