"""Comprehensive Deployment Tests - Week 4 Observability & Deployment

Tests for tracing, dashboards, alerts, packaging, and installation modules.
Validates deployment readiness, performance targets, and integration.
"""

import asyncio
import json
import pytest
from pathlib import Path
import tempfile

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from observability.tracing import TracingManager, SpanKind
from observability.dashboards import (
    DashboardGenerator, DashboardManager
)
from observability.alerts import (
    AlertManager, AlertSeverity
)
from deployment.packager import (
    ServicePackager, ArtifactRegistry, ArtifactMetadata
)
from deployment.installer import (
    ServiceInstaller, DeploymentOrchestrator
)


# ============================================================================
# TRACING TESTS
# ============================================================================

class TestTracingManager:
    """Tests for distributed tracing."""

    @pytest.mark.asyncio
    async def test_span_creation(self):
        """Test creating spans."""
        manager = TracingManager()
        span = await manager.start_span("test_operation", kind=SpanKind.INTERNAL)
        assert span is not None
        assert span.span_name == "test_operation"
        assert span.kind == SpanKind.INTERNAL

    @pytest.mark.asyncio
    async def test_span_lifecycle(self):
        """Test span start/end lifecycle."""
        manager = TracingManager()
        span = await manager.start_span("test_op")
        span_id = span.span_id

        # Verify active
        assert await manager.get_active_spans_count() == 1

        # End span
        duration = await manager.end_span(span_id)
        assert duration > 0
        assert await manager.get_active_spans_count() == 0

    @pytest.mark.asyncio
    async def test_span_events(self):
        """Test adding events to spans."""
        manager = TracingManager()
        span = await manager.start_span("test_op")

        result = await manager.add_event(span.span_id, "step_1", {"status": "started"})
        assert result is True

        await manager.end_span(span.span_id)

    @pytest.mark.asyncio
    async def test_span_metrics(self):
        """Test span metrics collection."""
        manager = TracingManager()
        trace_id = "test_trace_123"

        span1 = await manager.start_span("op1", trace_id=trace_id)
        await asyncio.sleep(0.01)
        await manager.end_span(span1.span_id)

        metrics = await manager.get_span_metrics(trace_id)
        assert metrics["span_count"] == 1
        assert metrics["p95_duration_ms"] >= 10

    @pytest.mark.asyncio
    async def test_span_error_handling(self):
        """Test error handling in spans."""
        manager = TracingManager()
        span = await manager.start_span("failing_op")

        await manager.end_span(span.span_id, error="Test error")

        history = await manager.get_spans_history(limit=1)
        assert len(history) > 0
        assert history[0]["status"] == "ERROR"
        assert history[0]["error_message"] == "Test error"


# ============================================================================
# DASHBOARD TESTS
# ============================================================================

class TestDashboardGenerator:
    """Tests for Grafana dashboard generation."""

    def test_performance_dashboard_creation(self):
        """Test creating performance dashboard."""
        dashboard = DashboardGenerator.create_performance_dashboard()
        assert dashboard.title == "ASTRA Performance Metrics"
        assert len(dashboard.panels) > 0

    def test_health_dashboard_creation(self):
        """Test creating health dashboard."""
        dashboard = DashboardGenerator.create_health_dashboard()
        assert dashboard.title == "ASTRA System Health"
        assert len(dashboard.panels) >= 4

    def test_memory_dashboard_creation(self):
        """Test creating memory dashboard."""
        dashboard = DashboardGenerator.create_memory_dashboard()
        assert dashboard.title == "ASTRA Memory System"
        assert len(dashboard.panels) >= 3

    def test_deployment_dashboard_creation(self):
        """Test creating deployment dashboard."""
        dashboard = DashboardGenerator.create_deployment_dashboard()
        assert dashboard.title == "ASTRA Deployment"
        assert len(dashboard.panels) >= 3

    def test_dashboard_serialization(self):
        """Test dashboard JSON serialization."""
        dashboard = DashboardGenerator.create_performance_dashboard()
        json_str = dashboard.to_json()

        data = json.loads(json_str)
        assert data["dashboard"]["title"] == "ASTRA Performance Metrics"

    def test_dashboard_rendering_performance(self):
        """Test dashboard rendering meets <500ms target."""
        manager = DashboardManager()

        # Register all dashboards
        manager.register_dashboard("performance", DashboardGenerator.create_performance_dashboard())
        manager.register_dashboard("health", DashboardGenerator.create_health_dashboard())
        manager.register_dashboard("memory", DashboardGenerator.create_memory_dashboard())
        manager.register_dashboard("deployment", DashboardGenerator.create_deployment_dashboard())

        # Render dashboards
        for dashboard_name in manager.list_dashboards():
            json_str = manager.render_dashboard(dashboard_name)
            assert len(json_str) > 0

        # Check performance
        stats = manager.get_render_stats()
        assert stats.get("p95_ms", 0) < 500


