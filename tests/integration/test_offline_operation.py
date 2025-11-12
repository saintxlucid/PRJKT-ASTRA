"""Offline operation validation - Phase 2 Task 4.

Minimal offline validation suite testing core offline capabilities:
- Hardening and risk scoring without external calls
- Structured logging in offline mode
- Metrics collection completely offline
"""

import tempfile
import time
from pathlib import Path
from unittest import mock

from astra.agents.hardening import AgentAction, OperatorRiskScorer, RiskLevel
from astra.observability.metrics import MetricsCollector
from astra.observability.structured_logger import StructuredLogger


class TestOfflineHardening:
    """Test agent hardening completely offline."""

    def test_risk_scoring_offline(self) -> None:
        """Test risk scoring works completely offline."""
        scorer = OperatorRiskScorer()

        action = AgentAction(
            tool_name="search_knowledge",
            arguments={"query": "test"},
            agent_id="offline-agent",
        )

        risk_level, reason = scorer.score_action(action)

        assert risk_level is not None
        assert isinstance(risk_level, RiskLevel)
        assert isinstance(reason, str)

    def test_risk_scoring_no_network(self) -> None:
        """Verify risk scoring never attempts network calls."""
        scorer = OperatorRiskScorer()

        with mock.patch("urllib.request.urlopen") as mock_http:
            action = AgentAction(
                tool_name="read_file",
                arguments={"path": "/tmp/test"},
                agent_id="offline-agent",
            )
            scorer.score_action(action)
            mock_http.assert_not_called()

    def test_multiple_tool_scoring_offline(self) -> None:
        """Test scoring multiple tools in offline mode."""
        scorer = OperatorRiskScorer()

        tools = ["read_file", "list_dir", "write_file"]
        risk_levels = []

        for tool_name in tools:
            action = AgentAction(
                tool_name=tool_name,
                arguments={},
                agent_id="offline-agent",
            )
            risk_level, _ = scorer.score_action(action)
            risk_levels.append(risk_level)

        assert len(risk_levels) == len(tools)
        assert all(isinstance(r, RiskLevel) for r in risk_levels)

    def test_tool_escalation_detection_offline(self) -> None:
        """Test tool escalation detection works offline."""
        scorer = OperatorRiskScorer()

        # Low-risk action
        low_action = AgentAction(
            tool_name="read_file",
            arguments={"path": "/tmp/data.txt"},
            agent_id="offline-agent",
        )
        low_risk, _ = scorer.score_action(low_action)

        # High-risk action
        high_action = AgentAction(
            tool_name="execute_command",
            arguments={"cmd": "rm -rf /"},
            agent_id="offline-agent",
        )
        high_risk, _ = scorer.score_action(high_action)

        # Verify escalation is detected
        assert high_risk.value > low_risk.value


