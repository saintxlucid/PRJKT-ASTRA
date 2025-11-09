"""
Phase 11: MetricsCollector - Prometheus-Compatible Metrics Collection

Provides counter, gauge, histogram, and summary metrics with
Prometheus-compatible export format for monitoring and alerting.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import math


class MetricType(Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class LabelSet:
    """Labels for a metric observation."""
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_prometheus_labels(self) -> str:
        """Convert to Prometheus label format."""
        if not self.labels:
            return ""
        items = [f'{k}="{v}"' for k, v in self.labels.items()]
        return "{" + ",".join(items) + "}"


class Counter:
    """Prometheus counter metric (monotonically increasing)."""
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
    
    def increment(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Increment counter."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0) + amount
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key for label combination."""
        if not labels:
            return "__no_labels__"
        items = [f"{k}={v}" for k, v in sorted(labels.items())]
        return "|".join(items)
    
    def get_values(self) -> Dict[str, float]:
        """Get all counter values."""
        return dict(self._values)
    
    def to_prometheus_lines(self) -> List[str]:
        """Convert to Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} counter",
        ]
        for labels_key, value in self._values.items():
            if labels_key == "__no_labels__":
                lines.append(f"{self.name} {value} {int(datetime.utcnow().timestamp() * 1000)}")
            else:
                label_dict = dict(item.split('=') for item in labels_key.split('|'))
                label_str = LabelSet(label_dict).to_prometheus_labels()
                lines.append(f"{self.name}{label_str} {value} {int(datetime.utcnow().timestamp() * 1000)}")
        return lines


class Gauge:
    """Prometheus gauge metric (can go up or down)."""
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        key = self._make_key(labels)
        self._values[key] = value
    
    def increment(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Increment gauge."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0) + amount
    
    def decrement(self, labels: Optional[Dict[str, str]] = None, amount: float = 1.0) -> None:
        """Decrement gauge."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0) - amount
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key for label combination."""
        if not labels:
            return "__no_labels__"
        items = [f"{k}={v}" for k, v in sorted(labels.items())]
        return "|".join(items)
    
    def get_values(self) -> Dict[str, float]:
        """Get all gauge values."""
        return dict(self._values)
    
    def to_prometheus_lines(self) -> List[str]:
        """Convert to Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} gauge",
        ]
        for labels_key, value in self._values.items():
            if labels_key == "__no_labels__":
                lines.append(f"{self.name} {value} {int(datetime.utcnow().timestamp() * 1000)}")
            else:
                label_dict = dict(item.split('=') for item in labels_key.split('|'))
                label_str = LabelSet(label_dict).to_prometheus_labels()
                lines.append(f"{self.name}{label_str} {value} {int(datetime.utcnow().timestamp() * 1000)}")
        return lines


class Histogram:
    """Prometheus histogram metric (distribution with buckets)."""
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None, buckets: List[float] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        
        # Per-label data
        self._observations: Dict[str, List[float]] = {}
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record observation."""
        key = self._make_key(labels)
        if key not in self._observations:
            self._observations[key] = []
        self._observations[key].append(value)
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key for label combination."""
        if not labels:
            return "__no_labels__"
        items = [f"{k}={v}" for k, v in sorted(labels.items())]
        return "|".join(items)
    
    def _get_statistics(self, observations: List[float]) -> Dict[str, float]:
        """Calculate statistics from observations."""
        if not observations:
            return {'count': 0, 'sum': 0, 'buckets': {}}
        
        sorted_obs = sorted(observations)
        bucket_counts = {}
        for bucket in self.buckets:
            bucket_counts[bucket] = sum(1 for o in observations if o <= bucket)
        bucket_counts['inf'] = len(observations)
        
        return {
            'count': len(observations),
            'sum': sum(observations),
            'buckets': bucket_counts,
        }
    
    def to_prometheus_lines(self) -> List[str]:
        """Convert to Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} histogram",
        ]
        
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        for labels_key, observations in self._observations.items():
            stats = self._get_statistics(observations)
            
            if labels_key == "__no_labels__":
                label_str = ""
                base_name = self.name
            else:
                label_dict = dict(item.split('=') for item in labels_key.split('|'))
                label_str = LabelSet(label_dict).to_prometheus_labels()
                base_name = self.name
            
            # Bucket lines
            for bucket, count in stats['buckets'].items():
                le_str = "+Inf" if bucket == 'inf' else str(bucket)
                if label_str:
                    lines.append(f'{base_name}_bucket{{le="{le_str}"{label_str[1:-1]}}} {count} {timestamp}')
                else:
                    lines.append(f'{base_name}_bucket{{le="{le_str}"}} {count} {timestamp}')
            
            # Sum line
            if label_str:
                lines.append(f'{base_name}_sum{label_str} {stats["sum"]} {timestamp}')
            else:
                lines.append(f'{base_name}_sum {stats["sum"]} {timestamp}')
            
            # Count line
            if label_str:
                lines.append(f'{base_name}_count{label_str} {stats["count"]} {timestamp}')
            else:
                lines.append(f'{base_name}_count {stats["count"]} {timestamp}')
        
        return lines


class Summary:
    """Prometheus summary metric (quantiles over time window)."""
    
    DEFAULT_QUANTILES = [0.5, 0.9, 0.99]
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None, quantiles: List[float] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self.quantiles = quantiles or self.DEFAULT_QUANTILES
        
        # Per-label data (keep last 1000 observations)
        self._observations: Dict[str, List[float]] = {}
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record observation."""
        key = self._make_key(labels)
        if key not in self._observations:
            self._observations[key] = []
        self._observations[key].append(value)
        
        # Keep only last 1000
        if len(self._observations[key]) > 1000:
            self._observations[key] = self._observations[key][-1000:]
    
    def _make_key(self, labels: Optional[Dict[str, str]]) -> str:
        """Create unique key for label combination."""
        if not labels:
            return "__no_labels__"
        items = [f"{k}={v}" for k, v in sorted(labels.items())]
        return "|".join(items)
    
    def _get_quantile(self, observations: List[float], q: float) -> float:
        """Calculate quantile from observations."""
        if not observations:
            return 0.0
        sorted_obs = sorted(observations)
        index = int(q * (len(sorted_obs) - 1))
        return sorted_obs[min(index, len(sorted_obs) - 1)]
    
    def to_prometheus_lines(self) -> List[str]:
        """Convert to Prometheus text format lines."""
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} summary",
        ]
        
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        for labels_key, observations in self._observations.items():
            if not observations:
                continue
            
            if labels_key == "__no_labels__":
                label_str = ""
                base_name = self.name
            else:
                label_dict = dict(item.split('=') for item in labels_key.split('|'))
                label_str = LabelSet(label_dict).to_prometheus_labels()
                base_name = self.name
            
            # Quantile lines
            for q in self.quantiles:
                quantile_val = self._get_quantile(observations, q)
                if label_str:
                    lines.append(f'{base_name}{{quantile="{q}"{label_str[1:-1]}}} {quantile_val} {timestamp}')
                else:
                    lines.append(f'{base_name}{{quantile="{q}"}} {quantile_val} {timestamp}')
            
            # Sum line
            sum_val = sum(observations)
            if label_str:
                lines.append(f'{base_name}_sum{label_str} {sum_val} {timestamp}')
            else:
                lines.append(f'{base_name}_sum {sum_val} {timestamp}')
            
            # Count line
            count_val = len(observations)
            if label_str:
                lines.append(f'{base_name}_count{label_str} {count_val} {timestamp}')
            else:
                lines.append(f'{base_name}_count {count_val} {timestamp}')
        
        return lines