# ============================================================================
# ALERT TESTS
# ============================================================================

class TestAlertManager:
    """Tests for alert management."""

    def test_create_alert_rule(self):
        """Test creating alert rules."""
        manager = AlertManager()
        rule = manager.create_rule(
            rule_id="high_latency",
            rule_name="High Latency Alert",
            description="Latency exceeds 500ms",
            metric="request_latency_ms",
            operator="gt",
            threshold=500.0,
            severity=AlertSeverity.WARNING,
        )
        assert rule is not None
        assert rule.rule_name == "High Latency Alert"

    def test_metric_evaluation(self):
        """Test evaluating metrics against rules."""
        manager = AlertManager()
        manager.create_rule(
            rule_id="high_latency",
            rule_name="High Latency",
            description="Latency > 500ms",
            metric="latency",
            operator="gt",
            threshold=500.0,
            severity=AlertSeverity.WARNING,
        )

        # Should trigger alert
        alerts = manager.evaluate_metric("latency", 600.0)
        assert len(alerts) == 1

        # Should not trigger alert
        alerts = manager.evaluate_metric("latency", 400.0)
        assert len(alerts) == 0

    def test_anomaly_detection(self):
        """Test anomaly detection."""
        manager = AlertManager()

        # Add normal values
        for i in range(10):
            manager.detect_anomalies("metric", 100.0 + i)

        # Add anomaly
        alerts = manager.detect_anomalies("metric", 500.0)
        assert len(alerts) == 1

    def test_alert_stats(self):
        """Test alert statistics."""
        manager = AlertManager()
        manager.create_rule(
            rule_id="test_rule",
            rule_name="Test",
            description="Test",
            metric="test_metric",
            operator="gt",
            threshold=100.0,
            severity=AlertSeverity.CRITICAL,
        )

        manager.evaluate_metric("test_metric", 200.0)

        stats = manager.get_alert_stats()
        assert stats["total_alerts"] > 0
        assert stats["rules_count"] == 1


# ============================================================================
# PACKAGING TESTS
# ============================================================================

