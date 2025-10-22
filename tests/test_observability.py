"""
Phase 11: Observability & Monitoring - Comprehensive Test Suite

Tests for StructuredLogger, MetricsCollector, DistributedTracer, and IncidentExporter.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

# Import modules (adjust paths as needed)
from apps.core.logging import StructuredLogger, LogLevel, LogContext
from apps.core.metrics import MetricsCollector, MetricType
from apps.core.tracing import DistributedTracer, SpanStatus
from apps.core.export import IncidentExporter, IncidentCategory, SeverityLevel, ExportFormat


# ============================================================================
# StructuredLogger Tests
# ============================================================================

class TestStructuredLogger:
    """Tests for StructuredLogger."""
    
    @pytest.fixture
    def logger(self):
        """Create logger instance."""
        return StructuredLogger("test_app", "1.0.0")
    
    @pytest.mark.asyncio
    async def test_debug_logging(self, logger):
        """Test debug level logging."""
        context = logger.create_context("req-001", component="test")
        event = await logger.debug("Debug message", context)
        
        assert event is not None
        assert event.level == LogLevel.DEBUG
        assert event.message == "Debug message"
        assert event.context.request_id == "req-001"
    
    @pytest.mark.asyncio
    async def test_info_logging(self, logger):
        """Test info level logging."""
        context = logger.create_context("req-002", component="test")
        event = await logger.info("Info message", context)
        
        assert event is not None
        assert event.level == LogLevel.INFO
        assert event.message == "Info message"
    
    @pytest.mark.asyncio
    async def test_error_logging(self, logger):
        """Test error level logging with exception."""
        context = logger.create_context("req-003", component="test")
        try:
            raise ValueError("Test error")
        except ValueError as e:
            event = await logger.error("Error occurred", context, error=e)
        
        assert event is not None
        assert event.level == LogLevel.ERROR
        assert event.error is not None
        assert "ValueError" in event.error
    
    @pytest.mark.asyncio
    async def test_context_stack(self, logger):
        """Test context push/pop."""
        context1 = logger.create_context("req-001", component="comp1")
        logger.push_context(context1)
        
        context2 = logger.pop_context()
        assert context2.request_id == "req-001"
        assert context2.component == "comp1"
    
    @pytest.mark.asyncio
    async def test_log_filtering(self, logger):
        """Test log filtering."""
        logger.set_level(LogLevel.WARNING)
        
        context = logger.create_context("req-004")
        
        # These should be filtered
        event1 = await logger.debug("Debug message", context)
        event2 = await logger.info("Info message", context)
        
        # This should pass
        event3 = await logger.warning("Warning message", context)
        
        assert event1 is None
        assert event2 is None
        assert event3 is not None
    
    @pytest.mark.asyncio
    async def test_get_recent_logs(self, logger):
        """Test retrieving recent logs."""
        context = logger.create_context("req-005")
        
        await logger.info("Message 1", context)
        await logger.info("Message 2", context)
        await logger.info("Message 3", context)
        
        logs = await logger.get_recent_logs(limit=2)
        assert len(logs) == 2
        assert logs[-1].message == "Message 3"
    
    @pytest.mark.asyncio
    async def test_get_logs_by_context(self, logger):
        """Test filtering logs by context."""
        ctx1 = logger.create_context("req-001", component="comp1")
        ctx2 = logger.create_context("req-002", component="comp2")
        
        await logger.info("Message 1", ctx1)
        await logger.info("Message 2", ctx2)
        await logger.info("Message 3", ctx1)
        
        logs = await logger.get_logs_by_context(request_id="req-001")
        assert len(logs) == 2
    
    @pytest.mark.asyncio
    async def test_log_event_to_json(self, logger):
        """Test converting log event to JSON."""
        context = logger.create_context("req-006", component="test", user_id="user1")
        event = await logger.info("Test message", context, extra_data="value")
        
        json_str = event.to_json()
        data = json.loads(json_str)
        
        assert data['message'] == "Test message"
        assert data['component'] == "test"
        assert data['user_id'] == "user1"
    
    @pytest.mark.asyncio
    async def test_logger_statistics(self, logger):
        """Test logger statistics."""
        context = logger.create_context("req-007")
        
        await logger.debug("Debug", context)
        await logger.info("Info", context)
        await logger.warning("Warning", context)
        await logger.error("Error", context)
        
        stats = logger.get_stats()
        
        assert stats['debug'] == 1
        assert stats['info'] == 1
        assert stats['warning'] == 1
        assert stats['error'] == 1


# ============================================================================
# MetricsCollector Tests
# ============================================================================

class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create collector instance."""
        return MetricsCollector()
    
    def test_counter_registration(self, collector):
        """Test registering a counter metric."""
        counter = collector.register_counter(
            'test_counter',
            'Test counter metric',
            labels=['component', 'status']
        )
        
        assert counter is not None
        assert counter.name == 'test_counter'
        assert 'test_counter' in [m.name for m in collector.get_all_metrics()]
    
    def test_counter_increment(self, collector):
        """Test counter increment."""
        counter = collector.register_counter('events_total', 'Total events')
        
        counter.increment(labels={'component': 'policy'})
        counter.increment(labels={'component': 'policy'}, amount=5)
        
        values = counter.get_values()
        assert values['component=policy'] == 6
    
    def test_gauge_operations(self, collector):
        """Test gauge operations."""
        gauge = collector.register_gauge('queue_depth', 'Queue depth')
        
        gauge.set(10, labels={'queue': 'events'})
        gauge.increment(labels={'queue': 'events'})
        gauge.decrement(labels={'queue': 'events'})
        
        values = gauge.get_values()
        assert values['queue=events'] == 10
    
    def test_histogram_observations(self, collector):
        """Test histogram observations."""
        histogram = collector.register_histogram(
            'latency_ms',
            'Latency in milliseconds'
        )
        
        histogram.observe(0.015, labels={'component': 'router'})
        histogram.observe(0.025, labels={'component': 'router'})
        histogram.observe(0.035, labels={'component': 'router'})
        
        assert len(histogram._observations) > 0
    
    def test_summary_observations(self, collector):
        """Test summary observations."""
        summary = collector.register_summary(
            'request_duration',
            'Request duration'
        )
        
        summary.observe(0.1, labels={'endpoint': '/api'})
        summary.observe(0.2, labels={'endpoint': '/api'})
        summary.observe(0.15, labels={'endpoint': '/api'})
        
        assert len(summary._observations) > 0
    
    def test_prometheus_export(self, collector):
        """Test Prometheus format export."""
        counter = collector.register_counter('total_events', 'Total events')
        counter.increment(labels={'component': 'test'})
        
        prometheus_str = collector.export_prometheus_format()
        
        assert 'HELP total_events' in prometheus_str
        assert 'TYPE total_events counter' in prometheus_str
        assert 'total_events' in prometheus_str
    
    def test_json_export(self, collector):
        """Test JSON export."""
        counter = collector.register_counter('test_counter', 'Test counter')
        counter.increment(labels={'status': 'ok'})
        
        json_data = collector.export_json()
        
        assert 'test_counter' in json_data
        assert json_data['test_counter']['status=ok'] == 1
    
    def test_collector_statistics(self, collector):
        """Test collector statistics."""
        collector.register_counter('counter1', 'Counter 1')
        collector.register_gauge('gauge1', 'Gauge 1')
        collector.register_histogram('histogram1', 'Histogram 1')
        collector.register_summary('summary1', 'Summary 1')
        
        stats = collector.get_collector_stats()
        
        assert stats['total_metrics'] == 4
        assert stats['counters'] == 1
        assert stats['gauges'] == 1
        assert stats['histograms'] == 1
        assert stats['summaries'] == 1
    
    def test_reset_metric(self, collector):
        """Test resetting a metric."""
        counter = collector.register_counter('counter_reset', 'Counter to reset')
        counter.increment(labels={'test': 'value'})
        
        collector.reset_metric('counter_reset')
        
        values = counter.get_values()
        assert len(values) == 0
    
    def test_reset_all_metrics(self, collector):
        """Test resetting all metrics."""
        counter = collector.register_counter('counter1', 'Counter 1')
        gauge = collector.register_gauge('gauge1', 'Gauge 1')
        
        counter.increment()
        gauge.set(42)
        
        collector.reset_all()
        
        assert len(counter.get_values()) == 0
        assert len(gauge.get_values()) == 0


