"""Grafana Dashboards - Metrics Visualization

This module generates Grafana dashboard definitions for visualizing
ASTRA system performance, health metrics, and operational insights.

Key Features:
- Dynamic dashboard generation
- Multiple visualization types (graphs, gauges, tables)
- Alert integration
- Real-time metric queries
- Performance and health monitoring panels
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardPanel:
    """A single panel in a Grafana dashboard."""
    title: str
    panel_type: str
    targets: list[dict[str, Any]]
    gridPos: dict[str, int] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    fieldConfig: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert panel to dictionary."""
        return {
            "title": self.title,
            "type": self.panel_type,
            "targets": self.targets,
            "gridPos": self.gridPos,
            "options": self.options,
            "fieldConfig": self.fieldConfig,
        }


@dataclass
class GrafanaDashboard:
    """Grafana dashboard definition."""
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    panels: list[DashboardPanel] = field(default_factory=list)
    refresh: str = "30s"
    timezone: str = "browser"
    uid: str = ""

    def add_panel(self, panel: DashboardPanel, position: tuple[int, int]) -> None:
        """Add a panel to the dashboard.
        
        Args:
            panel: DashboardPanel to add
            position: (x, y) grid position
        """
        panel.gridPos = {"x": position[0], "y": position[1], "w": 12, "h": 8}
        self.panels.append(panel)

    def to_dict(self) -> dict[str, Any]:
        """Convert dashboard to dictionary."""
        return {
            "dashboard": {
                "title": self.title,
                "description": self.description,
                "tags": self.tags,
                "panels": [p.to_dict() for p in self.panels],
                "refresh": self.refresh,
                "timezone": self.timezone,
                "uid": self.uid,
                "version": 0,
            },
            "overwrite": True,
        }

    def to_json(self) -> str:
        """Convert dashboard to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class DashboardGenerator:
    """Generates Grafana dashboards for ASTRA system monitoring."""

    @staticmethod
    def create_performance_dashboard() -> GrafanaDashboard:
        """Create performance monitoring dashboard.
        
        Returns:
            GrafanaDashboard with performance metrics
        """
        dashboard = GrafanaDashboard(
            title="ASTRA Performance Metrics",
            description="Real-time performance metrics for ASTRA system",
            tags=["astra", "performance", "metrics"],
        )

        # Request latency panel
        latency_panel = DashboardPanel(
            title="Request Latency (ms)",
            panel_type="timeseries",
            targets=[
                {
                    "expr": 'histogram_quantile(0.95, rate(astra_request_duration_ms_bucket[5m]))',
                    "legendFormat": "p95",
                    "refId": "A",
                },
                {
                    "expr": 'histogram_quantile(0.99, rate(astra_request_duration_ms_bucket[5m]))',
                    "legendFormat": "p99",
                    "refId": "B",
                },
            ],
            options={"legend": {"calcs": ["mean", "max"], "displayMode": "table"}},
        )
        dashboard.add_panel(latency_panel, (0, 0))

        # Throughput panel
        throughput_panel = DashboardPanel(
            title="Request Throughput (req/s)",
            panel_type="timeseries",
            targets=[
                {
                    "expr": 'rate(astra_requests_total[5m])',
                    "legendFormat": "requests/sec",
                    "refId": "A",
                }
            ],
            options={"legend": {"displayMode": "list"}},
        )
        dashboard.add_panel(throughput_panel, (12, 0))

        # Error rate panel
        error_rate_panel = DashboardPanel(
            title="Error Rate (%)",
            panel_type="gauge",
            targets=[
                {
                    "expr": '100 * (rate(astra_errors_total[5m]) / rate(astra_requests_total[5m]))',
                    "refId": "A",
                }
            ],
            options={
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 5},
                        {"color": "red", "value": 10},
                    ],
                }
            },
        )
        dashboard.add_panel(error_rate_panel, (0, 8))

        return dashboard

    @staticmethod
    def create_health_dashboard() -> GrafanaDashboard:
        """Create system health monitoring dashboard.
        
        Returns:
            GrafanaDashboard with health metrics
        """
        dashboard = GrafanaDashboard(
            title="ASTRA System Health",
            description="System health and resource utilization",
            tags=["astra", "health", "system"],
        )

        # CPU usage panel
        cpu_panel = DashboardPanel(
            title="CPU Usage (%)",
            panel_type="gauge",
            targets=[
                {
                    "expr": "astra_process_cpu_percent",
                    "refId": "A",
                }
            ],
            options={
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 60},
                        {"color": "red", "value": 85},
                    ],
                }
            },
        )
        dashboard.add_panel(cpu_panel, (0, 0))

        # Memory usage panel
        memory_panel = DashboardPanel(
            title="Memory Usage (MB)",
            panel_type="gauge",
            targets=[
                {
                    "expr": "astra_process_memory_mb",
                    "refId": "A",
                }
            ],
            options={
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 1024},
                        {"color": "red", "value": 2048},
                    ],
                }
            },
        )
        dashboard.add_panel(memory_panel, (12, 0))

        # Disk I/O panel
        disk_io_panel = DashboardPanel(
            title="Disk I/O (MB/s)",
            panel_type="timeseries",
            targets=[
                {
                    "expr": 'rate(astra_disk_io_bytes[5m]) / 1024 / 1024',
                    "legendFormat": "MB/s",
                    "refId": "A",
                }
            ],
            options={"legend": {"displayMode": "list"}},
        )
        dashboard.add_panel(disk_io_panel, (0, 8))

        # Component health status panel
        health_panel = DashboardPanel(
            title="Component Status",
            panel_type="table",
            targets=[
                {
                    "expr": "astra_component_healthy",
                    "format": "table",
                    "instant": True,
                    "refId": "A",
                }
            ],
            options={"showHeader": True},
        )
        dashboard.add_panel(health_panel, (12, 8))

        return dashboard

    @staticmethod
    def create_memory_dashboard() -> GrafanaDashboard:
        """Create memory system monitoring dashboard.
        
        Returns:
            GrafanaDashboard with memory metrics
        """
        dashboard = GrafanaDashboard(
            title="ASTRA Memory System",
            description="Memory graph and recall engine metrics",
            tags=["astra", "memory", "system"],
        )

        # Memory graph size panel
        graph_size_panel = DashboardPanel(
            title="Memory Graph Nodes",
            panel_type="stat",
            targets=[
                {
                    "expr": "astra_memory_graph_nodes_total",
                    "refId": "A",
                }
            ],
            options={"displayMode": "number"},
        )
        dashboard.add_panel(graph_size_panel, (0, 0))

        # Recall latency panel
        recall_latency_panel = DashboardPanel(
            title="Recall Latency (ms)",
            panel_type="timeseries",
            targets=[
                {
                    "expr": 'histogram_quantile(0.95, rate(astra_recall_latency_ms_bucket[5m]))',
                    "legendFormat": "p95",
                    "refId": "A",
                }
            ],
            options={"legend": {"displayMode": "list"}},
        )
        dashboard.add_panel(recall_latency_panel, (12, 0))

        # Embedding store size panel
        embedding_size_panel = DashboardPanel(
            title="Embeddings Stored",
            panel_type="stat",
            targets=[
                {
                    "expr": "astra_embedding_store_count",
                    "refId": "A",
                }
            ],
            options={"displayMode": "number"},
        )
        dashboard.add_panel(embedding_size_panel, (0, 8))

        # Cache hit rate panel
        cache_hits_panel = DashboardPanel(
            title="Cache Hit Rate (%)",
            panel_type="gauge",
            targets=[
                {
                    "expr": '100 * (rate(astra_recall_cache_hits[5m]) / rate(astra_recall_queries[5m]))',
                    "refId": "A",
                }
            ],
            options={
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": 0},
                        {"color": "yellow", "value": 50},
                        {"color": "green", "value": 80},
                    ],
                }
            },
        )
        dashboard.add_panel(cache_hits_panel, (12, 8))

        return dashboard

    @staticmethod
    def create_deployment_dashboard() -> GrafanaDashboard:
        """Create deployment and rollout monitoring dashboard.
        
        Returns:
            GrafanaDashboard with deployment metrics
        """
        dashboard = GrafanaDashboard(
            title="ASTRA Deployment",
            description="Deployment status and rollout metrics",
            tags=["astra", "deployment", "operations"],
        )

        # Deployment progress panel
        progress_panel = DashboardPanel(
            title="Deployment Progress (%)",
            panel_type="gauge",
            targets=[
                {
                    "expr": "astra_deployment_progress_percent",
                    "refId": "A",
                }
            ],
            options={
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": 0},
                        {"color": "yellow", "value": 50},
                        {"color": "green", "value": 100},
                    ],
                }
            },
        )
        dashboard.add_panel(progress_panel, (0, 0))

        # Instances running panel
        instances_panel = DashboardPanel(
            title="Instances Running",
            panel_type="stat",
            targets=[
                {
                    "expr": "astra_deployment_instances_running",
                    "refId": "A",
                }
            ],
            options={"displayMode": "number"},
        )
        dashboard.add_panel(instances_panel, (12, 0))

        # Rollout status panel
        rollout_panel = DashboardPanel(
            title="Rollout Status",
            panel_type="table",
            targets=[
                {
                    "expr": "astra_deployment_rollout_status",
                    "format": "table",
                    "instant": True,
                    "refId": "A",
                }
            ],
            options={"showHeader": True},
        )
        dashboard.add_panel(rollout_panel, (0, 8))

        # Service restart events panel
        restart_panel = DashboardPanel(
            title="Service Restarts (24h)",
            panel_type="stat",
            targets=[
                {
                    "expr": 'increase(astra_deployment_restarts_total[24h])',
                    "refId": "A",
                }
            ],
            options={"displayMode": "number"},
        )
        dashboard.add_panel(restart_panel, (12, 8))

        return dashboard


class DashboardManager:
    """Manages dashboard lifecycle and operations."""

    def __init__(self):
        """Initialize dashboard manager."""
        self.dashboards: dict[str, GrafanaDashboard] = {}
        self.render_times: list[float] = []

    def register_dashboard(self, name: str, dashboard: GrafanaDashboard) -> None:
        """Register a dashboard.
        
        Args:
            name: Dashboard name/identifier
            dashboard: GrafanaDashboard instance
        """
        self.dashboards[name] = dashboard

    def render_dashboard(self, name: str) -> str:
        """Render a dashboard to JSON.
        
        Args:
            name: Dashboard name
            
        Returns:
            JSON string representation
        """
        start = time.time()

        if name not in self.dashboards:
            raise ValueError(f"Dashboard '{name}' not found")

        dashboard = self.dashboards[name]
        result = dashboard.to_json()

        render_time = (time.time() - start) * 1000
        self.render_times.append(render_time)

        return result

    def get_render_stats(self) -> dict[str, float]:
        """Get rendering performance statistics.
        
        Returns:
            Dictionary with render time stats
        """
        if not self.render_times:
            return {}

        sorted_times = sorted(self.render_times)
        return {
            "count": len(sorted_times),
            "min_ms": sorted_times[0],
            "max_ms": sorted_times[-1],
            "mean_ms": sum(sorted_times) / len(sorted_times),
            "p95_ms": sorted_times[int(len(sorted_times) * 0.95)],
            "p99_ms": sorted_times[int(len(sorted_times) * 0.99)],
        }

    def list_dashboards(self) -> list[str]:
        """List all registered dashboards.
        
        Returns:
            List of dashboard names
        """
        return list(self.dashboards.keys())