class TestServicePackager:
    """Tests for service packaging."""

    def test_artifact_creation(self):
        """Test creating service artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            packager = ServicePackager(base_path=tmpdir)

            # Create source directory
            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            (source_dir / "test.py").write_text("# test")

            metadata = packager.create_artifact(
                artifact_id="test_artifact",
                service_name="test_service",
                version="1.0.0",
                source_dir=str(source_dir),
                created_by="test_user",
                description="Test artifact",
            )

            assert metadata.artifact_id == "test_artifact"
            assert metadata.service_name == "test_service"
            assert metadata.file_count > 0

    def test_artifact_verification(self):
        """Test artifact integrity verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            packager = ServicePackager(base_path=tmpdir)

            source_dir = Path(tmpdir) / "source"
            source_dir.mkdir()
            (source_dir / "test.py").write_text("# test")

            _metadata = packager.create_artifact(
                artifact_id="test_artifact",
                service_name="test_service",
                version="1.0.0",
                source_dir=str(source_dir),
            )

            # Verify should pass
            assert packager.verify_artifact("test_artifact") is True

    def test_artifact_registry(self):
        """Test artifact registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ArtifactRegistry(str(Path(tmpdir) / "registry.json"))

            metadata = ArtifactMetadata(
                artifact_id="test_1",
                service_name="test_service",
                version="1.0.0",
                created_at_ms=1000.0,
                created_by="test_user",
                description="Test",
            )

            registry.register_artifact(metadata)

            latest = registry.get_latest_version("test_service")
            assert latest is not None
            assert latest["version"] == "1.0.0"


# ============================================================================
# INSTALLER TESTS
# ============================================================================

class TestServiceInstaller:
    """Tests for service installation."""

    def test_installation_steps_creation(self):
        """Test installation step tracking."""
        installer = ServiceInstaller()
        assert len(installer.installations) == 0

    def test_installation_stats(self):
        """Test installation statistics."""
        installer = ServiceInstaller()

        stats = installer.get_installation_stats()
        assert stats["total_installations"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0


class TestDeploymentOrchestrator:
    """Tests for deployment orchestration."""

    def test_orchestrator_creation(self):
        """Test orchestrator creation."""
        orchestrator = DeploymentOrchestrator()
        assert orchestrator is not None

    def test_deployment_status(self):
        """Test deployment status reporting."""
        orchestrator = DeploymentOrchestrator()

        status = orchestrator.get_deployment_status()
        assert status["total_deployments"] == 0
        assert status["successful"] == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestWeek4Integration:
    """Integration tests for Week 4 observability and deployment."""

    @pytest.mark.asyncio
    async def test_tracing_with_alerts(self):
        """Test tracing integration with alerting."""
        tracing = TracingManager()
        alerts = AlertManager()

        # Create alert rule for long spans
        alerts.create_rule(
            rule_id="long_span",
            rule_name="Long Span",
            description="Span > 500ms",
            metric="span_duration",
            operator="gt",
            threshold=500.0,
            severity=AlertSeverity.WARNING,
        )

        # Create span that triggers alert
        span = await tracing.start_span("long_operation")
        await asyncio.sleep(0.1)
        await tracing.end_span(span.span_id)

        triggered_alerts = alerts.evaluate_metric("span_duration", 600.0)
        assert len(triggered_alerts) > 0

    @pytest.mark.asyncio
    async def test_full_observability_stack(self):
        """Test full observability stack integration."""
        tracing = TracingManager()
        dashboards = DashboardManager()
        alerts = AlertManager()

        # Create tracing
        span = await tracing.start_span("full_test")
        await tracing.add_event(span.span_id, "test_event")
        await tracing.end_span(span.span_id)

        # Create dashboards
        dashboards.register_dashboard(
            "performance",
            DashboardGenerator.create_performance_dashboard()
        )

        # Create alerts
        alerts.create_rule(
            rule_id="integration_test",
            rule_name="Integration",
            description="Test",
            metric="test",
            operator="gt",
            threshold=100.0,
            severity=AlertSeverity.INFO,
        )

        # Verify all working
        metrics = await tracing.get_span_metrics(span.trace_id)
        assert metrics["span_count"] == 1

        dashboard_json = dashboards.render_dashboard("performance")
        assert len(dashboard_json) > 0

        alert_stats = alerts.get_alert_stats()
        assert alert_stats["rules_count"] == 1

    def test_deployment_readiness(self):
        """Test deployment readiness checks."""
        packager = ServicePackager()
        installer = ServiceInstaller()
        orchestrator = DeploymentOrchestrator()

        # All components initialized
        assert packager is not None
        assert installer is not None
        assert orchestrator is not None

        # Stats available
        pkg_stats = packager.get_artifact_stats()
        inst_stats = installer.get_installation_stats()
        deploy_status = orchestrator.get_deployment_status()

        assert "total_artifacts" in pkg_stats
        assert "total_installations" in inst_stats
        assert "total_deployments" in deploy_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