# ============================================================================
# DistributedTracer Tests
# ============================================================================

class TestDistributedTracer:
    """Tests for DistributedTracer."""
    
    @pytest.fixture
    def tracer(self):
        """Create tracer instance."""
        return DistributedTracer("test_service")
    
    def test_span_creation(self, tracer):
        """Test creating a span."""
        span = tracer.create_span("test_operation")
        
        assert span is not None
        assert span.name == "test_operation"
        assert span.status == SpanStatus.UNSET
    
    def test_span_parent_child(self, tracer):
        """Test parent-child span relationship."""
        parent = tracer.create_span("parent")
        child = tracer.create_span("child", parent_span=parent)
        
        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id
    
    def test_span_attributes(self, tracer):
        """Test setting span attributes."""
        span = tracer.create_span(
            "operation",
            attributes={'user_id': 'user123', 'action': 'read'}
        )
        
        assert span.attributes['user_id'] == 'user123'
        assert span.attributes['action'] == 'read'
    
    def test_span_events(self, tracer):
        """Test adding events to span."""
        span = tracer.create_span("operation")
        
        span.add_event("started")
        span.add_event("processing", {'items': 5})
        span.add_event("finished")
        
        assert len(span.events) == 3
        assert span.events[1].name == "processing"
        assert span.events[1].attributes['items'] == 5
    
    def test_span_status(self, tracer):
        """Test setting span status."""
        span = tracer.create_span("operation")
        
        span.set_status(SpanStatus.OK)
        assert span.status == SpanStatus.OK
        
        span.set_status(SpanStatus.ERROR, "Something went wrong")
        assert span.status == SpanStatus.ERROR
        assert span.error == "Something went wrong"
    
    def test_span_finish(self, tracer):
        """Test finishing a span."""
        span = tracer.create_span("operation")
        start_time = span.start_time
        
        span.finish()
        
        assert span.end_time is not None
        assert span.end_time >= start_time
        assert span.duration_ms >= 0
    
    def test_get_trace(self, tracer):
        """Test retrieving a trace."""
        parent = tracer.create_span("parent")
        child = tracer.create_span("child", parent_span=parent)
        
        trace = tracer.get_trace(parent.trace_id)
        
        assert len(trace) == 2
        assert trace[0].name == "parent"
        assert trace[1].name == "child"
    
    def test_context_injection(self, tracer):
        """Test context injection for propagation."""
        span = tracer.create_span("operation")
        
        context = tracer.inject_context(span)
        
        assert context['trace_id'] == span.trace_id
        assert context['span_id'] == span.span_id
    
    def test_context_extraction(self, tracer):
        """Test context extraction."""
        original_span = tracer.create_span("original")
        context = tracer.inject_context(original_span)
        
        extracted_span_id = tracer.extract_context(context)
        
        assert extracted_span_id is not None
        extracted_span = tracer.get_span(extracted_span_id)
        assert extracted_span.trace_id == original_span.trace_id
    
    def test_export_json(self, tracer):
        """Test exporting traces as JSON."""
        span = tracer.create_span("operation", attributes={'user': 'user1'})
        span.add_event("test_event")
        span.finish()
        
        json_data = tracer.export_json()
        
        assert len(json_data) > 0
        assert json_data[0]['name'] == "operation"
        assert len(json_data[0]['events']) > 0
    
    def test_tracer_statistics(self, tracer):
        """Test tracer statistics."""
        tracer.create_span("span1")
        tracer.create_span("span2")
        tracer.create_span("span3")
        
        stats = tracer.get_tracer_stats()
        
        assert stats['spans_created'] == 3
        assert stats['total_spans'] == 3