class TestOfflineObservability:
    """Test observability features in offline mode."""

    def test_structured_logging_offline(self) -> None:
        """Test structured logging works completely offline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                log_path=str(Path(tmpdir) / "logs.jsonl"),
            )

            corr_id = logger.log_event(
                "offline_operation",
                level="INFO",
                operation="test",
                status="started",
            )

            assert corr_id is not None
            assert Path(logger.log_path).exists()

    def test_correlation_id_tracking_offline(self) -> None:
        """Test correlation ID tracking works offline."""
        logger = StructuredLogger()

        custom_id = "offline-trace-123"
        logger.set_correlation_id(custom_id)

        for i in range(5):
            logger.log_event(f"step_{i}", level="INFO")

        logs = logger.get_correlation_logs(custom_id)
        assert len(logs) >= 5
        assert all(log["correlation_id"] == custom_id for log in logs)

    def test_request_response_logging_offline(self) -> None:
        """Test request-response logging flow works offline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                log_path=str(Path(tmpdir) / "logs.jsonl"),
            )

            logger.log_request(
                "vector_search",
                agent_id="offline-agent",
                query="test query",
            )

            logger.log_response(
                "vector_search",
                agent_id="offline-agent",
                status="success",
                duration_ms=45.5,
                result_count=3,
            )

            with open(logger.log_path) as f:
                lines = f.readlines()

            assert len(lines) == 2

    def test_metrics_collection_offline(self) -> None:
        """Test metrics collection works completely offline."""
        collector = MetricsCollector()

        # Record various metrics
        collector.record_latency("inference", 45.5)
        collector.record_gauge("gpu_memory", 4096.0)
        collector.increment_counter("requests", 10)

        # Verify collection
        assert collector.get_gauge("gpu_memory") == 4096.0
        assert collector.get_counter("requests") == 10

    def test_metrics_export_offline(self) -> None:
        """Test metrics export works offline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = MetricsCollector(
                metrics_path=str(Path(tmpdir) / "metrics.jsonl"),
            )

            collector.record_latency("inference", 45.0)
            collector.record_gauge("gpu_memory", 4096.0)
            collector.increment_counter("total_requests", 100)

            snapshot = collector.write_metrics_snapshot("offline_checkpoint")

            assert Path(collector.metrics_path).exists()
            assert "offline_checkpoint" in snapshot

    def test_latency_percentiles_offline(self) -> None:
        """Test latency percentile calculations work offline."""
        collector = MetricsCollector()

        # Record latency samples
        for i in range(1, 101):
            collector.record_latency("test_latency", float(i))

        percentiles = collector.get_latency_percentiles(
            "test_latency",
            percentiles=[50, 95, 99],
        )

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] <= percentiles["p95"] <= percentiles["p99"]


class TestOfflineIntegration:
    """Integration tests for offline operations."""

    def test_hardening_with_logging(self) -> None:
        """Test hardening operations with structured logging."""
        logger = StructuredLogger()
        scorer = OperatorRiskScorer()

        corr_id = "hardening-test-123"
        logger.set_correlation_id(corr_id)

        tools = ["read_file", "list_dir"]

        for tool_name in tools:
            logger.log_request(f"score_{tool_name}", agent_id="offline")

            action = AgentAction(
                tool_name=tool_name,
                arguments={},
                agent_id="offline",
            )
            risk_level, reason = scorer.score_action(action)

            logger.log_response(
                f"score_{tool_name}",
                agent_id="offline",
                status="success",
                risk_level=risk_level.name,
                reason=reason,
                duration_ms=1.0,
            )

        # Verify complete trace
        logs = logger.get_correlation_logs(corr_id if corr_id else "")
        assert len(logs) >= len(tools) * 2  # Request + Response per tool

    def test_zero_external_dependencies(self) -> None:
        """Verify offline operations have zero external dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch("urllib.request.urlopen") as mock_http:
                with mock.patch("requests.get") as mock_requests:
                    # Run typical offline operations
                    logger = StructuredLogger(
                        log_path=str(Path(tmpdir) / "logs.jsonl"),
                    )
                    scorer = OperatorRiskScorer()
                    collector = MetricsCollector()

                    # Perform operations
                    logger.log_event("test_event")

                    action = AgentAction(
                        tool_name="read_file",
                        arguments={"path": "/tmp/test"},
                        agent_id="offline",
                    )
                    scorer.score_action(action)
                    collector.record_latency("test", 50.0)

                    # Verify no external calls made
                    mock_http.assert_not_called()
                    mock_requests.assert_not_called()


class TestOfflineBenchmarks:
    """Performance benchmarks for offline operations."""

    def test_logging_throughput_benchmark(self) -> None:
        """Benchmark logging throughput."""
        logger = StructuredLogger()

        start = time.time()
        for i in range(1000):
            logger.log_event(f"event_{i}", level="INFO")
        duration = time.time() - start

        # Should handle 1000 events in reasonable time
        assert duration < 5.0, f"Logging 1000 events took {duration}s"

    def test_metrics_collection_benchmark(self) -> None:
        """Benchmark metrics collection performance."""
        collector = MetricsCollector()

        start = time.time()
        for i in range(1000):
            collector.record_latency("test", float(i))
            collector.increment_counter("test_counter")
            collector.record_gauge("test_gauge", float(i))
        duration = time.time() - start

        # Should handle 1000 metric operations in reasonable time
        assert duration < 1.0, f"1000 metric operations took {duration}s"

    def test_risk_scoring_throughput_benchmark(self) -> None:
        """Benchmark risk scoring throughput."""
        scorer = OperatorRiskScorer()

        start = time.time()
        for _ in range(100):
            action = AgentAction(
                tool_name="read_file",
                arguments={"path": "/tmp/test"},
                agent_id="benchmark",
            )
            scorer.score_action(action)
        duration = time.time() - start

        # Should score 100 actions quickly
        assert duration < 1.0, f"Scoring 100 actions took {duration}s"
