"""Integration tests for ASTRA observability (logging and metrics)."""

import json
import tempfile
from pathlib import Path

from astra.observability.metrics import MetricsCollector
from astra.observability.structured_logger import StructuredLogger


class TestStructuredLogger:
    """Test structured logger functionality."""

    def test_logger_initialization(self) -> None:
        """Test logger can be initialized with custom paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(
                log_path=log_path,
                level="INFO",
                service_name="TEST",
            )

            assert logger.log_path == log_path
            assert logger.service_name == "TEST"
            assert logger.level == "INFO"

    def test_correlation_id_generation(self) -> None:
        """Test correlation ID is generated automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            corr_id1 = logger.get_correlation_id()
            corr_id2 = logger.get_correlation_id()

            # Same context should return same ID
            assert corr_id1 == corr_id2
            assert len(corr_id1) == 36  # UUID4 length

    def test_correlation_id_explicit_setting(self) -> None:
        """Test correlation ID can be explicitly set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            custom_id = "custom-correlation-id"
            logger.set_correlation_id(custom_id)

            assert logger.get_correlation_id() == custom_id

    def test_log_event_writes_jsonl(self) -> None:
        """Test log event is written to JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            corr_id = logger.log_event(
                "test_event",
                level="INFO",
                action="test",
                status="success",
            )

            assert Path(log_path).exists()

            # Read and verify JSONL
            with open(log_path) as f:
                entry = json.loads(f.readline())

            assert entry["event"] == "test_event"
            assert entry["level"] == "INFO"
            assert entry["correlation_id"] == corr_id
            assert entry["context"]["action"] == "test"
            assert entry["service"] == "ASTRA"

    def test_log_request_response_flow(self) -> None:
        """Test request-response logging flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            # Log request
            corr_id = logger.log_request(
                "vector_search",
                agent_id="agent-1",
                query="test query",
            )

            # Log response
            logger.log_response(
                "vector_search",
                agent_id="agent-1",
                status="success",
                duration_ms=45.5,
                result_count=5,
            )

            # Verify both in file
            with open(log_path) as f:
                lines = f.readlines()

            assert len(lines) == 2
            req = json.loads(lines[0])
            resp = json.loads(lines[1])

            assert "request_start" in req["event"]
            assert "request_complete" in resp["event"]
            assert req["correlation_id"] == resp["correlation_id"] == corr_id

    def test_log_error_with_context(self) -> None:
        """Test error logging with context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            logger.log_error(
                "vector_search",
                error="Connection timeout",
                error_type="TimeoutError",
                retry_count=3,
                endpoint="http://localhost:8000",
            )

            with open(log_path) as f:
                entry = json.loads(f.readline())

            assert entry["level"] == "ERROR"
            assert "error:" in entry["event"]
            assert entry["context"]["error"] == "Connection timeout"
            assert entry["context"]["error_type"] == "TimeoutError"

    def test_log_performance_threshold(self) -> None:
        """Test performance logging with threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            # Within threshold
            logger.log_performance(
                "inference",
                duration_ms=50.0,
                threshold_ms=100.0,
            )

            # Exceed threshold
            logger.log_performance(
                "inference",
                duration_ms=150.0,
                threshold_ms=100.0,
            )

            with open(log_path) as f:
                lines = f.readlines()

            entry1 = json.loads(lines[0])
            entry2 = json.loads(lines[1])

            assert entry1["level"] == "INFO"
            assert entry1["context"]["exceeded"] is False

            assert entry2["level"] == "WARNING"
            assert entry2["context"]["exceeded"] is True

    def test_get_logs_recent(self) -> None:
        """Test retrieving recent logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            for i in range(10):
                logger.log_event(f"event_{i}")

            logs = logger.get_logs(limit=5)

            assert len(logs) == 5
            assert logs[0]["event"] == "event_5"
            assert logs[-1]["event"] == "event_9"

    def test_get_correlation_logs(self) -> None:
        """Test retrieving logs by correlation ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            corr_id1 = logger.log_event("event_1")
            logger.log_event("event_2")
            logger.set_correlation_id(corr_id1)
            logger.log_event("event_3")

            logs = logger.get_correlation_logs(corr_id1)

            assert len(logs) >= 2
            assert all(log["correlation_id"] == corr_id1 for log in logs)

    def test_get_operation_logs(self) -> None:
        """Test retrieving logs by operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            logger.log_event("request_start:inference", level="INFO")
            logger.log_event("performance:inference", level="DEBUG")
            logger.log_event("request_complete:inference", level="INFO")
            logger.log_event("request_start:retrieval", level="INFO")

            logs = logger.get_operation_logs("inference")

            assert len(logs) == 3
            assert all("inference" in log["event"] for log in logs)


