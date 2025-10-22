"""
ASTRA Metrics Collection
Prometheus metrics for monitoring ASTRA's behavior and performance.
Created: October 16, 2025
"""
from typing import Dict, Any, Optional, cast, Callable, Awaitable, TypeVar
try:
    # Python 3.11+
    from typing import ParamSpec
except ImportError:  # pragma: no cover
    # Fallback for older environments
    from typing_extensions import ParamSpec  # type: ignore
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client import start_http_server
import structlog
from functools import wraps
import time

from .safety_metrics import SafetyMetrics

logger = structlog.get_logger()

P = ParamSpec("P")
R = TypeVar("R")

__all__ = ['MetricsManager', 'SafetyMetrics']


class MetricsManager:
    """Manages metrics collection and reporting"""
    
    def __init__(self, port: int = 9090, registry: Optional[CollectorRegistry] = None):
        """Initialize metrics tracking"""
        self.port = port
        self._registry = registry
        
        # Core metrics for operations
        # Note: Action counters are managed by SafetyMetrics to avoid duplicate
        # registrations of the same metric name across components.
        
        # Performance metrics
        self.llm_latency = Histogram(
            'astra_llm_latency_seconds',
            'LLM response time in seconds',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self._registry)

        self.memory_latency = Histogram(
            'astra_memory_latency_seconds',
            'Memory operation latency in seconds',
            ['operation'],
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0),
            registry=self._registry)

        # Resource metrics
        self.memory_usage = Gauge(
            'astra_memory_usage_bytes',
            'Memory usage by store type',
            ['store'],
            registry=self._registry)

        self.cache_stats = Counter(
            'astra_cache_total',
            'Cache operations total',
            ['operation'],
            registry=self._registry)
            
        # Reconciliation metrics
        self.reconciliation_diffs = Gauge(
            'astra_memory_reconciliation_diffs',
            'Number of differences found during reconciliation',
            ['memory_type'],
            registry=self._registry)
            
        self.reconciliation_errors = Counter(
            'astra_memory_reconciliation_errors_total',
            'Total number of errors encountered during reconciliation',
            registry=self._registry)
        
        # Core metrics from SafetyMetrics
        self.safety = SafetyMetrics(registry=self._registry)
    
    def track_action(self, tool: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorator to track tool execution"""
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                try:
                    result = await func(*args, **kwargs)
                    # Delegate to SafetyMetrics to record action success
                    self.safety.record_action_result(tool=tool, success=True)
                    return result
                except Exception:
                    # Delegate to SafetyMetrics to record action failure
                    self.safety.record_action_result(tool=tool, success=False)
                    raise
            return wrapper
        return decorator

    def track_memory(self, operation: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorator to track memory operations"""
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.time()
                result = await func(*args, **kwargs)
                self.memory_latency.labels(
                    operation=operation).observe(time.time() - start)
                return result
            return wrapper
        return decorator

    def track_llm(self) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        """Decorator to track LLM latency"""
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start = time.time()
                result = await func(*args, **kwargs)
                self.llm_latency.observe(time.time() - start)
                return result
            return wrapper
        return decorator
        
    def start(self) -> None:
        """Start Prometheus metrics server"""
        start_http_server(self.port)
        logger.info(f"Metrics server started on port {self.port}")
        
    def record_plan(self, mode: str) -> None:
        """Record execution plan"""
        self.safety.record_plan_result(mode)
        
    def record_escalation(self, reason: str) -> None:
        """Record alignment escalation"""
        self.safety.record_alignment_escalation(reason, "")
        
    def record_consent(self, level: str) -> None:
        """Record consent request"""
        self.safety.record_consent_required(level)
        
    def record_backup(self, path: str = "") -> None:
        """Record backup operation"""
        self.safety.record_backup_injected(path)
        
    def record_irreversible_no_backup(self, operation: str = "") -> None:
        """Record irreversible action without backup"""
        self.safety.record_irreversible_without_backup(operation)
        
    def update_memory_usage(self, store: str, bytes: int) -> None:
        """Update memory usage gauge"""
        self.memory_usage.labels(store=store).set(bytes)
        
    def record_cache(self, operation: str) -> None:
        """Record cache operation"""
        self.cache_stats.labels(operation=operation).inc()
        
    def observe_reconciliation_diffs(self, semantic: int, episodic: int, procedural: int) -> None:
        """Record number of differences found during reconciliation"""
        self.reconciliation_diffs.labels(memory_type="semantic").set(semantic)
        self.reconciliation_diffs.labels(memory_type="episodic").set(episodic)
        self.reconciliation_diffs.labels(memory_type="procedural").set(procedural)
        
    def record_reconciliation_error(self) -> None:
        """Record an error encountered during reconciliation"""
        self.reconciliation_errors.inc()