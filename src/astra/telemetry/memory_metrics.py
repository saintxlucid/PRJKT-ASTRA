"""
Memory system metrics collection and export.

Collects Prometheus metrics for memory operations, counts,
and reconciliation status.
"""

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Any

# Memory Item Counts
MEMORY_ITEMS = Gauge(
    "astra_memory_items",
    "Current number of memory items by type",
    labelnames=["type"]  # type: semantic, episodic, procedural
)

# Memory Operation Latency
MEMORY_LATENCY = Histogram(
    "astra_memory_latency_ms",
    "Memory operation latency in milliseconds",
    labelnames=["op"],  # op: retrieve, upsert, search
    buckets=(5, 10, 25, 50, 100, 200, 500, 1000)
)

# Memory Reconciliation
MEMORY_RECONCILE_DRIFT = Counter(
    "astra_memory_reconcile_drift_total",
    "Total number of inconsistencies found during reconciliation",
    labelnames=["store"]  # store: chroma, sqlite
)

MEMORY_RECONCILE_DURATION = Histogram(
    "astra_memory_reconcile_duration_seconds",
    "Duration of memory reconciliation in seconds",
    buckets=(1, 5, 10, 30, 60, 120)
)

class MemoryMetrics:
    """Metric collection for memory system operations."""

    @staticmethod
    def update_memory_count(type: str, count: int) -> None:
        """Update memory item count for a given type."""
        MEMORY_ITEMS.labels(type=type).set(count)

    @staticmethod
    def observe_memory_latency(op: str, latency_ms: float) -> None:
        """Record memory operation latency."""
        MEMORY_LATENCY.labels(op=op).observe(latency_ms)

    @staticmethod
    def record_reconcile_drift(store: str) -> None:
        """Record reconciliation drift detection."""
        MEMORY_RECONCILE_DRIFT.labels(store=store).inc()

    @staticmethod
    def observe_reconcile_duration(duration_seconds: float) -> None:
        """Record reconciliation job duration."""
        MEMORY_RECONCILE_DURATION.observe(duration_seconds)

    @staticmethod
    def get_metrics_report() -> Dict[str, Any]:
        """Get current memory metrics as a dictionary."""
        return {
            "counts": {
                "semantic": MEMORY_ITEMS.labels("semantic")._value.get(),
                "episodic": MEMORY_ITEMS.labels("episodic")._value.get(),
                "procedural": MEMORY_ITEMS.labels("procedural")._value.get()
            },
            "reconciliation": {
                "chroma_drifts": MEMORY_RECONCILE_DRIFT.labels("chroma")._value.get(),
                "sqlite_drifts": MEMORY_RECONCILE_DRIFT.labels("sqlite")._value.get()
            }
        }