class MetricsCollector:
    """Central metrics collection with Prometheus export."""
    
    def __init__(self):
        """Initialize collector."""
        self._metrics: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            'counters': 0,
            'gauges': 0,
            'histograms': 0,
            'summaries': 0,
            'total_observations': 0,
        }
    
    def register_counter(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """Register a counter metric."""
        counter = Counter(name, help_text, labels)
        self._metrics[name] = counter
        self._stats['counters'] += 1
        return counter
    
    def register_gauge(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """Register a gauge metric."""
        gauge = Gauge(name, help_text, labels)
        self._metrics[name] = gauge
        self._stats['gauges'] += 1
        return gauge
    
    def register_histogram(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None,
    ) -> Histogram:
        """Register a histogram metric."""
        histogram = Histogram(name, help_text, labels, buckets)
        self._metrics[name] = histogram
        self._stats['histograms'] += 1
        return histogram
    
    def register_summary(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None,
        quantiles: Optional[List[float]] = None,
    ) -> Summary:
        """Register a summary metric."""
        summary = Summary(name, help_text, labels, quantiles)
        self._metrics[name] = summary
        self._stats['summaries'] += 1
        return summary
    
    def get_metric(self, name: str) -> Any:
        """Get metric by name."""
        return self._metrics.get(name)
    
    def get_all_metrics(self) -> List[Any]:
        """Get all registered metrics."""
        return list(self._metrics.values())
    
    def get_metrics_by_component(self, component: str) -> List[Any]:
        """Get metrics with component label."""
        result = []
        for metric in self._metrics.values():
            if hasattr(metric, '_values'):
                for labels_key in metric._values.keys():
                    if component in labels_key:
                        result.append(metric)
                        break
        return result
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        for metric in self._metrics.values():
            if hasattr(metric, 'to_prometheus_lines'):
                lines.extend(metric.to_prometheus_lines())
                lines.append("")  # Blank line between metric families
        return "\n".join(lines)
    
    def export_json(self) -> Dict[str, Any]:
        """Export metrics as JSON."""
        result = {}
        for name, metric in self._metrics.items():
            if isinstance(metric, (Counter, Gauge)):
                result[name] = metric.get_values()
            elif isinstance(metric, Histogram):
                result[name] = {
                    'type': 'histogram',
                    'observations_count': sum(len(obs) for obs in metric._observations.values()),
                }
            elif isinstance(metric, Summary):
                result[name] = {
                    'type': 'summary',
                    'observations_count': sum(len(obs) for obs in metric._observations.values()),
                }
        return result
    
    def reset_metric(self, name: str) -> None:
        """Reset a specific metric."""
        metric = self._metrics.get(name)
        if metric:
            if hasattr(metric, '_values'):
                metric._values.clear()
            elif hasattr(metric, '_observations'):
                metric._observations.clear()
    
    def reset_all(self) -> None:
        """Reset all metrics."""
        for metric in self._metrics.values():
            if hasattr(metric, '_values'):
                metric._values.clear()
            elif hasattr(metric, '_observations'):
                metric._observations.clear()
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        total_obs = 0
        for metric in self._metrics.values():
            if hasattr(metric, '_observations'):
                total_obs += sum(len(obs) for obs in metric._observations.values())
            elif hasattr(metric, '_values'):
                total_obs += len(metric._values)
        
        return {
            'total_metrics': len(self._metrics),
            'counters': self._stats['counters'],
            'gauges': self._stats['gauges'],
            'histograms': self._stats['histograms'],
            'summaries': self._stats['summaries'],
            'total_observations': total_obs,
        }


# Global collector instance
_global_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def set_collector(collector: MetricsCollector) -> None:
    """Set global metrics collector."""
    global _global_collector
    _global_collector = collector
