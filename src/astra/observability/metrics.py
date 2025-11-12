"""
Prometheus-style metrics collection for ASTRA observability.

Collects and aggregates performance metrics including latency, resource usage,
and request counts for real-time monitoring and dashboarding.
"""

import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class HistogramBucket:
    """Histogram bucket for latency tracking."""
    boundary_ms: float
    count: int = 0


@dataclass
class MetricSnapshot:
    """Point-in-time metric snapshot."""
    timestamp: str
    metric_name: str
    value: float | int
    unit: str = ""
    tags: dict[str, str] | None = None


class MetricsCollector:
    """Prometheus-style metrics collector with gauges, counters, and histograms."""

    def __init__(self, metrics_path: str = "./logs/astra_metrics.jsonl"):
        """
        Initialize metrics collector.

        Args:
            metrics_path: Path to write metrics snapshots
        """
        self.metrics_path = metrics_path
        self._lock = threading.Lock()

        # Initialize metrics storage
        self.gauges: dict[str, float] = defaultdict(float)
        self.counters: dict[str, int] = defaultdict(int)
        self.histograms: dict[str, list[float]] = defaultdict(list)
        self.tags: dict[str, dict[str, str]] = defaultdict(dict)

        # Ensure metrics path exists
        Path(self.metrics_path).parent.mkdir(parents=True, exist_ok=True)

    def record_latency(
        self,
        metric_name: str,
        duration_ms: float,
        **tags: str,
    ) -> None:
        """
        Record latency measurement.

        Args:
            metric_name: Latency metric name
            duration_ms: Duration in milliseconds
            **tags: Additional tags for this metric
        """
        with self._lock:
            self.histograms[metric_name].append(duration_ms)
            if tags:
                self.tags[metric_name] = {**self.tags.get(metric_name, {}), **tags}

    def record_gauge(
        self,
        metric_name: str,
        value: float,
        **tags: str,
    ) -> None:
        """
        Record gauge metric (current state).

        Args:
            metric_name: Gauge metric name
            value: Gauge value
            **tags: Additional tags for this metric
        """
        with self._lock:
            self.gauges[metric_name] = value
            if tags:
                self.tags[metric_name] = {**self.tags.get(metric_name, {}), **tags}

    def increment_counter(
        self,
        metric_name: str,
        amount: int = 1,
        **tags: str,
    ) -> int:
        """
        Increment counter metric.

        Args:
            metric_name: Counter metric name
            amount: Amount to increment by
            **tags: Additional tags for this metric

        Returns:
            New counter value
        """
        with self._lock:
            self.counters[metric_name] += amount
            if tags:
                self.tags[metric_name] = {**self.tags.get(metric_name, {}), **tags}
            return self.counters[metric_name]

    def get_latency_percentiles(
        self,
        metric_name: str,
        percentiles: list[int] | None = None,
    ) -> dict[str, float]:
        """
        Get latency percentiles.

        Args:
            metric_name: Latency metric name
            percentiles: List of percentiles (50, 95, 99, etc.)

        Returns:
            Dictionary of percentile values
        """
        if percentiles is None:
            percentiles = [50, 95, 99]

        with self._lock:
            samples = sorted(self.histograms.get(metric_name, []))

        if not samples:
            return {}

        result = {}
        for p in percentiles:
            idx = int(len(samples) * (p / 100.0))
            idx = min(idx, len(samples) - 1)
            result[f"p{p}"] = samples[idx]

        return result

    def get_gauge(self, metric_name: str) -> float | None:
        """
        Get current gauge value.

        Args:
            metric_name: Gauge metric name

        Returns:
            Current gauge value or None if not set
        """
        with self._lock:
            return self.gauges.get(metric_name)

    def get_counter(self, metric_name: str) -> int:
        """
        Get current counter value.

        Args:
            metric_name: Counter metric name

        Returns:
            Current counter value
        """
        with self._lock:
            return self.counters.get(metric_name, 0)

    def get_latency_stats(
        self,
        metric_name: str,
    ) -> dict[str, float | int] | None:
        """
        Get latency statistics.

        Args:
            metric_name: Latency metric name

        Returns:
            Dictionary with min, max, mean, median, p95, p99
        """
        with self._lock:
            samples = self.histograms.get(metric_name, [])

        if not samples:
            return None

        sorted_samples = sorted(samples)
        return {
            "count": len(sorted_samples),
            "min": min(sorted_samples),
            "max": max(sorted_samples),
            "mean": sum(sorted_samples) / len(sorted_samples),
            "median": sorted_samples[len(sorted_samples) // 2],
            "p95": sorted_samples[int(len(sorted_samples) * 0.95)],
            "p99": sorted_samples[int(len(sorted_samples) * 0.99)],
        }

    def export_metrics(self) -> dict[str, Any]:
        """
        Export all metrics as dictionary.

        Returns:
            Dictionary containing all metric data
        """
        with self._lock:
            metrics_export = {
                "timestamp": datetime.now().isoformat(),
                "gauges": dict(self.gauges),
                "counters": dict(self.counters),
                "histograms": {
                    k: {
                        "count": len(v),
                        "samples": v,
                        "stats": self.get_latency_stats(k),
                    }
                    for k, v in self.histograms.items()
                },
            }

        return metrics_export

    def write_metrics_snapshot(self, snapshot_name: str = "") -> str:
        """
        Write metrics snapshot to JSONL file.

        Args:
            snapshot_name: Optional name for this snapshot

        Returns:
            Written snapshot as JSON string
        """
        metrics_data = self.export_metrics()
        if snapshot_name:
            metrics_data["snapshot_name"] = snapshot_name

        snapshot_json = json.dumps(metrics_data)

        with open(self.metrics_path, 'a') as f:
            f.write(snapshot_json + '\n')

        return snapshot_json

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get summary of current metrics.

        Returns:
            Dictionary with key metrics summary
        """
        with self._lock:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "active_requests": self.gauges.get("active_requests", 0),
                "total_requests": self.counters.get("total_requests", 0),
                "total_errors": self.counters.get("errors_total", 0),
                "llm_latency": self.get_latency_stats("llm_inference_latency"),
                "retrieval_latency": self.get_latency_stats("vector_retrieval_latency"),
                "execution_latency": self.get_latency_stats("agent_task_execution_latency"),
                "gpu_memory_mb": self.gauges.get("gpu_memory_usage", 0),
                "cpu_percent": self.gauges.get("cpu_utilization", 0),
            }

        return summary

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        with self._lock:
            self.gauges.clear()
            self.counters.clear()
            self.histograms.clear()
            self.tags.clear()

    def get_histogram_buckets(
        self,
        metric_name: str,
        bucket_boundaries: list[float] | None = None,
    ) -> dict[str, int]:
        """
        Get histogram buckets for metric.

        Args:
            metric_name: Histogram metric name
            bucket_boundaries: Bucket boundaries in ms (default: standard Prometheus buckets)

        Returns:
            Dictionary of bucket boundaries to counts
        """
        if bucket_boundaries is None:
            bucket_boundaries = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]

        with self._lock:
            samples = self.histograms.get(metric_name, [])

        buckets = {}
        for boundary in bucket_boundaries:
            count = sum(1 for s in samples if s <= boundary)
            buckets[f"{boundary}ms"] = count

        return buckets
