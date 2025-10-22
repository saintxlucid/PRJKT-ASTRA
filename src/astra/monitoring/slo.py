"""
Service Level Objectives (SLO) definitions and monitoring.
Tracks API latency, WebSocket uptime, memory usage, and error rates.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
import structlog
from prometheus_client import Counter, Histogram, Gauge
from .metrics_exporter import MetricsExporter

logger = structlog.get_logger()

class SLOMetricType(Enum):
    """Types of SLO metrics"""
    LATENCY = "latency"
    UPTIME = "uptime"
    ERROR_RATE = "error_rate"
    BYTES = "bytes"

@dataclass
class SLODefinition:
    """Definition of a Service Level Objective"""
    name: str
    description: str
    type: SLOMetricType
    target: float  # Target value (e.g., 99.9 for 99.9% uptime)
    window: timedelta  # Time window for evaluation
    critical_threshold: float  # Alert threshold
    warning_threshold: float  # Warning threshold

class SLOMonitor:
    """Monitors and reports on SLO compliance"""
    
    def __init__(self, metrics_exporter: Optional[MetricsExporter] = None):
        self.metrics_exporter = metrics_exporter or MetricsExporter()
        
        # Initialize metrics
        self.api_latency = Histogram(
            "astra_api_latency_seconds",
            "API request latency",
            ["endpoint", "method"],
            buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
        )
        
        self.ws_uptime = Gauge(
            "astra_ws_uptime_ratio",
            "WebSocket connection uptime ratio"
        )
        
        self.context_bytes = Gauge(
            "astra_context_bytes_total",
            "Total bytes in context",
            ["type"]  # semantic, episodic, procedural
        )
        
        self.error_counter = Counter(
            "astra_errors_total",
            "Total error count",
            ["type", "severity"]
        )
        
        # Define SLOs
        self.slos: Dict[str, SLODefinition] = {
            "api_latency": SLODefinition(
                name="API Latency",
                description="95th percentile API latency under 250ms",
                type=SLOMetricType.LATENCY,
                target=0.25,  # 250ms
                window=timedelta(minutes=5),
                critical_threshold=0.5,  # 500ms
                warning_threshold=0.35  # 350ms
            ),
            "ws_uptime": SLODefinition(
                name="WebSocket Uptime",
                description="WebSocket connection uptime above 99.9%",
                type=SLOMetricType.UPTIME,
                target=99.9,
                window=timedelta(hours=24),
                critical_threshold=99.0,
                warning_threshold=99.5
            ),
            "context_size": SLODefinition(
                name="Context Size",
                description="Total context size under 100MB per user",
                type=SLOMetricType.BYTES,
                target=100 * 1024 * 1024,  # 100MB
                window=timedelta(minutes=5),
                critical_threshold=200 * 1024 * 1024,  # 200MB
                warning_threshold=150 * 1024 * 1024  # 150MB
            ),
            "error_rate": SLODefinition(
                name="Error Rate",
                description="Error rate below 0.1%",
                type=SLOMetricType.ERROR_RATE,
                target=0.1,
                window=timedelta(minutes=5),
                critical_threshold=1.0,  # 1%
                warning_threshold=0.5  # 0.5%
            )
        }
        
        # Initialize violation tracking
        self.last_violation: Dict[str, Optional[datetime]] = {
            slo: None for slo in self.slos
        }
        
    async def track_api_latency(self, endpoint: str, method: str, latency: float) -> None:
        """Track API request latency"""
        self.api_latency.labels(endpoint=endpoint, method=method).observe(latency)
        
        # Check SLO
        if latency > self.slos["api_latency"].critical_threshold:
            await self._handle_violation(
                "api_latency",
                f"Critical latency of {latency:.3f}s for {method} {endpoint}"
            )
        elif latency > self.slos["api_latency"].warning_threshold:
            await self._handle_warning(
                "api_latency",
                f"High latency of {latency:.3f}s for {method} {endpoint}"
            )
            
    async def update_ws_uptime(self, uptime_ratio: float) -> None:
        """Update WebSocket uptime ratio"""
        self.ws_uptime.set(uptime_ratio)
        
        # Check SLO
        if uptime_ratio < self.slos["ws_uptime"].critical_threshold:
            await self._handle_violation(
                "ws_uptime",
                f"Critical WebSocket uptime at {uptime_ratio:.1f}%"
            )
        elif uptime_ratio < self.slos["ws_uptime"].warning_threshold:
            await self._handle_warning(
                "ws_uptime", 
                f"Low WebSocket uptime at {uptime_ratio:.1f}%"
            )
            
    async def update_context_bytes(self, type_: str, bytes_: int) -> None:
        """Update context size metrics"""
        self.context_bytes.labels(type=type_).set(bytes_)
        
        # Check total against SLO
        total_bytes = sum(
            float(self.context_bytes.labels(type=t)._value.get())
            for t in ["semantic", "episodic", "procedural"]
        )
        
        if total_bytes > self.slos["context_size"].critical_threshold:
            await self._handle_violation(
                "context_size",
                f"Critical context size of {total_bytes/1024/1024:.1f}MB"
            )
        elif total_bytes > self.slos["context_size"].warning_threshold:
            await self._handle_warning(
                "context_size",
                f"High context size of {total_bytes/1024/1024:.1f}MB"
            )
            
    async def track_error(self, type_: str, severity: str = "error") -> None:
        """Track error occurrence"""
        self.error_counter.labels(type=type_, severity=severity).inc()
        
        # Calculate error rate over window
        window_errors = sum(
            float(self.error_counter.labels(type=t, severity=s)._value.get())
            for t in ["api", "websocket", "plugin", "memory"]
            for s in ["error", "critical"]
        )
        
        total_ops = float(self.api_latency._metrics["count"])
        if total_ops > 0:
            error_rate = (window_errors / total_ops) * 100
            
            if error_rate > self.slos["error_rate"].critical_threshold:
                await self._handle_violation(
                    "error_rate",
                    f"Critical error rate of {error_rate:.2f}%"
                )
            elif error_rate > self.slos["error_rate"].warning_threshold:
                await self._handle_warning(
                    "error_rate",
                    f"High error rate of {error_rate:.2f}%"
                )
                
    async def _handle_violation(self, slo: str, message: str) -> None:
        """Handle SLO violation"""
        now = datetime.utcnow()
        last = self.last_violation[slo]
        
        # Don't alert more than once per window
        if not last or (now - last) > self.slos[slo].window:
            logger.error(
                "SLO violation",
                slo=slo,
                message=message,
                threshold=self.slos[slo].critical_threshold,
                window=self.slos[slo].window
            )
            self.last_violation[slo] = now
            
    async def _handle_warning(self, slo: str, message: str) -> None:
        """Handle SLO warning"""
        logger.warning(
            "SLO warning",
            slo=slo,
            message=message,
            threshold=self.slos[slo].warning_threshold
        )
        
    def get_slo_status(self) -> Dict[str, Dict]:
        """Get current SLO status"""
        status = {}
        for name, slo in self.slos.items():
            status[name] = {
                "name": slo.name,
                "description": slo.description,
                "target": slo.target,
                "current": self._get_current_value(name),
                "last_violation": self.last_violation[name],
                "status": self._get_slo_status(name)
            }
        return status
        
    def _get_current_value(self, slo: str) -> float:
        """Get current value for an SLO metric"""
        if slo == "api_latency":
            return float(self.api_latency.observe_exemplars._value.get())
        elif slo == "ws_uptime":
            return float(self.ws_uptime._value.get())
        elif slo == "context_size":
            return sum(
                float(self.context_bytes.labels(type=t)._value.get())
                for t in ["semantic", "episodic", "procedural"]
            )
        elif slo == "error_rate":
            total_ops = float(self.api_latency._metrics["count"])
            if total_ops > 0:
                window_errors = sum(
                    float(self.error_counter.labels(type=t, severity=s)._value.get())
                    for t in ["api", "websocket", "plugin", "memory"]
                    for s in ["error", "critical"]
                )
                return (window_errors / total_ops) * 100
            return 0.0
        return 0.0
        
    def _get_slo_status(self, slo: str) -> str:
        """Get status indicator for an SLO"""
        current = self._get_current_value(slo)
        definition = self.slos[slo]
        
        if (definition.type in [SLOMetricType.LATENCY, SLOMetricType.ERROR_RATE, SLOMetricType.BYTES] 
            and current > definition.critical_threshold):
            return "critical"
        elif (definition.type == SLOMetricType.UPTIME 
              and current < definition.critical_threshold):
            return "critical"
        elif (definition.type in [SLOMetricType.LATENCY, SLOMetricType.ERROR_RATE, SLOMetricType.BYTES]
              and current > definition.warning_threshold):
            return "warning"
        elif (definition.type == SLOMetricType.UPTIME
              and current < definition.warning_threshold):
            return "warning"
        return "ok"