# ============================================================================
# IncidentExporter Tests
# ============================================================================

class TestIncidentExporter:
    """Tests for IncidentExporter."""
    
    @pytest.fixture
    def exporter(self):
        """Create exporter instance with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield IncidentExporter(tmpdir)
    
    @pytest.mark.asyncio
    async def test_record_incident(self, exporter):
        """Test recording an incident."""
        record = await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='security',
            message='Test threat detected',
            context={'threat_id': 'THR-001'}
        )
        
        assert record.incident_id is not None
        assert record.category == IncidentCategory.THREAT
        assert record.severity == SeverityLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_record_threat(self, exporter):
        """Test recording a threat."""
        record = await exporter.record_threat(
            threat_type='malware',
            severity=SeverityLevel.CRITICAL,
            context={'file': 'test.exe'}
        )
        
        assert record.category == IncidentCategory.THREAT
        assert record.component == 'security_sentinel'
    
    @pytest.mark.asyncio
    async def test_record_violation(self, exporter):
        """Test recording a violation."""
        record = await exporter.record_violation(
            violation_type='policy_denied',
            component='policy_engine',
            context={'policy_id': 'POL-001'}
        )
        
        assert record.category == IncidentCategory.VIOLATION
        assert record.severity == SeverityLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_record_anomaly(self, exporter):
        """Test recording an anomaly."""
        record = await exporter.record_anomaly(
            anomaly_type='unusual_activity',
            confidence=0.95,
            component='anomaly_detector',
            context={'activity': 'high_mem_usage'}
        )
        
        assert record.category == IncidentCategory.ANOMALY
        assert record.severity == SeverityLevel.CRITICAL
    
    @pytest.mark.asyncio
    async def test_create_batch(self, exporter):
        """Test creating a batch."""
        batch_id = await exporter.create_batch(ExportFormat.JSON)
        
        assert batch_id is not None
        assert batch_id.startswith('BATCH-')
    
    @pytest.mark.asyncio
    async def test_add_to_batch(self, exporter):
        """Test adding records to batch."""
        batch_id = await exporter.create_batch(ExportFormat.JSON)
        
        record = await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='test',
            message='Test'
        )
        
        await exporter.add_to_batch(batch_id, record)
        
        assert len(exporter._batches[batch_id].records) == 1
    
    @pytest.mark.asyncio
    async def test_export_json(self, exporter):
        """Test exporting to JSON."""
        record = await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='test',
            message='Test incident'
        )
        
        file_path = await exporter.export_recent(limit=10, format=ExportFormat.JSON)
        
        assert Path(file_path).exists()
        with open(file_path) as f:
            data = json.load(f)
            assert len(data) > 0
    
    @pytest.mark.asyncio
    async def test_get_incidents(self, exporter):
        """Test retrieving incidents."""
        await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='comp1',
            message='Incident 1'
        )
        await exporter.record_incident(
            category=IncidentCategory.VIOLATION,
            severity=SeverityLevel.MEDIUM,
            component='comp2',
            message='Incident 2'
        )
        
        incidents = await exporter.get_incidents()
        assert len(incidents) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_category(self, exporter):
        """Test filtering incidents by category."""
        await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='test',
            message='Threat'
        )
        await exporter.record_incident(
            category=IncidentCategory.VIOLATION,
            severity=SeverityLevel.HIGH,
            component='test',
            message='Violation'
        )
        
        threats = await exporter.get_by_category(IncidentCategory.THREAT)
        assert len(threats) == 1
        assert threats[0].category == IncidentCategory.THREAT
    
    @pytest.mark.asyncio
    async def test_get_by_severity(self, exporter):
        """Test filtering incidents by severity."""
        await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.CRITICAL,
            component='test',
            message='Critical'
        )
        await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.LOW,
            component='test',
            message='Low'
        )
        
        critical = await exporter.get_by_severity(SeverityLevel.CRITICAL)
        assert len(critical) == 1
    
    @pytest.mark.asyncio
    async def test_export_statistics(self, exporter):
        """Test export statistics."""
        await exporter.record_incident(
            category=IncidentCategory.THREAT,
            severity=SeverityLevel.HIGH,
            component='comp1',
            message='Incident'
        )
        
        stats = exporter.get_export_stats()
        
        assert stats['total_incidents'] == 1
        assert stats['by_category']['threat'] == 1
        assert stats['by_severity']['high'] == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests across observability modules."""
    
    @pytest.mark.asyncio
    async def test_logger_with_metrics(self):
        """Test logger feeding into metrics."""
        logger = StructuredLogger("app")
        collector = MetricsCollector()
        
        context = logger.create_context("req-001", component="test")
        
        # Log events
        await logger.info("Event 1", context)
        await logger.info("Event 2", context)
        
        # Register and update metric
        counter = collector.register_counter("logs_total", "Total logs")
        logs = await logger.get_recent_logs(limit=10)
        counter.increment(labels={'component': 'test'}, amount=len(logs))
        
        stats = collector.get_collector_stats()
        assert stats['total_observations'] == 2
    
    @pytest.mark.asyncio
    async def test_tracer_with_incidents(self):
        """Test tracer with incident exporting."""
        tracer = DistributedTracer("service")
        exporter = IncidentExporter()
        
        span = tracer.create_span("operation")
        span.add_event("processing")
        
        # Record incident when operation finishes
        await exporter.record_incident(
            category=IncidentCategory.ERROR,
            severity=SeverityLevel.MEDIUM,
            component='tracer',
            message=f'Trace {span.trace_id} completed',
            context={'span_id': span.span_id, 'duration_ms': span.duration_ms}
        )
        
        incidents = await exporter.get_incidents()
        assert len(incidents) > 0
    
    @pytest.mark.asyncio
    async def test_full_observability_flow(self):
        """Test full observability flow."""
        logger = StructuredLogger("app")
        collector = MetricsCollector()
        tracer = DistributedTracer("service")
        exporter = IncidentExporter()
        
        # Simulate operation with full observability
        context = logger.create_context("req-001", component="api")
        
        span = tracer.create_span("request_handler")
        
        await logger.info("Request received", context)
        span.add_event("request_received")
        
        events_counter = collector.register_counter("events_total", "Total events")
        events_counter.increment(labels={'component': 'api'})
        
        span.set_status(SpanStatus.OK)
        span.finish()
        
        await logger.info("Request completed", context)
        
        # Export everything
        logs = await logger.get_recent_logs(limit=10)
        metrics = collector.export_prometheus_format()
        traces = tracer.export_json()
        
        assert len(logs) > 0
        assert len(metrics) > 0
        assert len(traces) > 0


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance tests for observability modules."""
    
    @pytest.mark.asyncio
    async def test_logging_throughput(self):
        """Test logging throughput."""
        logger = StructuredLogger("app", max_history=10000)
        context = logger.create_context("req-001", component="perf")
        
        start = datetime.utcnow()
        for i in range(1000):
            await logger.info(f"Message {i}", context)
        duration = (datetime.utcnow() - start).total_seconds()
        
        throughput = 1000 / duration
        assert throughput > 100  # At least 100 msgs/sec
    
    def test_metrics_observation_rate(self):
        """Test metrics observation rate."""
        collector = MetricsCollector()
        histogram = collector.register_histogram("latency", "Latency")
        
        start = datetime.utcnow()
        for i in range(1000):
            histogram.observe(0.01 + (i % 100) / 10000)
        duration = (datetime.utcnow() - start).total_seconds()
        
        rate = 1000 / duration
        assert rate > 1000  # At least 1000 obs/sec
    
    def test_span_creation_rate(self):
        """Test span creation rate."""
        tracer = DistributedTracer("service", max_traces=100)
        
        start = datetime.utcnow()
        for i in range(1000):
            tracer.create_span(f"operation_{i}")
        duration = (datetime.utcnow() - start).total_seconds()
        
        rate = 1000 / duration
        assert rate > 500  # At least 500 spans/sec
