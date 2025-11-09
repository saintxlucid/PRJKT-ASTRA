# telemetry/metrics.py
"""
Prometheus metrics exporter for ASTRA OS.
Exports metrics on HTTP endpoint for monitoring.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import Counter, Gauge, Histogram, Info

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        start_http_server,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Define dummy types for type checking
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    Gauge = None  # type: ignore
    Info = None  # type: ignore
    start_http_server = None  # type: ignore


class MetricsExporter:
    """
    Prometheus metrics exporter.
    Exposes /metrics endpoint on HTTP server.
    """

    def __init__(self, port: int = 9108, enable_server: bool = True):
        """
        Initialize metrics exporter.

        Args:
            port: HTTP port for /metrics endpoint
            enable_server: Whether to start HTTP server (default True)
        """
        self.port = port
        self.server_started = False

        if not PROMETHEUS_AVAILABLE:
            print("Warning: prometheus_client not installed, metrics disabled")
            self._metrics_enabled = False
            return

        self._metrics_enabled = True

        # Tool metrics
        self.tool_latency_ms = Histogram(  # type: ignore
            "astra_tool_latency_ms",
            "Tool execution latency in milliseconds",
            ["tool_name"],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
        )

        self.tool_calls_total = Counter(  # type: ignore
            "astra_tool_calls_total",
            "Total number of tool calls",
            ["tool_name", "status"],
        )

        # Token verification metrics
        self.token_verify_total = Counter(  # type: ignore
            "astra_token_verify_total",
            "Total token verifications",
            ["result"],
        )

        self.token_verify_fail_total = Counter(  # type: ignore
            "astra_token_verify_fail_total",
            "Total failed token verifications",
            ["reason"],
        )

        # Controller action metrics
        self.controller_action_total = Counter(  # type: ignore
            "astra_controller_action_total",
            "Total controller actions",
            ["action", "status"],
        )

        # Agent state metrics
        self.agent_state = Gauge(  # type: ignore
            "astra_agent_state",
            "Current agent state (0=IDLE, 1=PLAN, 2=CALL_TOOL, 3=OBSERVE, 4=ANSWER)",
        )

        self.agent_iterations = Counter(  # type: ignore
            "astra_agent_iterations_total",
            "Total agent iterations",
        )

        self.agent_tasks_total = Counter(  # type: ignore
            "astra_agent_tasks_total",
            "Total agent tasks",
            ["status"],
        )

        # Memory metrics
        self.memory_writes_total = Counter(  # type: ignore
            "astra_memory_writes_total",
            "Total memory writes",
            ["tier"],
        )

        self.memory_reads_total = Counter(  # type: ignore
            "astra_memory_reads_total",
            "Total memory reads",
            ["tier", "result"],
        )

        # Browser metrics
        self.browser_nav_total = Counter(  # type: ignore
            "astra_browser_nav_total",
            "Total browser navigations",
            ["status"],
        )

        self.browser_extract_total = Counter(  # type: ignore
            "astra_browser_extract_total",
            "Total DOM extractions",
        )

        # System info
        self.system_info = Info(  # type: ignore
            "astra_system",
            "ASTRA OS system information",
        )

        self.system_info.info({
            "version": "0.1.0",
            "phase": "P0",
        })

        # Start HTTP server if enabled
        if enable_server:
            self.start_server()

    def start_server(self) -> None:
        """Start Prometheus HTTP server."""
        if not self._metrics_enabled:
            return

        if self.server_started:
            print(f"Metrics server already running on port {self.port}")
            return

        try:
            start_http_server(self.port)  # type: ignore
            self.server_started = True
            print(f"Metrics server started on http://localhost:{self.port}/metrics")
        except OSError as e:
            print(f"Warning: Could not start metrics server on port {self.port}: {e}")

    # Tool metrics methods
    def record_tool_call(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record tool call metrics."""
        if not self._metrics_enabled:
            return

        self.tool_latency_ms.labels(tool_name=tool_name).observe(latency_ms)
        status = "success" if success else "error"
        self.tool_calls_total.labels(tool_name=tool_name, status=status).inc()

    # Token verification metrics
    def record_token_verify(self, success: bool, reason: str | None = None) -> None:
        """Record token verification."""
        if not self._metrics_enabled:
            return

        result = "success" if success else "fail"
        self.token_verify_total.labels(result=result).inc()

        if not success and reason:
            self.token_verify_fail_total.labels(reason=reason).inc()

    # Controller action metrics
    def record_controller_action(self, action: str, success: bool) -> None:
        """Record controller action."""
        if not self._metrics_enabled:
            return

        status = "success" if success else "error"
        self.controller_action_total.labels(action=action, status=status).inc()

    # Agent state metrics
    def set_agent_state(self, state: str) -> None:
        """Set current agent state."""
        if not self._metrics_enabled:
            return

        state_map = {
            "IDLE": 0,
            "PLAN": 1,
            "CALL_TOOL": 2,
            "OBSERVE": 3,
            "ANSWER": 4,
        }
        self.agent_state.set(state_map.get(state, 0))

    def record_agent_iteration(self) -> None:
        """Record agent iteration."""
        if not self._metrics_enabled:
            return

        self.agent_iterations.inc()

    def record_agent_task(self, status: str) -> None:
        """Record agent task completion."""
        if not self._metrics_enabled:
            return

        self.agent_tasks_total.labels(status=status).inc()

    # Memory metrics
    def record_memory_write(self, tier: str) -> None:
        """Record memory write."""
        if not self._metrics_enabled:
            return

        self.memory_writes_total.labels(tier=tier).inc()

    def record_memory_read(self, tier: str, found: bool) -> None:
        """Record memory read."""
        if not self._metrics_enabled:
            return

        result = "hit" if found else "miss"
        self.memory_reads_total.labels(tier=tier, result=result).inc()

    # Browser metrics
    def record_browser_nav(self, success: bool) -> None:
        """Record browser navigation."""
        if not self._metrics_enabled:
            return

        status = "success" if success else "error"
        self.browser_nav_total.labels(status=status).inc()

    def record_browser_extract(self) -> None:
        """Record DOM extraction."""
        if not self._metrics_enabled:
            return

        self.browser_extract_total.inc()


# Global metrics instance
_metrics: MetricsExporter | None = None


def get_metrics(port: int = 9108, enable_server: bool = True) -> MetricsExporter:
    """
    Get global metrics instance (singleton).

    Args:
        port: HTTP port for /metrics endpoint
        enable_server: Whether to start HTTP server

    Returns:
        MetricsExporter instance
    """
    global _metrics

    if _metrics is None:
        _metrics = MetricsExporter(port=port, enable_server=enable_server)

    return _metrics