class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_metrics_collector_initialization(self) -> None:
        """Test metrics collector initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = str(Path(tmpdir) / "metrics.jsonl")
            collector = MetricsCollector(metrics_path=metrics_path)

            assert collector.metrics_path == metrics_path
            assert len(collector.gauges) == 0
            assert len(collector.counters) == 0
            assert len(collector.histograms) == 0

    def test_record_latency(self) -> None:
        """Test recording latency metrics."""
        collector = MetricsCollector()

        collector.record_latency("inference_latency", 45.5)
        collector.record_latency("inference_latency", 50.2)
        collector.record_latency("inference_latency", 48.9)

        latencies = collector.histograms["inference_latency"]
        assert len(latencies) == 3
        assert 45.5 in latencies

    def test_record_gauge(self) -> None:
        """Test recording gauge metrics."""
        collector = MetricsCollector()

        collector.record_gauge("gpu_memory", 4096.0)
        collector.record_gauge("cpu_usage", 45.5)

        assert collector.gauges["gpu_memory"] == 4096.0
        assert collector.gauges["cpu_usage"] == 45.5

    def test_increment_counter(self) -> None:
        """Test incrementing counter metrics."""
        collector = MetricsCollector()

        val1 = collector.increment_counter("total_requests")
        val2 = collector.increment_counter("total_requests", amount=5)

        assert val1 == 1
        assert val2 == 6
        assert collector.get_counter("total_requests") == 6

    def test_get_latency_percentiles(self) -> None:
        """Test getting latency percentiles."""
        collector = MetricsCollector()

        # Add 100 samples
        for i in range(1, 101):
            collector.record_latency("test_latency", float(i))

        percentiles = collector.get_latency_percentiles(
            "test_latency",
            percentiles=[50, 95, 99],
        )

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # Verify ordering
        assert percentiles["p50"] <= percentiles["p95"]
        assert percentiles["p95"] <= percentiles["p99"]

    def test_get_latency_stats(self) -> None:
        """Test getting latency statistics."""
        collector = MetricsCollector()

        for val in [10.0, 20.0, 30.0, 40.0, 50.0]:
            collector.record_latency("latency", val)

        stats = collector.get_latency_stats("latency")

        assert stats is not None
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0

    def test_export_metrics(self) -> None:
        """Test exporting all metrics."""
        collector = MetricsCollector()

        collector.record_latency("inference", 45.0)
        collector.record_gauge("gpu_memory", 4096.0)
        collector.increment_counter("total_requests", amount=10)

        export = collector.export_metrics()

        assert "timestamp" in export
        assert "gauges" in export
        assert "counters" in export
        assert "histograms" in export

        assert export["gauges"]["gpu_memory"] == 4096.0
        assert export["counters"]["total_requests"] == 10

    def test_write_metrics_snapshot(self) -> None:
        """Test writing metrics snapshot to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = str(Path(tmpdir) / "metrics.jsonl")
            collector = MetricsCollector(metrics_path=metrics_path)

            collector.record_gauge("gpu_memory", 4096.0)
            collector.increment_counter("total_requests", amount=5)

            collector.write_metrics_snapshot("checkpoint_1")

            assert Path(metrics_path).exists()

            with open(metrics_path) as f:
                data = json.loads(f.readline())

            assert data["snapshot_name"] == "checkpoint_1"
            assert data["gauges"]["gpu_memory"] == 4096.0

    def test_get_metrics_summary(self) -> None:
        """Test getting metrics summary."""
        collector = MetricsCollector()

        collector.record_gauge("active_requests", 5.0)
        collector.increment_counter("total_requests", amount=100)
        collector.increment_counter("errors_total", amount=2)
        collector.record_latency("llm_inference_latency", 50.0)

        summary = collector.get_metrics_summary()

        assert summary["active_requests"] == 5.0
        assert summary["total_requests"] == 100
        assert summary["total_errors"] == 2
        assert summary["llm_latency"] is not None

    def test_reset_metrics(self) -> None:
        """Test resetting all metrics."""
        collector = MetricsCollector()

        collector.record_gauge("gpu_memory", 4096.0)
        collector.record_latency("latency", 50.0)
        collector.increment_counter("requests", amount=10)

        assert len(collector.gauges) > 0

        collector.reset_metrics()

        assert len(collector.gauges) == 0
        assert len(collector.counters) == 0
        assert len(collector.histograms) == 0

    def test_get_histogram_buckets(self) -> None:
        """Test getting histogram buckets."""
        collector = MetricsCollector()

        for i in range(1, 101):
            collector.record_latency("latency", float(i * 5))

        buckets = collector.get_histogram_buckets(
            "latency",
            bucket_boundaries=[50, 100, 250, 500],
        )

        assert "50ms" in buckets
        assert "100ms" in buckets
        assert buckets["50ms"] > 0
        assert buckets["500ms"] > buckets["50ms"]

    def test_thread_safe_metrics(self) -> None:
        """Test metrics collector is thread-safe."""
        import threading

        collector = MetricsCollector()

        def record_metrics() -> None:
            for i in range(100):
                collector.record_latency("latency", float(i))
                collector.increment_counter("requests")
                collector.record_gauge("gauge", float(i))

        threads = [threading.Thread(target=record_metrics) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify all metrics recorded
        assert collector.get_counter("requests") == 500
        assert len(collector.histograms["latency"]) == 500


class TestObservabilityIntegration:
    """Integration tests for logger and metrics together."""

    def test_correlation_id_propagation(self) -> None:
        """Test correlation ID propagates correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            logger = StructuredLogger(log_path=log_path)

            # Set correlation ID
            custom_id = "integration-test-123"
            logger.set_correlation_id(custom_id)

            # Log multiple events
            logger.log_request("operation_1", "agent-1")
            logger.log_response("operation_1", "agent-1", "success", 45.0)
            logger.log_event("some_event")

            # All should have same correlation ID
            logs = logger.get_correlation_logs(custom_id)
            assert len(logs) == 3
            assert all(log["correlation_id"] == custom_id for log in logs)

    def test_metrics_and_logging_together(self) -> None:
        """Test metrics and logging working together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "test.jsonl")
            metrics_path = str(Path(tmpdir) / "metrics.jsonl")

            logger = StructuredLogger(log_path=log_path)
            collector = MetricsCollector(metrics_path=metrics_path)

            logger.log_request("inference", "agent-1")

            # Simulate inference
            duration_ms = 45.5
            collector.record_latency("llm_inference_latency", duration_ms)

            logger.log_response("inference", "agent-1", "success", duration_ms)

            # Write metrics
            collector.write_metrics_snapshot()

            # Verify both files exist and have data
            assert Path(log_path).exists()
            assert Path(metrics_path).exists()

            # Verify correlation ID in logs
            logs = logger.get_operation_logs("inference")
            assert len(logs) == 2

            # Verify metrics recorded
            summary = collector.get_metrics_summary()
            assert summary["llm_latency"] is not None
