"""
Prometheus metrics exporter for ASTRA Phase-C components.

Collects metrics from event bus and exports to Prometheus.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server
import structlog

from astra.core.event_bus import get_event_bus


logger = structlog.get_logger(__name__)


# Prometheus Metrics Definition

# Counters
ROUTER_CALLS = Counter(
    "astra_router_calls_total",
    "Total router calls by mode",
    ["mode"],
)

ROUTER_PHASES = Counter(
    "astra_router_evolution_phases_total",
    "Evolution phases executed",
    ["phase"],
)

TOOL_CALLS = Counter(
    "astra_tool_execution_total",
    "Total tool executions",
    ["tool", "status"],
)

CONSENT_REQUESTS = Counter(
    "astra_consent_requests_total",
    "Consent requests by status",
    ["status"],
)

CONSENT_BYPASSES = Counter(
    "astra_consent_bypass_attempts_total",
    "Bypass attempt events",
)

BUDGET_EXHAUSTIONS = Counter(
    "astra_budget_exhaustion_events_total",
    "Budget exhaustion events by component",
    ["component"],
)

ACT_GATES = Counter(
    "astra_act_phase_gates_total",
    "ACT phase gate decisions",
    ["result"],
)

OS_ACTIONS = Counter(
    "astra_os_action_total",
    "OS operator actions by type",
    ["operator", "status"],
)

# OS Operator Specific Metrics (GO-LIVE Item 4)
OSOP_ACTIONS = Counter(
    "astra_osop_actions_total",
    "OSOP capability invocations by capability and result",
    ["capability", "result", "consent_given"],
)

OSOP_BYTES = Counter(
    "astra_osop_bytes_total",
    "OSOP data bytes transferred (fs.read/fs.write)",
    ["operation"],
)

OSOP_CONSENT_BLOCKS = Counter(
    "astra_osop_consent_blocks_total",
    "OSOP operations blocked due to missing consent",
    ["capability"],
)

# Histograms
TOOL_DURATION = Histogram(
    "astra_tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool", "status"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

PLAN_GENERATION_DURATION = Histogram(
    "astra_plan_generation_duration_seconds",
    "Plan generation duration in seconds",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0),
)

PLAN_EXECUTION_DURATION = Histogram(
    "astra_plan_execution_duration_seconds",
    "Plan execution duration in seconds",
    ["status"],
    buckets=(1.0, 2.5, 5.0, 10.0, 25.0),
)

CONSENT_APPROVAL_TIME = Histogram(
    "astra_consent_approval_time_seconds",
    "Time to consent decision in seconds",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0),
)

OS_ACTION_DURATION = Histogram(
    "astra_os_action_duration_seconds",
    "OS action duration in seconds",
    ["operator"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
)

# Gauges
ACTIVE_PLANS = Gauge(
    "astra_active_plans",
    "Currently executing plans",
)

ACTIVE_CONSENTS = Gauge(
    "astra_active_consent_requests",
    "Pending consent approvals",
)

REMAINING_BUDGET = Gauge(
    "astra_remaining_budget_tokens",
    "Remaining budget tokens",
)


@dataclass
class MetricEvent:
    """Internal metric event tracking."""

    event_type: str
    timestamp: float
    labels: Dict[str, str]
    value: Optional[float] = None


class MetricsExporter:
    """Collects and exports metrics from event bus."""

    def __init__(self, port: int = 8000):
        """Initialize metrics exporter."""
        self.port = port
        self.bus = get_event_bus()
        self.running = False

        # Event tracking for timing
        self.tool_starts: Dict[str, float] = {}
        self.plan_starts: Dict[str, float] = {}
        self.consent_starts: Dict[str, float] = {}

        logger.info("metrics_exporter_init", port=port)

    def start(self) -> None:
        """Start metrics HTTP server."""
        try:
            start_http_server(self.port)
            self.running = True
            logger.info("metrics_http_started", port=self.port)
        except Exception as e:
            logger.error("metrics_start_failed", error=str(e))
            raise

    async def setup_subscriptions(self) -> None:
        """Setup event subscriptions for metrics collection."""
        # Router events
        self.bus.subscribe("astra.router.route_selected", self._on_route_selected)
        self.bus.subscribe("astra.router.phase_executing", self._on_phase_executing)

        # Tool events
        self.bus.subscribe("astra.tool.before", self._on_tool_before)
        self.bus.subscribe("astra.tool.executed", self._on_tool_executed)
        self.bus.subscribe("astra.tool.timeout", self._on_tool_timeout)
        self.bus.subscribe("astra.tool.error", self._on_tool_error)

        # Plan events
        self.bus.subscribe("astra.plan.generation_start", self._on_plan_gen_start)
        self.bus.subscribe("astra.plan.generation_complete", self._on_plan_gen_complete)
        self.bus.subscribe("astra.plan.execution_start", self._on_plan_exec_start)
        self.bus.subscribe("astra.plan.execution_complete", self._on_plan_exec_complete)

        # Consent events
        self.bus.subscribe("astra.plan.consent_request", self._on_consent_request)
        self.bus.subscribe("astra.plan.consent_decision", self._on_consent_decision)
        self.bus.subscribe("astra.plan.consent_bypass", self._on_consent_bypass)

        # Budget events
        self.bus.subscribe("astra.plan.budget_exhaustion", self._on_budget_exhaustion)

        # ACT gate events
        self.bus.subscribe("astra.act.gate_decision", self._on_act_gate)

        # OS events
        self.bus.subscribe("astra.os.action_start", self._on_os_action_start)
        self.bus.subscribe("astra.os.action_complete", self._on_os_action_complete)
        
        # OSOP-specific events (GO-LIVE Item 4)
        self.bus.subscribe("astra.osop.capability_invoked", self._on_osop_capability)
        self.bus.subscribe("astra.osop.consent_blocked", self._on_osop_consent_blocked)
        self.bus.subscribe("astra.osop.bytes_transferred", self._on_osop_bytes)

        logger.info("metrics_subscriptions_setup")

    # Router event handlers

    def _on_route_selected(self, event: Any) -> None:
        """Track route selection."""
        mode = event.data.get("mode", "unknown")
        ROUTER_CALLS.labels(mode=mode).inc()
        logger.debug("metric_route", mode=mode)

    def _on_phase_executing(self, event: Any) -> None:
        """Track evolution phase execution."""
        phase = event.data.get("phase", "unknown")
        ROUTER_PHASES.labels(phase=phase).inc()
        logger.debug("metric_phase", phase=phase)

    # Tool event handlers

    def _on_tool_before(self, event: Any) -> None:
        """Track tool execution start."""
        tool_id = event.data.get("tool_id", "unknown")
        self.tool_starts[tool_id] = time.time()
        logger.debug("metric_tool_start", tool_id=tool_id)

    def _on_tool_executed(self, event: Any) -> None:
        """Track successful tool execution."""
        tool_id = event.data.get("tool_id", "unknown")
        tool_name = event.data.get("tool", "unknown")
        success = event.data.get("success", False)

        status = "success" if success else "failed"
        TOOL_CALLS.labels(tool=tool_name, status=status).inc()

        # Record duration
        if tool_id in self.tool_starts:
            duration = time.time() - self.tool_starts.pop(tool_id)
            TOOL_DURATION.labels(tool=tool_name, status=status).observe(duration)
            logger.debug("metric_tool_complete", tool=tool_name, duration=duration)

    def _on_tool_timeout(self, event: Any) -> None:
        """Track tool timeout."""
        tool_id = event.data.get("tool_id", "unknown")
        tool_name = event.data.get("tool", "unknown")

        TOOL_CALLS.labels(tool=tool_name, status="timeout").inc()

        if tool_id in self.tool_starts:
            duration = time.time() - self.tool_starts.pop(tool_id)
            TOOL_DURATION.labels(tool=tool_name, status="timeout").observe(duration)

        logger.debug("metric_tool_timeout", tool=tool_name)

    def _on_tool_error(self, event: Any) -> None:
        """Track tool error."""
        tool_id = event.data.get("tool_id", "unknown")
        tool_name = event.data.get("tool", "unknown")

        TOOL_CALLS.labels(tool=tool_name, status="error").inc()

        if tool_id in self.tool_starts:
            duration = time.time() - self.tool_starts.pop(tool_id)
            TOOL_DURATION.labels(tool=tool_name, status="error").observe(duration)

        logger.debug("metric_tool_error", tool=tool_name)

    # Plan event handlers

    def _on_plan_gen_start(self, event: Any) -> None:
        """Track plan generation start."""
        plan_id = event.data.get("plan_id", "unknown")
        self.plan_starts[plan_id] = time.time()
        logger.debug("metric_plan_gen_start", plan_id=plan_id)

    def _on_plan_gen_complete(self, event: Any) -> None:
        """Track plan generation completion."""
        plan_id = event.data.get("plan_id", "unknown")

        if plan_id in self.plan_starts:
            duration = time.time() - self.plan_starts.pop(plan_id)
            PLAN_GENERATION_DURATION.observe(duration)
            logger.debug("metric_plan_gen_complete", duration=duration)

    def _on_plan_exec_start(self, event: Any) -> None:
        """Track plan execution start."""
        plan_id = event.data.get("plan_id", "unknown")
        self.plan_starts[plan_id] = time.time()
        ACTIVE_PLANS.inc()
        logger.debug("metric_plan_exec_start", plan_id=plan_id)

    def _on_plan_exec_complete(self, event: Any) -> None:
        """Track plan execution completion."""
        plan_id = event.data.get("plan_id", "unknown")
        status = event.data.get("status", "unknown")

        ACTIVE_PLANS.dec()

        if plan_id in self.plan_starts:
            duration = time.time() - self.plan_starts.pop(plan_id)
            PLAN_EXECUTION_DURATION.labels(status=status).observe(duration)
            logger.debug("metric_plan_exec_complete", status=status, duration=duration)

    # Consent event handlers

    def _on_consent_request(self, event: Any) -> None:
        """Track consent request."""
        request_id = event.data.get("request_id", "unknown")
        self.consent_starts[request_id] = time.time()
        ACTIVE_CONSENTS.inc()
        logger.debug("metric_consent_request", request_id=request_id)

    def _on_consent_decision(self, event: Any) -> None:
        """Track consent decision."""
        request_id = event.data.get("request_id", "unknown")
        approved = event.data.get("approved", False)

        ACTIVE_CONSENTS.dec()
        status = "approved" if approved else "rejected"
        CONSENT_REQUESTS.labels(status=status).inc()

        # Record approval time
        if request_id in self.consent_starts:
            duration = time.time() - self.consent_starts.pop(request_id)
            CONSENT_APPROVAL_TIME.observe(duration)
            logger.debug("metric_consent_decision", status=status, duration=duration)

    def _on_consent_bypass(self, event: Any) -> None:
        """Track bypass attempt."""
        CONSENT_BYPASSES.inc()
        logger.warning("metric_bypass_attempt")

    # Budget event handlers

    def _on_budget_exhaustion(self, event: Any) -> None:
        """Track budget exhaustion."""
        component = event.data.get("component", "unknown")
        BUDGET_EXHAUSTIONS.labels(component=component).inc()
        logger.warning("metric_budget_exhausted", component=component)

    # ACT gate handlers

    def _on_act_gate(self, event: Any) -> None:
        """Track ACT gate decision."""
        allowed = event.data.get("allowed", False)
        result = "allowed" if allowed else "blocked"
        ACT_GATES.labels(result=result).inc()
        logger.debug("metric_act_gate", result=result)

    # OS event handlers

    def _on_os_action_start(self, event: Any) -> None:
        """Track OS action start."""
        action_id = event.data.get("action_id", "unknown")
        operator = event.data.get("operator", "unknown")
        self.tool_starts[f"os_{action_id}"] = time.time()
        logger.debug("metric_os_action_start", operator=operator)

    def _on_os_action_complete(self, event: Any) -> None:
        """Track OS action completion."""
        action_id = event.data.get("action_id", "unknown")
        operator = event.data.get("operator", "unknown")
        success = event.data.get("success", False)

        status = "success" if success else "failed"
        OS_ACTIONS.labels(operator=operator, status=status).inc()

        # Record duration
        key = f"os_{action_id}"
        if key in self.tool_starts:
            duration = time.time() - self.tool_starts.pop(key)
            OS_ACTION_DURATION.labels(operator=operator).observe(duration)
            logger.debug("metric_os_action_complete", operator=operator, duration=duration)
    
    # OSOP-specific event handlers (GO-LIVE Item 4)
    
    def _on_osop_capability(self, event: Any) -> None:
        """Track OSOP capability invocation."""
        capability = event.data.get("capability", "unknown")
        result = event.data.get("result", "unknown")  # success, failed, blocked
        consent_given = str(event.data.get("consent_given", False)).lower()
        
        OSOP_ACTIONS.labels(
            capability=capability,
            result=result,
            consent_given=consent_given
        ).inc()
        
        logger.debug("metric_osop_capability", capability=capability, result=result)
    
    def _on_osop_consent_blocked(self, event: Any) -> None:
        """Track OSOP operations blocked due to missing consent."""
        capability = event.data.get("capability", "unknown")
        OSOP_CONSENT_BLOCKS.labels(capability=capability).inc()
        logger.warning("metric_osop_consent_blocked", capability=capability)
    
    def _on_osop_bytes(self, event: Any) -> None:
        """Track OSOP data bytes transferred (fs.read/fs.write)."""
        operation = event.data.get("operation", "unknown")  # read or write
        bytes_count = event.data.get("bytes", 0)
        
        OSOP_BYTES.labels(operation=operation).inc(bytes_count)
        logger.debug("metric_osop_bytes", operation=operation, bytes=bytes_count)


async def start_metrics_exporter(port: int = 8000) -> MetricsExporter:
    """Start metrics exporter and setup subscriptions."""
    exporter = MetricsExporter(port=port)
    exporter.start()
    await exporter.setup_subscriptions()
    return exporter
